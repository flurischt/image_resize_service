import mimetypes
from functools import wraps

from flask import Flask, send_file, request, Response, render_template
from flask.ext.restful import Api, Resource, reqparse, fields, marshal_with
from flask_cors import CORS
from werkzeug.exceptions import Forbidden
import werkzeug

from storage import *


CONFIG_STORAGE_DIR = "STORAGE_DIRECTORY"

app = Flask(__name__)
app.config.from_pyfile('../default.cfg', silent=True)
app.config.from_pyfile('../production.cfg', silent=True)
api = Api(app)
cors = CORS(app, resources={r"/upload": {"origins": "*"}})

_storage = None


@app.after_request
def add_header(response):
    response.headers[
        'Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept, Cache-Control, Authorization'
    return response


def storage():
    """returns access to the storage (save_image(), get() and exists())"""
    global _storage
    if _storage is None:
        _storage = FileSystemStorage(app.config[CONFIG_STORAGE_DIR])
    return _storage


def _check_auth(username, password, project):
    """This function is called to check if a username /
    password combination is valid.
    """
    if project not in app.config['PROJECTS']:
        return False
    correct_user, correct_pass = app.config['PROJECTS'][project]['auth']
    return username == correct_user and password == correct_pass


def _check_auth_token(origin, token, project):
    correct_origin, correct_token = app.config['PROJECTS'][project]['auth_token']
    return (correct_origin == "*" or origin == correct_origin) and token == correct_token


def _serve_image(image_file, extension):
    mime_type = mimetypes.types_map['.%s' % extension]
    return send_file(image_file, mimetype=mime_type, add_etags=False)


def _authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login using your credentials and a valid PROJECT',

        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


@app.route('/')
def index():
    return render_template('demo.html')


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        project = kwargs['project'] if 'project' in kwargs else None
        if project is None or project not in app.config['PROJECTS']:
            raise Forbidden()

        # check if it has auth token
        auth_header = request.headers.get('Authorization')
        origin = request.headers.get('Origin')
        if auth_header is not None and origin is not None and auth_header.startswith('Token'):
            # get the origin header
            key, token = auth_header.split(" ")
            if _check_auth_token(origin, token, project):
                return f(*args, **kwargs)

        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password, project):
            return _authenticate()
        return f(*args, **kwargs)

    return decorated


def _upload_json_response(success, **kwargs):
    res_dict = dict(status='ok' if success else 'fail')
    res_dict.update(kwargs)
    code = 201 if success else 500
    return res_dict, code


def serve_image(project_name, name, extension, mode=None, size=None):
    if project_name not in app.config['PROJECTS']:
        raise NotFound()
    return _serve_image(project_name, name, extension, mode, size)


class UploadResponse:
    resource_fields = {
        'url': fields.String
    }


class UploadAPI(Resource):
    """
    API that supports POST for images.
    """
    decorators = [requires_auth]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('file', type=werkzeug.datastructures.FileStorage, required=True,
                                   help='No file provided', location='files')
        super(UploadAPI, self).__init__()

    @marshal_with(UploadResponse.resource_fields)
    def post(self, project):
        args = self.reqparse.parse_args()
        uploaded_file = args['file']
        filename, extension = secure_filename(uploaded_file.filename).rsplit(
            '.', 1)
        filename = storage().safe_name(project, filename, extension)
        storage().save(project, filename, extension, uploaded_file.read())
        url = api.url_for(ImageAPI, project=project, name=filename, extension=extension)
        return {"url": url}, 201


class ImageAPI(Resource):
    """
    API that supports GET, PUT and DELETE for images.
    """

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('file', type=werkzeug.datastructures.FileStorage, required=True,
                                   help='No file provided', location='files')
        super(ImageAPI, self).__init__()

    @requires_auth
    def put(self, project, name, extension):
        args = self.reqparse.parse_args()
        uploaded_file = args['file']
        created = not storage().exists(project, name, extension)
        storage().save(project, name, extension, uploaded_file.read())
        return Response('', 201 if created else 200)

    @requires_auth
    def delete(self, project, name, extension):
        if storage().exists(project, name, extension):
            storage().delete(project, name, extension)
            return Response('', 200)
        raise NotFound()

    def get(self, project, name, extension):
        image = storage().get(project, name, extension)
        return _serve_image(image, extension)


class ManipulatedImageAPI(Resource):
    """
    API that supports GET for manipulated images.
    """

    def get(self, project, name, mode, width, height, extension):
        try:
            image = storage().get(project, name, extension, mode, (int(width), int(height)))
        except ValueError:
            raise NotFound()
        return _serve_image(image, extension)


api.add_resource(UploadAPI, '/images/<project>/')
api.add_resource(ImageAPI, '/images/<project>/<name>.<extension>')
api.add_resource(ManipulatedImageAPI, '/images/<project>/<name>@<mode>-<width>x<height>.<extension>')

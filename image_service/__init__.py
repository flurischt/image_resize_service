import mimetypes
import werkzeug
from functools import wraps

from flask import Flask, send_file, request, Response, render_template
from flask_restful import Api, Resource, reqparse, fields, marshal_with
from flask_cors import CORS
from werkzeug.exceptions import Unauthorized

from image_service.storage import *


CONFIG_STORAGE_DIR = 'STORAGE_DIRECTORY'

app = Flask(__name__)
app.config.from_pyfile('../config.py', silent=True)
api = Api(app)
cors = CORS(app, resources={r'/*': {'origins': '*'}})

_storage = None


@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Headers'] = ', '.join((
            'Origin', 
            'X-Requested-With', 
            'Content-Type', 
            'Accept', 
            'Cache-Control', 
            'Authorization'
    ))
    return response


def storage():
    """returns access to the storage (save_image(), get() and exists())"""
    global _storage
    if not _storage:
        _storage = FileSystemStorage(app.config[CONFIG_STORAGE_DIR])
    return _storage


def _serve_image(image_file, extension):
    mime_type = mimetypes.types_map['.%s' % extension.lower()]
    return send_file(image_file, mimetype=mime_type, add_etags=False)


def _check_auth_token(origin, token):
    if 'AUTH_TOKEN' in app.config and app.config['AUTH_TOKEN'] != '':
        expected_origin, expected_token = app.config['AUTH_TOKEN']
        return (expected_origin == '*' or expected_origin == origin) and expected_token == token


def _check_auth_basic(username, password):
    if 'AUTH_BASIC' in app.config and app.config['AUTH_BASIC'] != '':
        correct_user, correct_pass = app.config['AUTH_BASIC']
        return username == correct_user and password == correct_pass


@app.route('/')
def index():
    if app.config['ENABLE_DEMO']:
        return render_template('demo.html')
    return Response('Nothing to see here ;)', 404)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # check if it has auth token
        auth_header = request.headers.get('Authorization')
        origin = request.headers.get('Origin')
        if auth_header is not None:
            if auth_header.startswith('Token'):
                # get the origin header
                key, token = auth_header.split(' ')
                if _check_auth_token(origin, token):
                    return f(*args, **kwargs)
            if auth_header.startswith('Basic'):
                auth = request.authorization
                if _check_auth_basic(auth.username, auth.password):
                    return f(*args, **kwargs)
        raise Unauthorized()
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
    def post(self):
        args = self.reqparse.parse_args()
        uploaded_file = args['file']
        filename, extension = secure_filename(uploaded_file.filename).rsplit(
            '.', 1)
        filename = storage().safe_name(filename, extension)
        storage().save(filename, extension, uploaded_file.read())
        url = api.url_for(ImageAPI, name=filename, extension=extension)
        return {'url': url}, 201


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
    def put(self, name, extension):
        args = self.reqparse.parse_args()
        uploaded_file = args['file']
        created = not storage().exists(name, extension)
        storage().save(name, extension, uploaded_file.read())
        return Response('', 201 if created else 200)

    @requires_auth
    def delete(self, project, name, extension):
        if storage().exists(project, name, extension):
            storage().delete(project, name, extension)
            return Response('', 200)
        raise NotFound()

    def get(self, name, extension):
        image = storage().get(name, extension)
        return _serve_image(image, extension)


class ManipulatedImageAPI(Resource):
    """
    API that supports GET for manipulated images.
    """

    def get(self, name, mode, width, height, extension):
        try:
            image = storage().get(name, extension, mode, (int(width), int(height)))
        except ValueError:
            raise NotFound()
        return _serve_image(image, extension)


api.add_resource(UploadAPI, '/images/')
api.add_resource(ImageAPI, '/images/<name>.<extension>')
api.add_resource(ManipulatedImageAPI, '/images/<name>@<mode>-<width>x<height>.<extension>')

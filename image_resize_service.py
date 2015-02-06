import mimetypes
from functools import wraps
import os

from flask import Flask, render_template, send_file, request, url_for, Response
from werkzeug.exceptions import NotFound
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from flask.ext.restful import Api, Resource, reqparse, fields, marshal_with
from flask_restful_swagger import swagger
from flask_cors import CORS


app = Flask(__name__)

app.config.from_pyfile('default.cfg', silent=True)
app.config.from_pyfile('production.cfg', silent=True)
__storage = None
api = swagger.docs(Api(app), apiVersion='0.1', basePath=app.config['BASEPATH'])
cors = CORS(app, resources={r"/upload": {"origins": "*"}})


@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept, Cache-Control, Authorization'
    return response


def _storage():
    """returns access to the storage (save_image(), get() and exists())"""
    global __storage
    if not __storage:
        if app.config['STORAGE'] == 'FILESYSTEM':
            from storage.filesystem import FileImageStorage

            __storage = FileImageStorage(
                app.config['FILESYSTEM_STORAGE_DIR'])
        elif app.config['STORAGE'] == 'APPENGINE':
            from storage.appengine_datastore import DatastoreImageStorage

            __storage = DatastoreImageStorage()
    return __storage


def _fit_image(image, size):
    image.thumbnail(size, Image.ANTIALIAS)
    return image


def _crop_image(image, size):
    im = ImageOps.fit(image, size, Image.ANTIALIAS, 0.0, (0.5, 0.5))
    return im


def _manipulated_image(project, name, extension, mode, size):
    if not size in app.config['PROJECTS'][project]["size"]:
        raise NotFound()
    storage_mode = "%s-%s" % (mode, size)

    if _storage().exists(project, name, extension, storage_mode):
        image = _storage().get(project, name, extension, storage_mode)
    else:
        original_image = Image.open(_original_image(project, name, extension))
        size_value = app.config['PROJECTS'][project]["size"][size]
        # module = sys.modules(__name__)
        # func = getattr(module, '_'+mode+'_image')
        # manipulated_image = func(image, size_value)
        if mode == "fit":
           manipulated_image = _fit_image(original_image, size_value)
        else:
           manipulated_image = _crop_image(original_image, size_value)
        image = _storage().save_image(project, name, extension, manipulated_image, storage_mode)
    return _serve_image(image, extension)


def _original_image(project, name, extension):
    if not _storage().exists(project, name, extension):
        raise NotFound()
    return _storage().get(project, name, extension)


def _serve_image(image_file, extension):
    mime_type = mimetypes.types_map['.%s' % extension]
    return send_file(image_file, mimetype=mime_type, add_etags=False)


def _check_auth(username, password, project):
    """This function is called to check if a username /
    password combination is valid.
    """
    if project not in app.config['PROJECTS']:
        return False
    correct_user, correct_pass = app.config['PROJECTS'][project]['auth']
    return username == correct_user and password == correct_pass


def _check_auth_token(origin, token, project):
    if project not in app.config['PROJECTS']:
        return False
    correct_origin, correct_token = app.config['PROJECTS'][project]['auth_token']
    return token == correct_token and origin == correct_origin


def _authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login using your credentials and a valid PROJECT',

        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


"""
    setup demo project, create all directories if FILESYSTEM is used as storage...
"""
storage = _storage()
if app.config['STORAGE'] == 'FILESYSTEM' and 'demo_project' in app.config['PROJECTS']:
    project_dir = _storage().project_dir('demo_project')
    if not os.path.isfile(os.path.join(project_dir, "welcome.jpg")):
        with open(app.config['BASE_DIR'] + '/test_images/jpg_image.jpg', 'r') as f:
            storage.save('demo_project', "welcome", "jpg", f.read())


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # temp workaround to make this decorator work with functions
        # and the restful class TODO: fix this
        project = kwargs['project'] if 'project' in kwargs else request.form[
            'project']

        #check if it has auth token
        auth_header = request.headers.get('Authorization')
        origin = request.headers.get('Origin')
        if auth_header is not None and origin is not None and auth_header.startswith('Token'):
            #get the origin header
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

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/img/<project>/<name>.<extension>', methods=['GET'])
def serve_original_image(project, name, extension):
    image = _original_image(project, name, extension)
    return _serve_image(image, extension)


@app.route('/img/<project>/<name>@fit-<size>.<extension>', methods=['GET'])
def serve_fitted_image(project, name, size, extension):
    return _manipulated_image(project, name, extension, "fit", size)

@app.route('/img/<project>/<name>@crop-<size>.<extension>', methods=['GET'])
def serve_cropped_image(project, name, size, extension):
    return _manipulated_image(project, name, extension, "crop", size)



@app.route('/uploadform', methods=['GET'])
def upload_form():
    return render_template('upload.html')


@swagger.model
class UploadResponse:
    resource_fields = {
        'status': fields.String,
        'message': fields.String(default=''),
        'url': fields.String
    }


@swagger.model
class DeleteResponse:
    resource_fields = {
        'status': fields.String,
        'message': fields.String(default='')
    }


def _delete_manipulated_images():
    pass


def _save_to_storage(uploaded_file, project, name, extension):
    if not extension.lower() in app.config['ALLOWED_EXTENSIONS']:
        return _upload_json_response(False,
                                     message='unsupported file extension.')
    try:
        uploaded_file.seek(0)
        im = Image.open(uploaded_file)
        _storage().save_image(project, name, extension, im)
        return _upload_json_response(True,
                                     url=url_for('serve_original_image',
                                                 project=project, name=name,
                                                 extension=extension))
    except IOError:
        return _upload_json_response(False,
                                     message='your uploaded binary data does '
                                             'not represent a recognized image format.')


class UploadAPI(Resource):
    """
    API that represents the /upload resource. deprecated by PUT /api/v1.0/
    """
    decorators = [requires_auth]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('file', type=file, required=True,
                                   help='No file provided', location='files')
        self.reqparse.add_argument('project', type=str, required=True,
                                   help='no or invalid project provided',
                                   choices=set(app.config['PROJECTS'].keys()))
        super(UploadAPI, self).__init__()

    @swagger.operation(
        notes='create a new image. filename is chosen by the server',
        responseClass=UploadResponse.__name__,
        nickname='upload',
        parameters=[
            {
                "name": "project",
                "description": "the project to which you want to upload",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "form"
            },
            {
                "name": "file",
                "description": "an image uploaded using multipart-formdata",
                "required": True,
                "allowMultiple": False,
                "dataType": file.__name__,
                "paramType": "body"
            }
        ],
        responseMessages=[
            {
                "code": 201,
                "message": "Created."
            },
            {
                "code": 500,
                "message": "Invalid input"
            }
        ]
    )

    @marshal_with(UploadResponse.resource_fields)
    def post(self):
        args = self.reqparse.parse_args()
        uploaded_file = args['file']
        project = args['project']
        filename, extension = secure_filename(uploaded_file.filename).rsplit(
            '.', 1)
        return _save_to_storage(uploaded_file, project, filename, extension)


class ImageAPI(Resource):
    """
    API that supports PUT and DELETE for images.
    """
    decorators = [requires_auth]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('file', type=file, required=True,
                                   help='No file provided', location='files')
        super(ImageAPI, self).__init__()

    @swagger.operation(
        notes='create or overwrite an image',
        responseClass=UploadResponse.__name__,
        nickname='put image',
        parameters=[
            {
                "name": "file",
                "description": "an image uploaded using multipart-formdata",
                "required": True,
                "allowMultiple": False,
                "dataType": "file",
                "paramType": "body"
            },
            {
                "name": "project",
                "description": "the project under which to create the img",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "path"
            },
            {
                "name": "name",
                "description": "the name of the image",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "path"
            },
            {
                "name": "extension",
                "description": "the extension of this image",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "path"
            }
        ],
        responseMessages=[
            {
                "code": 201,
                "message": "Created."
            },
            {
                "code": 500,
                "message": "Invalid input"
            }
        ]
    )
    @marshal_with(UploadResponse.resource_fields)
    def put(self, project, name, extension):
        args = self.reqparse.parse_args()
        if project not in app.config['PROJECTS']:
            return {'status': 'fail',
                    'message': 'invalid project provided'}, 500
        uploaded_file = args['file']
        return _save_to_storage(uploaded_file, project, name, extension)

    @swagger.operation(
        notes='delete existing image',
        responseClass=DeleteResponse.__name__,
        nickname='delete image',
        parameters=[
            {
                "name": "project",
                "description": "the project under which to create the img",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "path"
            },
            {
                "name": "name",
                "description": "the name of the image",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "path"
            },
            {
                "name": "extension",
                "description": "the extension of this image",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "path"
            }
        ],
        responseMessages=[
            {
                "code": 200,
                "message": "Deleted."
            },
            {
                "code": 404,
                "message": "Image does not exist."
            },
            {
                "code": 500,
                "message": "Invalid input"
            }
        ]
    )
    @marshal_with(DeleteResponse.resource_fields)
    def delete(self, project, name, extension):
        if project not in app.config['PROJECTS']:
            return {'status': 'fail',
                    'message': 'this project does not exist'}, 500
        success = _storage().delete(project, name, extension)
        code = 200 if success else 404
        return {'status': 'ok' if success else 'fail',
                'message': 'deleted' if success else ''}, code


api.add_resource(UploadAPI, '/upload')
api.add_resource(ImageAPI, '/api/v1.0/images/<project>/<name>.<extension>')

if __name__ == '__main__':
    if app.config['STORAGE'] == 'APPENGINE':
        raise Exception(
            'can\'t use flask dev server with appengine storage! check config')
    app.run()

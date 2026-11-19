import hmac
import werkzeug
from functools import wraps

from flask import Flask, send_file, request, Response, render_template
from flask_restful import Api, Resource, reqparse, fields, marshal_with
from flask_cors import CORS
from PIL import Image as PILImage
from werkzeug.exceptions import BadRequest, NotFound, Unauthorized
from werkzeug.utils import secure_filename

from image_service import image as image_utils
from image_service.storage import FileSystemStorage


CONFIG_STORAGE_DIR = 'STORAGE_DIRECTORY'

app = Flask(__name__)
app.config.from_pyfile('../config.py', silent=True)
PILImage.MAX_IMAGE_PIXELS = app.config.get('MAX_IMAGE_PIXELS', 25_000_000)
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
        _storage = FileSystemStorage(
            app.config[CONFIG_STORAGE_DIR],
            max_dimension=app.config.get('MAX_IMAGE_DIMENSION', 4096),
        )
    return _storage


def _serve_image(image_file, extension):
    mime_type = image_utils.mime_type_from_extension(extension)
    if mime_type is None:
        image_file.close()
        raise NotFound()
    response = send_file(image_file, mimetype=mime_type, etag=False)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = (
        "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
    )
    response.headers['Content-Disposition'] = 'inline'
    return response


def _validate_upload(binary_data, extension):
    try:
        image_utils.validate_image_data(
            binary_data,
            extension,
            max_pixels=app.config.get('MAX_IMAGE_PIXELS', 25_000_000),
        )
    except ValueError as exc:
        raise BadRequest(str(exc))


def _check_auth_token(origin, token):
    auth_token = app.config.get('AUTH_TOKEN')
    if not auth_token or len(auth_token) != 2 or not token:
        return False
    expected_origin, expected_token = auth_token
    if not expected_token:
        return False
    token_matches = hmac.compare_digest(expected_token, token)
    origin_matches = expected_origin == '*' or (
        origin is not None and hmac.compare_digest(expected_origin, origin)
    )
    return origin_matches and token_matches


def _check_auth_basic(username, password):
    auth_basic = app.config.get('AUTH_BASIC')
    if not auth_basic or len(auth_basic) != 2 or username is None or password is None:
        return False
    correct_user, correct_pass = auth_basic
    if not correct_user or not correct_pass:
        return False
    user_matches = hmac.compare_digest(correct_user, username)
    pass_matches = hmac.compare_digest(correct_pass, password)
    return user_matches and pass_matches


@app.route('/')
def index():
    if app.config['ENABLE_DEMO']:
        return render_template('demo.html')
    return Response('Nothing to see here ;)', 404)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        origin = request.headers.get('Origin')
        if auth_header is not None:
            scheme, sep, credentials = auth_header.strip().partition(' ')
            if sep and scheme == 'Token':
                token = credentials.strip()
                if token and ' ' not in token and _check_auth_token(origin, token):
                    return f(*args, **kwargs)
            elif sep and scheme == 'Basic':
                auth = request.authorization
                if auth is not None and _check_auth_basic(auth.username, auth.password):
                    return f(*args, **kwargs)
        raise Unauthorized()
    return decorated


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
        sanitized = secure_filename(uploaded_file.filename or '')
        if '.' not in sanitized:
            raise BadRequest('Filename must include an image extension')
        filename, extension = sanitized.rsplit('.', 1)
        extension = extension.lower()
        data = uploaded_file.read()
        _validate_upload(data, extension)
        filename = storage().safe_name(filename, extension)
        storage().save(filename, extension, data)
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
        extension = extension.lower()
        data = uploaded_file.read()
        _validate_upload(data, extension)
        created = not storage().exists(name, extension)
        storage().save(name, extension, data)
        return Response('', 201 if created else 200)

    @requires_auth
    def delete(self, name, extension):
        extension = extension.lower()
        if image_utils.mime_type_from_extension(extension) is None:
            raise NotFound()
        if storage().exists(name, extension):
            storage().delete(name, extension)
            return Response('', 200)
        raise NotFound()

    def get(self, name, extension):
        extension = extension.lower()
        if image_utils.mime_type_from_extension(extension) is None:
            raise NotFound()
        image = storage().get(name, extension)
        return _serve_image(image, extension)


class ManipulatedImageAPI(Resource):
    """
    API that supports GET for manipulated images.
    """

    def get(self, name, mode, width, height, extension):
        extension = extension.lower()
        if image_utils.mime_type_from_extension(extension) is None:
            raise NotFound()
        try:
            size = (int(width), int(height))
        except ValueError:
            raise NotFound()
        max_dim = app.config.get('MAX_IMAGE_DIMENSION', 4096)
        if size[0] < 1 or size[1] < 1 or size[0] > max_dim or size[1] > max_dim:
            raise BadRequest('Requested dimensions must be between 1 and %d' % max_dim)
        allowed_dims = app.config.get('ALLOWED_DIMENSIONS')
        if allowed_dims is not None and size not in allowed_dims:
            raise BadRequest('Requested dimensions are not allowed')
        try:
            image = storage().get(name, extension, mode, size)
        except ValueError:
            raise NotFound()
        return _serve_image(image, extension)


api.add_resource(UploadAPI, '/images/')
api.add_resource(ImageAPI, '/images/<name>.<extension>')
api.add_resource(ManipulatedImageAPI, '/images/<name>@<mode>-<width>x<height>.<extension>')

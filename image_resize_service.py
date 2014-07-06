import os.path as op
import io
import tempfile

from functools import wraps
from flask import Flask, render_template, send_file, request, url_for, Response
from werkzeug.exceptions import NotFound
from PIL import Image
from werkzeug.utils import secure_filename
from flask.ext.restful import Api, Resource, reqparse, fields, marshal_with
from flask_restful_swagger import swagger

app = Flask(__name__)
config = op.join(app.root_path, 'production.cfg')
app.config.from_pyfile(config)
__storage = None
api = swagger.docs(Api(app), apiVersion='0.1')


def _storage():
    """returns access to the storage (save_image(), get() and exists())"""
    global __storage
    if not __storage:
        if app.config['STORAGE'] == 'FILESYSTEM':
            from storage.filesystem import FileImageStorage

            __storage = FileImageStorage(
                app.config['FILESYSTEM_STORAGE_SOURCE_DIR'],
                app.config['FILESYSTEM_STORAGE_RESIZED_DIR'])
        elif app.config['STORAGE'] == 'APPENGINE':
            from storage.appengine_datastore import DatastoreImageStorage

            __storage = DatastoreImageStorage()
    return __storage


def _calc_size(target_size, image):
    """
    calculates the new image size such that it fits into the target_size
    bounding box and the proportions are still ok.
    :param target_size: a tuple containing (max_width, max_height) as ints. \
    the bounding box.
    :param image: a PIL or Pillow image
    :return: a tuple containing the new width and height as ints.
    """
    max_width, max_height = target_size
    width, height = image.size
    if max_width >= width and max_height >= height:
        return image.size  # no resize needed
    scale = min(max_width / float(width), max_height / float(height))
    return int(width * scale), int(height * scale)


def _resize_image(project, name, extension, size):
    """
    resizes the image identified by project, name and extension and saves it
    in the storage.
    :param project: a valid project.
        YOU NEED TO HAVE CHECKED THAT THIS PROJECT EXISTS
    :param name: the image name (prefix without dimension or extension)
    :param extension: the file extension
    :param size: the name of the new size as a string
        (e.g "large", "small" depends on your .cfg file)
    """
    if not _storage().exists(project, name, extension):
        raise NotFound()
    im = Image.open(_storage().get(project, name, extension))
    im = im.resize(
        _calc_size(app.config['PROJECTS'][project]['dimensions'][size], im))
    _storage().save_image(project, name, extension, im, size)
    # not cool, appengines PIL version needs a tempfile and flasks
    # send_file has trouble with it.: tempfile -> BytesIO
    ret_file = tempfile.TemporaryFile()
    im.save(ret_file, 'JPEG')
    ret_file.seek(0)
    return io.BytesIO(ret_file.read())


def _serve_image(project, name, size, extension):
    if project not in app.config['PROJECTS'] \
            or (size and size not in app.config['PROJECTS'][project][
                'dimensions']):
        raise NotFound()
    if not _storage().exists(project, name, extension, size):
        resized_file = _resize_image(project, name, extension, size)
        return send_file(resized_file, mimetype='image/jpeg')
    return send_file(_storage().get(project, name, extension, size),
                     mimetype='image/jpeg')


def _check_auth(username, password, project):
    """This function is called to check if a username /
    password combination is valid.
    """
    if project not in app.config['PROJECTS']:
        return False
    correct_user, correct_pass = app.config['PROJECTS'][project]['auth']
    return username == correct_user and password == correct_pass


def _authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login using your credentials and a valid PROJECT',

        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        # temp workaround to make this decorator work with functions
        # and the restful class TODO: fix this
        project = kwargs['project'] if 'project' in kwargs else request.form[
            'project']
        if not auth or not _check_auth(auth.username, auth.password, project):
            return _authenticate()
        return f(*args, **kwargs)

    return decorated


def _upload_json_response(success, **kwargs):
    res_dict = dict(status='ok' if success else 'fail')
    res_dict.update(kwargs)
    code = 201 if success else 500
    return res_dict, code


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/img/<project>/<name>.<extension>', methods=['GET'])
def serve_original_image(project, name, extension):
    return _serve_image(project, name, None, extension)


@app.route('/img/<project>/<name>@<size>.<extension>', methods=['GET'])
def serve_resized_image(project, name, size, extension):
    """
    serves the url /img/project/name@size.extension
    e.g /img/demo_project/welcome@small.jpg either returns an image of
    mimetype image/jpeg or a NotFound() 404 error
    :param project: a project that exists in your production.cfg file
    :param name: the image name
    :param size: the dimension. should be configured in your config file
    :param extension: the image file extension
    :return: an image or a 404 error
    """
    return _serve_image(project, name, size, extension)


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


def _save_to_storage(uploaded_file, project, name, extension):
    """
    puts the given file into the storage. used for POST and PUT service.
    an already existing image is overwritten. new images are created.
    :param uploaded_file: a file descriptor
    :param project: the already validated project.
        ITS YOUR TURN TO CHECK THAT THIS PROJECT EXISTS!
    :param name: name to be used
    :param extension: extension to be used
    :return:
    """
    if not extension.lower() in app.config['ALLOWED_EXTENSIONS']:
        return _upload_json_response(False,
                                     message='unsupported file extension.')
    try:
        uploaded_file.seek(0)
        im = Image.open(uploaded_file)
        jpg_image = tempfile.TemporaryFile()
        im.save(jpg_image, 'JPEG')
        jpg_image.seek(0)
        _storage().save(project, name, extension, jpg_image.read())
        return _upload_json_response(True,
                                     url=url_for('serve_original_image',
                                                 project=project, name=name,
                                                 extension=extension))
    except IOError:
        return _upload_json_response(False,
                                     message='your uploaded binary data does \
                                     not represent a recognized image format.')


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

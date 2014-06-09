import os.path as op
import tempfile

from flask import Flask, render_template, send_file
from werkzeug.exceptions import NotFound
from PIL import Image


app = Flask(__name__)
config = op.join(app.root_path, 'production.cfg')
app.config.from_pyfile(config)
__storage = None


def _storage():
    """returns access to the storage (save(), get() and exists())"""
    global __storage
    if not __storage:
        if app.config['STORAGE'] == 'FILESYSTEM':
            from storage.filesystem import FileImageStorage
            __storage = FileImageStorage(app.config['FILESYSTEM_STORAGE_SOURCE_DIR'],
                                         app.config['FILESYSTEM_STORAGE_RESIZED_DIR'])
        elif app.config['STORAGE'] == 'APPENGINE':
            from storage.appengine_datastore import DatastoreImageStorage

            __storage = DatastoreImageStorage()
    return __storage


def _calc_size(target_size, image):
    """
    calculates the new image size such that it fits into the target_size bounding box and the proportions are still ok.
    :param target_size: a tuple containing (max_width, max_height) as ints. the bounding box.
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
    resizes the image identified by project, name and extension and saves it to the RESIZED_DIR.
    :param project: a valid project. YOU NEED TO HAVE CHECKED THAT THIS PROJECT EXISTS
    :param name: the image name (prefix without dimension or extension)
    :param extension: the file extension
    :param size: the name of the new size as a string (e.g "large", "small" depends on your .cfg file)
    """
    if not _storage().exists(project, name, extension):
        raise NotFound()
    im = Image.open(_storage().get(project, name, extension))
    im = im.resize(_calc_size(app.config['PROJECTS'][project][size], im))
    # target_image = io.BytesIO()  # app engines PIL version has trouble with this...
    target_image = tempfile.TemporaryFile()
    im.save(target_image, 'JPEG')
    target_image.seek(0)
    _storage().save(project, name, extension, target_image.read(), size)
    target_image.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/img/<project>/<name>@<size>.<extension>', methods=['GET'])
def serve_image(project, name, size, extension):
    """
    serves the url /img/project/name@size.extension e.g /img/demo_project/welcome@small.jpg
    either returns an image of mimetype image/jpeg or a NotFound() 404 error
    :param project: a project that exists in your production.cfg file
    :param name: the image name
    :param size: the dimension. should be configured in your config file
    :param extension: the image file extension
    :return: an image or a 404 error
    """
    if not project in app.config['PROJECTS'] or not size in app.config['PROJECTS'][project]:
        raise NotFound()
    if not _storage().exists(project, name, extension, size):
        _resize_image(project, name, extension, size)
    return send_file(_storage().get(project, name, extension, size), mimetype='image/jpeg')


if __name__ == '__main__':
    app.run()
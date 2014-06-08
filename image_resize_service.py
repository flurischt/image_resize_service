import os.path as op
import io
from werkzeug.utils import secure_filename
from flask import Flask, render_template, send_file, safe_join
from werkzeug.exceptions import NotFound
from PIL import Image


app = Flask(__name__)
config = op.join(app.root_path, 'production.cfg')
app.config.from_pyfile(config)


class ImageStorage(object):
    """represents an image storage"""

    @staticmethod
    def exists(cls, project, name, extension, size=None):
        """true if image is in this storage, false otherwise"""
        raise NotImplemented()

    @staticmethod
    def save(cls, project, name, extension, binary_image_data, size=None):
        """saves the binary_image_data by creating or overwriting the project-name-extension-size images"""
        raise NotImplemented()

    @staticmethod
    def get(cls, project, name, extension, size=None):
        """returns a filedescriptor to the image (file, or io)"""
        raise NotImplemented()


class FileImageStorage(ImageStorage):
    @staticmethod
    def exists(project, name, extension, size=None):
        return op.isfile(FileImageStorage._path_to_image(project, name, extension, size=size))

    @staticmethod
    def save(project, name, extension, binary_image_data, size=None):
        with open(FileImageStorage._path_to_image(project, name, extension, size), 'w') as f:
            f.write(binary_image_data)

    @staticmethod
    def get(project, name, extension, size=None):
        return file(FileImageStorage._path_to_image(project, name, extension, size), 'r')

    @staticmethod
    def _path_to_image(project, name, extension, size=None):
        """
        constructs a path to an image.
        if a size is set, this returns a path to resized_dir. otherwise a path to source_dir is returned.
        :param name: the image name (the leading part before the dimension and without extension)
        :param extension: the file extension of the image. probably jpg
        :param project: the project name THIS FUNCTION DOES NOT CHECK IF THAT PROJECT EXISTS
        :param size: a tuple containing max_width and max_height as ints
        :return: the path to the image
        """
        if size:
            filename = secure_filename('%s_%s.%s' % (name, size, extension))
            directory = app.config['RESIZED_DIR']
        else:
            filename = secure_filename(name + '.' + extension)
            directory = app.config['SOURCE_DIR']
        directory = directory + '/' + project
        return safe_join(directory, filename)


def _storage():
    """returns access to the storage (save(), get() and exists())"""
    # TODO make this configurable
    return FileImageStorage


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
    target_image = io.BytesIO()
    im.save(target_image, 'JPEG')
    target_image.seek(0)
    _storage().save(project, name, extension, target_image.read(), size)


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

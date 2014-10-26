import os.path as op
import os

from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from flask import safe_join

from storage import ImageStorage


class FileImageStorage(ImageStorage):

    def __init__(self, SOURCE_DIR, RESIZED_DIR):
        self.SOURCE_DIR = SOURCE_DIR
        self.RESIZED_DIR = RESIZED_DIR

    def exists(self, project, name, extension, size=None):
        return op.isfile(self._path_to_image(project, name, extension, size=size))

    def save(self, project, name, extension, binary_image_data, size=None):
        with open(self._path_to_image(project, name, extension, size), 'wb') as f:
            f.write(binary_image_data)

    def get(self, project, name, extension, size=None):
        filename = self._path_to_image(project, name, extension, size)
        if op.isfile(filename):
            return file(filename, 'rb')
        else:
            raise NotFound()

    def delete(self, project, name, extension, size=None):
        if not self.exists(project, name, extension, size):
            return False
        path_to_image = self._path_to_image(project, name, extension, size)
        try:
            os.remove(path_to_image)
            return not self.exists(project, name, extension, size)
        except OSError:
            return False

    def _path_to_image(self, project, name, extension, size=None):
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
            directory = self.RESIZED_DIR
        else:
            filename = secure_filename(name + '.' + extension)
            directory = self.SOURCE_DIR
        directory = directory + project
        return safe_join(directory, filename)
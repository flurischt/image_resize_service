from abc import abstractmethod
from werkzeug.utils import secure_filename
from flask import safe_join
from werkzeug.exceptions import NotFound

import tempfile
import os
import utils


class Storage(object):
    """represents a storage"""

    @abstractmethod
    def exists(self, project, name, extension, size=None):
        """true if image is in this storage, false otherwise"""
        pass

    def save_image(self, project, name, extension, pil_image, mode=None):
        """put the given pil image to the storage"""
        binary = tempfile.TemporaryFile()
        pil_image.save(binary, utils.pil_format_from_file_extension(extension))
        binary.seek(0)
        self.save(project, name, extension, binary.read(), mode)
        binary.seek(0)
        return binary

    @abstractmethod
    def save(self, project, name, extension, binary_data, mode=None):
        """saves the binary_image_data by creating or overwriting the project-name-extension-size images"""
        pass

    @abstractmethod
    def get(self, project, name, extension, mode=None):
        """returns a filedescriptor to the image (file, or io)"""
        pass

    @abstractmethod
    def delete(self, project, name, extension, mode=None):
        """delete the image"""
        pass


class FileSystemStorage(Storage):

    def __init__(self, image_dir):
        self._image_dir = image_dir
        if not os.path.isdir(self._image_dir):
            os.makedirs(self._image_dir)

    def resize_dir(self, project):
        resize_dir = os.path.join(self._image_dir, project, "_resized")
        if not os.path.isdir(resize_dir):
            os.makedirs(resize_dir)
        return resize_dir

    def project_dir(self, project):
        project_dir = os.path.join(self._image_dir, project)
        if not os.path.isdir(project_dir):
            os.makedirs(project_dir)
        return project_dir

    def exists(self, project, name, extension, mode=None):
        return os.path.isfile(self._path_to_image(project, name, extension, mode))

    def save(self, project, name, extension, binary_image_data, mode=None):
        with open(self._path_to_image(project, name, extension, mode), 'wb') as f:
            f.write(binary_image_data)

    def get(self, project, name, extension, mode=None):
        filename = self._path_to_image(project, name, extension, mode)
        if os.path.isfile(filename):
            return file(filename, 'rb')
        else:
            raise NotFound()

    def delete(self, project, name, extension, mode=None):
        if not self.exists(project, name, extension, mode):
            return False
        path_to_image = self._path_to_image(project, name, extension, mode)
        try:
            os.remove(path_to_image)
            return not self.exists(project, name, extension, mode)
        except OSError:
            return False

    def _path_to_image(self, project, name, extension, mode=None):
        """
        constructs a path to an image.
        if a size is set, this returns a path to resized_dir. otherwise a path to source_dir is returned.
        :param name: the image name (the leading part before the dimension and without extension)
        :param extension: the file extension of the image. probably jpg
        :param project: the project name THIS FUNCTION DOES NOT CHECK IF THAT PROJECT EXISTS
        :param size: a tuple containing max_width and max_height as ints
        :return: the path to the image
        """

        if mode:
            filename = secure_filename('%s_%s.%s' % (name, mode, extension))
            directory = self.resize_dir(project)
        else:
            filename = secure_filename(name + '.' + extension)
            directory = self.project_dir(project)
        return safe_join(directory, filename)
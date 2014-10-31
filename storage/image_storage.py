import tempfile
from abc import abstractmethod

import utils


class ImageStorage(object):
    """represents an image storage"""

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
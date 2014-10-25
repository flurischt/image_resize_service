import tempfile
from abc import abstractmethod


class ImageStorage(object):
    """represents an image storage"""

    @abstractmethod
    def exists(self, project, name, extension, size=None):
        """true if image is in this storage, false otherwise"""
        pass

    def save_image(self, project, name, extension, pil_image, size=None):
        """put the given pil image to the storage"""
        f = tempfile.TemporaryFile()
        img_format = pil_image.format if pil_image.format is not None else extension.upper()
        img_format = "JPEG" if img_format == "JPG" else img_format

        pil_image.save(f, img_format)
        f.seek(0)
        self.save(project, name, extension, f.read(), size)

    @abstractmethod
    def save(self, project, name, extension, binary_data, size=None):
        """saves the binary_image_data by creating or overwriting the project-name-extension-size images"""
        pass

    @abstractmethod
    def get(self, project, name, extension, size=None):
        """returns a filedescriptor to the image (file, or io)"""
        pass

    @abstractmethod
    def delete(self, project, name, extension, size=None):
        """delete the image"""
        pass
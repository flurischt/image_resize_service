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
class ImageStorage(object):
    """represents an image storage"""

    def exists(self, project, name, extension, size=None):
        """true if image is in this storage, false otherwise"""
        raise NotImplemented()

    def save(self, project, name, extension, binary_image_data, size=None):
        """saves the binary_image_data by creating or overwriting the project-name-extension-size images"""
        raise NotImplemented()

    def get(self, project, name, extension, size=None):
        """returns a filedescriptor to the image (file, or io)"""
        raise NotImplemented()
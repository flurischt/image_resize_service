import shutil
import os

from werkzeug.utils import secure_filename
from flask import safe_join
from werkzeug.exceptions import NotFound

import image


class FileSystemStorage(object):
    def __init__(self, image_dir):
        self._image_dir = image_dir
        if not os.path.isdir(self._image_dir):
            os.makedirs(self._image_dir)

    def _check_mode_size(self, mode=None, size=None):
        if mode is not None and size is None or mode is None and size is not None:
            raise ValueError("if mode is given, a size must be given too")
        if mode is not None and (not mode == "crop" and not mode == "fit"):
            raise ValueError("only fit or crop allowed for mode")

    def exists(self, project, name, extension, mode=None, size=None):
        return os.path.isfile(self._path_to_image(project, name, extension, mode, size))

    def save(self, project, name, extension, binary_image_data, mode=None, size=None):
        if self.exists(project, name, extension, mode, size):
            self.delete(project, name, extension, mode, size)
        self._check_mode_size(mode, size)
        with open(self._path_to_image(project, name, extension, mode, size), 'wb') as f:
            f.write(binary_image_data)

    def get(self, project, name, extension, mode=None, size=None):
        self._check_mode_size(mode, size)

        image_path = self._path_to_image(project, name, extension, mode, size)
        if mode is not None and not os.path.isfile(image_path):
            original_image = self.get(project, name, extension)
            manipulated_image = None
            if mode == "crop":
                manipulated_image = image.crop_image(original_image, size)
            elif mode == "fit":
                manipulated_image = image.fit_image(original_image, size)
            self.save(project, name, extension, manipulated_image.read(), mode, size)

        if os.path.isfile(image_path):
            return file(image_path, 'rb')
        else:
            raise NotFound()

    def delete(self, project, name, extension, mode=None, size=None):
        path_to_image = self._path_to_image(project, name, extension, mode, size)
        try:
            os.remove(path_to_image)
        except OSError:
            raise NotFound()
        # only delete all files when no mode and size are given...
        if mode is None and size is None:
            manipulated_dir = self._manipulated_directory(project, name, extension)
            if os.path.isdir(manipulated_dir):
                shutil.rmtree(self._manipulated_directory(project, name, extension))

    def safe_name(self, project, name, extension):
        counter = 1
        safe_name = name
        while (self.exists(project, safe_name, extension)):
            safe_name = "%s-%d" % (name, counter)
            counter += 1
        return safe_name

    def _project_dir(self, project):
        project_dir = os.path.join(self._image_dir, project)
        return project_dir

    def _manipulated_directory(self, project, name, extension):
        return safe_join(self._project_dir(project), "_%s.%s" % (name, extension))

    def _path_to_image(self, project, name, extension, mode=None, size=None):
        if mode:
            filename = secure_filename('%s-%dx%d.%s' % (mode, size[0], size[1], extension))
            directory = self._manipulated_directory(project, name, extension)
        else:
            filename = secure_filename(name + '.' + extension)
            directory = self._project_dir(project)

        if not os.path.isdir(directory):
            os.makedirs(directory)

        return safe_join(directory, filename)
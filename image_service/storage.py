import os
import os.path as op
import re
import shutil
import tempfile

from werkzeug.security import safe_join
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound

from image_service import image


VALID_NAME_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9_-]|\.(?!\.)){0,127}$')
VALID_EXTENSION_RE = re.compile(r'^[A-Za-z0-9]{1,10}$')


class FileSystemStorage(object):
    def __init__(self, image_dir, max_dimension=4096):
        self._image_dir = op.realpath(image_dir)
        self._max_dimension = max_dimension
        os.makedirs(self._image_dir, exist_ok=True)

    def _validate_name_extension(self, name, extension):
        if not isinstance(name, str) or not isinstance(extension, str):
            raise ValueError('name and extension must be strings')
        if not name or name.endswith('.') or not VALID_NAME_RE.match(name):
            raise ValueError('Invalid image name')
        if not extension or not VALID_EXTENSION_RE.match(extension):
            raise ValueError('Invalid image extension')
        normalized_ext = extension.lower()
        canonical = '%s.%s' % (name, normalized_ext)
        if secure_filename(canonical) != canonical:
            raise ValueError('Invalid image name or extension')
        return name, normalized_ext

    def _safe_child_path(self, base_dir, *parts):
        joined = safe_join(base_dir, *parts)
        if joined is None:
            raise ValueError('Unsafe storage path')
        real_base = op.realpath(base_dir)
        real_target = op.realpath(joined)
        if real_target == real_base or not real_target.startswith(real_base + os.sep):
            raise ValueError('Storage path escapes base directory')
        return joined

    def _check_mode_size(self, mode=None, size=None):
        if (mode or size) and (not mode or not size):
            raise ValueError('mode and size bust be given both or neither')
        if mode and mode not in ('crop', 'fit'):
            raise ValueError('only fit or crop allowed for mode')
        if size is not None:
            if not isinstance(size, (tuple, list)) or len(size) != 2:
                raise ValueError('size must be a (width, height) pair')
            width, height = size
            if (isinstance(width, bool) or isinstance(height, bool)
                    or not isinstance(width, int) or not isinstance(height, int)):
                raise ValueError('width and height must be integers')
            if width < 1 or height < 1 or width > self._max_dimension or height > self._max_dimension:
                raise ValueError('width and height must be between 1 and %d' % self._max_dimension)

    def _write_temp_file(self, directory, binary_image_data):
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.tmp-')
        try:
            with os.fdopen(fd, 'wb') as tmp_file:
                tmp_file.write(binary_image_data)
            return tmp_path
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def exists(self, name, extension, mode=None, size=None):
        return op.isfile(self._path_to_image(name, extension, mode, size))

    def save(self, name, extension, binary_image_data, mode=None, size=None):
        self._check_mode_size(mode, size)
        image_path = self._path_to_image(name, extension, mode, size)
        directory = op.dirname(image_path)
        tmp_path = self._write_temp_file(directory, binary_image_data)
        try:
            os.replace(tmp_path, image_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        if mode is None and size is None:
            manipulated_dir = self._manipulated_directory(name, extension)
            if op.isdir(manipulated_dir):
                shutil.rmtree(manipulated_dir, ignore_errors=True)

    def save_unique(self, name, extension, binary_image_data):
        name, extension = self._validate_name_extension(name, extension)
        tmp_path = self._write_temp_file(self._image_dir, binary_image_data)
        try:
            counter = 0
            while True:
                candidate = name if counter == 0 else '%s-%d' % (name, counter)
                target_path = self._path_to_image(candidate, extension)
                try:
                    os.link(tmp_path, target_path)
                    return candidate
                except FileExistsError:
                    counter += 1
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def get(self, name, extension, mode=None, size=None):
        self._check_mode_size(mode, size)
        image_path = self._path_to_image(name, extension, mode, size)
        if mode and not op.isfile(image_path):
            with self.get(name, extension) as original_image:
                if mode == 'crop':
                    manipulated_image = image.crop_image(original_image, size)
                elif mode == 'fit':
                    manipulated_image = image.fit_image(original_image, size)
            with manipulated_image:
                self.save(name, extension, manipulated_image.read(), mode, size)

        if op.isfile(image_path):
            return open(image_path, 'rb')
        else:
            raise NotFound()

    def delete(self, name, extension, mode=None, size=None):
        path_to_image = self._path_to_image(name, extension, mode, size)
        try:
            os.remove(path_to_image)
        except OSError:
            raise NotFound()
        # only delete all files when no mode and size are given...
        if mode is None and size is None:
            manipulated_dir = self._manipulated_directory(name, extension)
            if op.isdir(manipulated_dir):
                shutil.rmtree(manipulated_dir, ignore_errors=True)

    def safe_name(self, name, extension):
        name, extension = self._validate_name_extension(name, extension)
        counter = 1
        safe_name = name
        while self.exists(safe_name, extension):
            safe_name = '%s-%d' % (name, counter)
            counter += 1
        return safe_name

    def _manipulated_directory(self, name, extension):
        name, extension = self._validate_name_extension(name, extension)
        return self._safe_child_path(self._image_dir, '_%s.%s' % (name, extension))

    def _path_to_image(self, name, extension, mode=None, size=None):
        name, extension = self._validate_name_extension(name, extension)
        if mode:
            filename = '%s-%dx%d.%s' % (mode, size[0], size[1], extension)
            directory = self._manipulated_directory(name, extension)
            return self._safe_child_path(directory, filename)
        filename = '%s.%s' % (name, extension)
        return self._safe_child_path(self._image_dir, filename)

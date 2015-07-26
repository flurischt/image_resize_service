import unittest
import os.path as op
import shutil

from PIL import Image as PILImage
from werkzeug.exceptions import NotFound

from image_service.storage import FileSystemStorage


class TestFileSystemStorage(unittest.TestCase):
    """tests the filesystem storage and therefore defines the storage API
       all storages must have the same behaviour as it's tested here.
       see DataStoreStorageTestCase below.
    """

    def setUp(self):
        self.storage_dir = op.join(op.dirname(op.dirname(op.realpath(__file__))), 'test_storage')
        self.storage = FileSystemStorage(self.storage_dir)

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def _test_image_path(self, image_name):
        current_dir = op.dirname(op.realpath(__file__))
        return op.join(current_dir, 'test_images', image_name)

    def test_create_storage_dir(self):
        self.assertTrue(op.exists(self.storage_dir))

    def test_add_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        file_path = op.join(self.storage_dir, '%s.%s' % (image_name, image_extension))
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
        self.assertTrue(op.exists(file_path))

    def test_read_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        file_path = op.join(self.storage_dir, '%s.%s' % (image_name, image_extension))
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
            image_file = self.storage.get(image_name, image_extension)
            image_file.seek(0)
            png_file.seek(0)
            self.assertTrue(file_path, image_file.name)
            self.assertEqual(image_file.read(), png_file.read())

    def test_read_not_existing(self):
        image_name = 'png_image'
        image_extension = 'png'
        self.assertRaises(NotFound, self.storage.get, image_name, image_extension)
        self.assertRaises(NotFound, self.storage.get, image_name, image_extension, 'fit', (200, 200))

    def test_illegal_mode(self):
        self.assertRaises(ValueError, self.storage.get, 'some', 'png', 'crop')
        self.assertRaises(ValueError, self.storage.get, 'some', 'png', None, (200, 200))
        self.assertRaises(ValueError, self.storage.get, 'some', 'png', 'notAllowed', (200, 200))

    def test_save_cropped_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        mode = 'crop'
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read(), mode, (200, 200))
            file_name = '%s-%dx%d.png' % (mode, 200, 200)
            file_path = op.join(self.storage_dir, '_%s.%s/%s' % (image_name,
                                                                      image_extension,
                                                                      file_name))
            self.assertTrue(op.isfile(file_path))

    def test_save_fitted_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        mode = 'fit'
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read(), mode, (200, 200))
            file_name = '%s-%dx%d.png' % (mode, 200, 200)
            file_path = op.join(self.storage_dir, '_%s.%s/%s' % (image_name,
                                                                      image_extension,
                                                                      file_name))
            self.assertTrue(op.isfile(file_path))

    def test_auto_create_cropped(self):
        image_name = 'png_image'
        image_extension = 'png'
        mode = 'crop'
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
            image_file = self.storage.get(image_name, image_extension, mode, (200, 200))
            file_name = '%s-%dx%d.png' % (mode, 200, 200)
            file_path = op.join(self.storage_dir, '_%s.%s/%s' % (image_name,
                                                                      image_extension,
                                                                      file_name))
            self.assertTrue(op.isfile(file_path))
            pil_image = PILImage.open(image_file)
            self.assertEqual((200, 200), pil_image.size)

    def test_auto_create_fit(self):
        image_name = 'png_image'
        image_extension = 'png'
        mode = 'fit'
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
            image_file = self.storage.get(image_name, image_extension, mode, (200, 200))
            file_name = '%s-%dx%d.png' % (mode, 200, 200)
            file_path = op.join(self.storage_dir, '_%s.%s/%s' % (image_name,
                                                                      image_extension,
                                                                      file_name))
            self.assertTrue(op.isfile(file_path))
            pil_image = PILImage.open(image_file)
            self.assertEqual((200, 150), pil_image.size)

    def test_delete_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
            self.storage.get(image_name, image_extension, 'crop', (200, 200))
            self.storage.get(image_name, image_extension, 'fit', (200, 200))
            manipulated_directory = op.join(self.storage_dir,
                                                 '_%s.%s' % (image_name, image_extension))
            original_image_path = op.join(self.storage_dir,
                                               '%s.%s' % (image_name, image_extension))
            self.assertTrue(op.isdir(manipulated_directory))
            self.assertTrue(op.isfile(original_image_path))
            self.storage.delete(image_name, image_extension)
            self.assertFalse(op.isdir(manipulated_directory))
            self.assertFalse(op.isfile(manipulated_directory))
        self.assertRaises(NotFound, self.storage.get, image_name, image_extension)
        self.assertRaises(NotFound, self.storage.get, image_name, image_extension, 'fit', (200, 200))

    def test_not_existing(self):
        image_name = 'png_image'
        image_extension = 'png'
        self.assertRaises(NotFound, self.storage.delete, image_name, image_extension)

    def test_override_file(self):
        image_name = 'png_image'
        image_extension = 'png'
        mode = 'crop'
        file_name = '%s-%dx%d.png' % (mode, 200, 200)
        file_path = op.join(self.storage_dir, '_%s.%s/%s' % (image_name,
                                                                  image_extension,
                                                                  file_name))
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
            self.storage.get(image_name, image_extension, mode, (200, 200))
            self.assertTrue(op.isfile(file_path))

        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
            self.assertFalse(op.isfile(file_path))

    def test_safe_name(self):
        image_name = 'png_image'
        image_extension = 'png'
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(image_name, image_extension, png_file.read())
        safe_name = self.storage.safe_name(image_name, image_extension)
        self.assertEqual('%s-1' % image_name, safe_name)
        with open(self._test_image_path('%s.%s' % (image_name, image_extension)), 'rb') as png_file:
            self.storage.save(safe_name, image_extension, png_file.read())
        safe_name = self.storage.safe_name(image_name, image_extension)
        self.assertEqual('%s-2' % image_name, safe_name)

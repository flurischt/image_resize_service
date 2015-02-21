import unittest
import os
import shutil

from image_service.storage import FileSystemStorage


class TestFileSystemStorage(unittest.TestCase):
    """tests the filesystem storage and therefore defines the storage API
       all storages must have the same behaviour as it's tested here.
       see DataStoreStorageTestCase below.
    """

    def setUp(self):
        self.storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "test_storage")
        self.storage = FileSystemStorage(self.storage_dir)
        self.project = "UnitTest"

    def tearDown(self):
        shutil.rmtree(self.storage_dir)

    def test_create_storage_dir(self):
        self.assertTrue(os.path.exists(self.storage_dir))

    def test_add_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        file_path = os.path.join(self.storage_dir, self.project, "%s.%s" % (image_name, image_extension))
        with open('test_images/%s.%s' % (image_name, image_extension), 'r') as png_file:
            self.storage.save(self.project, image_name, image_extension, png_file.read())

        self.assertTrue(os.path.exists(file_path))

    def test_read_image(self):
        image_name = 'png_image'
        image_extension = 'png'
        file_path = os.path.join(self.storage_dir, self.project, "%s.%s" % (image_name, image_extension))
        with open('test_images/%s.%s' % (image_name, image_extension), 'r') as png_file:
            self.storage.save(self.project, image_name, image_extension, png_file.read())
            image_file = self.storage.get(self.project, image_name, image_extension)
            image_file.seek(0)
            png_file.seek(0)
            self.assertTrue(file_path, image_file.name)
            self.assertEqual(image_file.read(), png_file.read())




"""
    def test_available_image_exists(self):
        _add_test_image_to_storage(self.storage, self.project, 'test_image', 'jpg')
        self.assertTrue(self.storage.exists('test_project', 'test_image', 'jpg'))

    def test_unavailable_image_exists_not(self):
        self.assertFalse(self.storage.exists('test_project', 'not_existing', 'png'))

    def test_get_existing_image(self):
        #get must return images of type JPEG with a valid dimension
        _add_test_image_to_storage(self.storage, self.project, 'test_image', 'jpg')
        im = Image.open(self.storage.get('test_project', 'test_image', 'jpg'))
        self.assertTrue(
            im.size[0] > 0 and im.size[1] > 0)  # image has any valid size
        self.assertEqual(im.format, 'JPEG')

    def test_get_missing_image(self):
        #calling get on an unavailable image should yield a 404 error
        with self.assertRaises(NotFound):
            self.storage.get('test_project', 'blabla', 'png')

    def test_overwrite(self):
        #calling save() on an image identified by (project, name, extension
        #    and size) that already exists
        #    must overwrite the image
        _add_test_image_to_storage(self.storage, self.project, 'test_image', 'jpg')
        im = Image.open(self.storage.get('test_project', 'test_image', 'jpg'))
        # save two new images in the storage
        self.storage.save_image('test_project', 'overwrite_test', 'jpg', im)
        self.storage.save_image('test_project', 'overwrite_test', 'jpg', im,
                                mode='imaginary_size')
        # now overwrite them with an image of another size
        new_width = 15
        new_height = 15
        resized_img = im.resize((new_width, new_height))
        self.assertEqual((new_width, new_height), resized_img.size)
        self.storage.save_image('test_project', 'overwrite_test', 'jpg',
                                resized_img)
        self.storage.save_image('test_project', 'overwrite_test', 'jpg',
                                resized_img, mode='imaginary_size')

        # check that the images have been overwritten
        im1 = Image.open(
            self.storage.get('test_project', 'overwrite_test', 'jpg'))
        im2 = Image.open(
            self.storage.get('test_project', 'overwrite_test', 'jpg',
                             'imaginary_size'))
        self.assertEqual((new_width, new_height), im1.size)
        self.assertEqual((new_width, new_height), im2.size)

    def test_save_new_img(self):
        #after saving a not yet existing image
        #    it must be available in the storage

        _add_test_image_to_storage(self.storage, self.project, 'test_image', 'jpg')
        fd = self.storage.get('test_project', 'test_image', 'jpg')
        im = Image.open(fd)
        resized_img = im.resize((20, 30))
        # invent a random size to make sure it does not yet exist in storage
        size = 'xtrasmall'
        random.seed()
        while self.storage.exists('test_project', 'test_image', 'jpg', size):
            size += str(random.randint(0, 10))
        self.assertFalse(
            self.storage.exists('test_project', 'test_image', 'jpg', size))
        self.storage.save_image('test_project', 'test_image', 'jpg', resized_img,
                                size)
        self.assertTrue(
            self.storage.exists('test_project', 'test_image', 'jpg', size))
        im_from_storage = Image.open(
            self.storage.get('test_project', 'test_image', 'jpg', size))
        # storage must return a JPEG image with the chosen size
        self.assertEqual(im_from_storage.size, resized_img.size)
        self.assertEqual(im_from_storage.format, 'JPEG')

    def test_image_fd_is_readonly(self):
        #the filedescriptor returned by get must not allow to change
        #    the image in the storage either directly raise an error at write()
        #    time or allow write() calls but do not store it (see the different
        #    implementations in FS and Datastore Testcases)
        _add_test_image_to_storage(self.storage, self.project, 'test_image', 'jpg')
        fd = self.storage.get('test_project', 'test_image', 'jpg')
        with self.assertRaises(IOError):
            fd.seek(0)
            fd.write(b'asdf')

    def test_delete_non_existing_image(self):
        #deleting a non-existing image should not succeed
        non_existing_image = 'non_existing_name'
        exists = self.storage.exists('test_project', non_existing_image, 'jpg')
        delete_succeeded = self.storage.delete('test_project',
                                               non_existing_image, 'jpg')
        self.assertFalse(exists)  # just to be sure
        self.assertFalse(delete_succeeded)

    def test_delete_existing_image(self):
        #tries to delete an existing image
        prj, name, extension = 'test_project', 'existing-image', 'jpg'
        _add_test_image_to_storage(self.storage, prj, name, extension)
        self.assertTrue(self.storage.exists(prj, name, extension))
        delete_succeeded = self.storage.delete(prj, name, extension)
        self.assertTrue(delete_succeeded)
        self.assertFalse(self.storage.exists(prj, name, extension))

    def test_save_png_image(self):
        with open('test_images/png_image.png', 'rb') as f:
            img = Image.open(f)
            self.storage.save_image(self.project, "test_image", "png", img)

        im_from_storage = Image.open(self.storage.get(self.project, 'test_image', 'png'))
        self.assertEqual(im_from_storage.format, 'PNG')
"""
import base64

import json
import random
import unittest
import io
import sys
import os

from PIL import Image
from werkzeug.exceptions import NotFound

from storage.filesystem import FileImageStorage
import image_resize_service as img_service


if 'RUNNING_ON_TRAVIS_CI' in os.environ:
    """we're on travis ci!
       let's check if there is a appengine sdk directory. if so, add the libs to the pythonpath and therefore
       enable the datastore tests too.
    """
    sdk_dir = './google_appengine'
    if os.path.isdir(sdk_dir):
        sys.path.append(sdk_dir)
        for library in os.listdir(sdk_dir + '/lib'):
            if os.path.isdir(sdk_dir + '/lib/' + library):
                sys.path.append(sdk_dir + '/lib/' + library)

try:
    # noinspection PyUnresolvedReferences
    from google.appengine.ext import testbed

    APP_ENGINE_AVAILABLE = True
except ImportError:
    APP_ENGINE_AVAILABLE = False
    sys.stderr.write('App engine not available. Datastore tests are NOT run.\n')


def _add_test_image_to_storage(storage, project, name, extension):
    """adds the welcome image to a storage. useful for testing empty storages"""
    with open('demo_image_dir/images/demo_project/welcome.jpg', 'r') as f:
        storage.save(project, name, extension, f.read())


class APITestCase(unittest.TestCase):
    """tests the HTTP API using the configured storage
       make sure to configure STORAGE=APP_ENGINE if you run the code in the dev_appserver or on appspot.
       otherwise you'll get readonly filesystem errors.
    """

    def setUp(self):
        img_service.app.config['TESTING'] = True
        self.app = img_service.app.test_client()
        if APP_ENGINE_AVAILABLE:
            # storage=appengine needs this
            self.testbed = testbed.Testbed()
            self.testbed.activate()
            self.testbed.init_datastore_v3_stub()
        _add_test_image_to_storage(img_service._storage(), 'demo_project', 'welcome', 'jpg')
        self.username, self.password = img_service.app.config['PROJECTS']['demo_project']['auth']

    def tearDown(self):
        if APP_ENGINE_AVAILABLE:
            self.testbed.deactivate()

    def test_index(self):
        """content doesn't matter. just make sure there is always a welcome page"""
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)

    def test_uploadform(self):
        """just make sure we get a html response containing a form"""
        rv = self.app.get('/uploadform')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue('<form' in rv.data)

    def test_resized_image(self):
        """just download an existing fullsize image"""
        rv, im = self.download_image('/img/demo_project/welcome@small.jpg')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        self.assertEqual(im.format, 'JPEG')

    def test_full_image(self):
        """download a resized image"""
        rv, im = self.download_image('/img/demo_project/welcome.jpg')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        self.assertEqual(im.format, 'JPEG')

    def test_wrong_method_resized_img(self):
        """resized image url only supports GET"""
        rv = self.app.post('/img/demo_project/welcome@small.jpg')
        self.assertEqual(rv.status_code, 405)  # method not allowed

    def test_wrong_method_img(self):
        """the full image url only supports GET"""
        rv = self.app.post('/img/demo_project/welcome.jpg')
        self.assertEqual(rv.status_code, 405)

    def test_wrong_method_upload(self):
        """the upload url only supports POST"""
        rv = self.app.get('/upload')
        self.assertEqual(rv.status_code, 405)

    def test_wrong_method_uploadform(self):
        """the uploadform only supports GET"""
        rv = self.app.post('/uploadform')
        self.assertEqual(rv.status_code, 405)

    def test_invalid_project(self):
        """wrong projects return a 404 error"""
        rv = self.app.get('/img/bla/welcome@small.jpg')
        self.assertEqual(rv.status_code, 404)
        # same test for fullsize images
        rv = self.app.get('/img/bla/welcome.jpg')
        self.assertEqual(rv.status_code, 404)

    def test_invalid_size(self):
        """unsupported dimensions return a 404 error"""
        rv = self.app.get('/img/demo_project/welcome@blabla.jpg')
        self.assertEqual(rv.status_code, 404)  # not found

    def test_correct_mimetype(self):
        """make sure we get a jpeg image and it's dimension fits the configuration"""
        for dimension_name, dimension in img_service.app.config['PROJECTS']['demo_project']['dimensions'].items():
            rv, im = self.download_image('/img/demo_project/welcome@' + dimension_name + '.jpg')
            max_width, max_height = dimension
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, 'image/jpeg')
            self.assertEqual(im.format, 'JPEG')
            self.assertTrue(im.size[0] <= max_width and im.size[1] <= max_height)

    def test_upload_wrong_credentials(self):
        """try to upload to a valid project using wrong credentials"""
        with open('demo_image_dir/images/demo_project/welcome.jpg', 'r') as f:
            rv = self.upload_with_auth('fred', 'frickler', 'demo_project', f, 'upload_test.jpg')
        self.assertEqual(rv.status_code, 401)  # Unauthorized

    def test_upload_wrong_project(self):
        """try to upload to an invalid project using valid credentials"""
        with open('demo_image_dir/images/demo_project/welcome.jpg', 'r') as f:
            rv = self.upload_with_correct_auth('blabla', f, 'upload_test.jpg')
        self.assertEqual(rv.status_code, 401)  # Unauthorized

    def check_valid_json_response(self, json_response, expected_keys, expected_values=None):
        """checks that json_response contains ONLY the expected keys and nothing else.
           if needed it can also check the values inside the json_response
        """
        for key, value in json_response.iteritems():
            self.assertTrue(key in expected_keys)
        for key in expected_keys:
            self.assertTrue(key in json_response)
        if expected_values:
            for key, value in expected_values.iteritems():
                self.assertEqual(json_response[key], expected_values[key])

    def test_upload(self):
        """upload a valid image using valid credentials.
           api must reply with a json response containing { 'status' : 'ok', 'url' : 'url_to_the_image'}
        """
        # upload a valid image
        with open('demo_image_dir/images/demo_project/welcome.jpg', 'r') as f:
            rv = self.upload_with_correct_auth('demo_project', f, 'upload.jpg')
        json_response = json.loads(rv.data)
        # and download it
        url_to_image = '/img/demo_project/upload.jpg'
        rv2, im = self.download_image(url_to_image)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv2.status_code, 200)
        self.assertEqual(im.format, 'JPEG')
        self.check_valid_json_response(json_response, ('status', 'url'), dict(status='ok', url=url_to_image))

    def test_upload_wrong_extension(self):
        """ correct login, but filename is not an image (.exe). API must response with a json
            containing status='fail' and an error message 'message'. expected statuscode = 500
        """
        with open('demo_image_dir/images/demo_project/welcome.jpg', 'r') as f:
            rv = self.upload_with_correct_auth('demo_project', f, 'upload.exe')
        json_response = json.loads(rv.data)
        self.assertEqual(rv.status_code, 500)
        self.check_valid_json_response(json_response, ('status', 'message'), dict(status='fail'))

    def test_upload_invalid_file(self):
        """valid credentials and imagename. but uploading some data that is no image
            API must response with a json containing status='fail' and an error message
            'message'. expected statuscode = 500
        """
        rv = self.upload_with_correct_auth('demo_project', io.BytesIO(r'asdfasdf'), 'upload.jpg')
        json_response = json.loads(rv.data)
        self.assertEqual(rv.status_code, 500)
        self.check_valid_json_response(json_response, ('status', 'message'), dict(status='fail'))

    def upload_with_auth(self, username, password, project, file, filename):
        """try uploading the given file using http basic login"""
        return self.app.post('/upload',
                             content_type='multipart/form-data',
                             headers={
                                 'Authorization': 'Basic ' + base64.b64encode(username + \
                                                                              ":" + password)
                             },
                             data={'project': project,
                                   'file': (file, filename)}
        )

    def upload_with_correct_auth(self, project, file, filename):
        """upload the file using valid credentials"""
        return self.upload_with_auth(self.username, self.password, project, file, filename)

    def download_image(self, url):
        """download the image and return response and PIL.Image objects"""
        rv = self.app.get(url)
        im = Image.open(io.BytesIO(rv.data))
        return rv, im


class FSStorageTestCase(unittest.TestCase):
    """tests the filesystem storage and therefore defines the storage API
       all storages must have the same behaviour as it's tested here.
       see DataStoreStorageTestCase below.
    """

    def setUp(self):
        self.storage = FileImageStorage(
            img_service.app.config['FILESYSTEM_STORAGE_SOURCE_DIR'],
            img_service.app.config['FILESYSTEM_STORAGE_RESIZED_DIR'])

    def tearDown(self):
        pass

    def test_available_image_exists(self):
        """storage.exists() should return true for available images"""
        self.assertTrue(self.storage.exists('demo_project', 'welcome', 'jpg'))

    def test_unavailable_image_exists_not(self):
        """storage.exists() should return false for unavailable images"""
        self.assertFalse(self.storage.exists('demo_project', 'blabla', 'png'))

    def test_get_existing_image(self):
        """get must return images of type JPEG with a valid dimension"""
        im = Image.open(self.storage.get('demo_project', 'welcome', 'jpg'))
        self.assertTrue(im.size[0] > 0 and im.size[1] > 0)  # image has any valid size
        self.assertEqual(im.format, 'JPEG')

    def test_get_missing_image(self):
        """calling get on an unavailable image should yield a 404 error"""
        with self.assertRaises(NotFound):
            self.storage.get('demo_project', 'blabla', 'png')

    def test_overwrite(self):
        """calling save() on an image identified by (project, name, extension and size) that already exists
           must overwrite the image
        """
        im = Image.open(self.storage.get('demo_project', 'welcome', 'jpg'))
        # save two new images in the storage
        self.storage.save_image('demo_project', 'overwrite_test', 'jpg', im)
        self.storage.save_image('demo_project', 'overwrite_test', 'jpg', im, size='imaginary_size')
        # now overwrite them with an image of another size
        new_width = 15
        new_height = 15
        resized_img = im.resize((new_width, new_height))
        self.assertEqual((new_width, new_height), resized_img.size)
        self.storage.save_image('demo_project', 'overwrite_test', 'jpg', resized_img)
        self.storage.save_image('demo_project', 'overwrite_test', 'jpg', resized_img, size='imaginary_size')
        # check that the images have been overwritten
        im1 = Image.open(self.storage.get('demo_project', 'overwrite_test', 'jpg'))
        im2 = Image.open(self.storage.get('demo_project', 'overwrite_test', 'jpg', 'imaginary_size'))
        self.assertEqual((new_width, new_height), im1.size)
        self.assertEqual((new_width, new_height), im2.size)

    def test_save_new_img(self):
        """after saving a not yet existing image it must be available in the storage """
        fd = self.storage.get('demo_project', 'welcome', 'jpg')
        im = Image.open(fd)
        resized_img = im.resize((20, 30))
        # invent a random size to make sure it does not yet exist in our storage
        size = 'xtrasmall'
        random.seed()
        while self.storage.exists('demo_project', 'welcome', 'jpg', size):
            size += str(random.randint(0, 10))
        self.assertFalse(self.storage.exists('demo_project', 'welcome', 'jpg', size))
        self.storage.save_image('demo_project', 'welcome', 'jpg', resized_img, size)
        self.assertTrue(self.storage.exists('demo_project', 'welcome', 'jpg', size))
        im_from_storage = Image.open(self.storage.get('demo_project', 'welcome', 'jpg', size))
        # storage must return a JPEG image with the chosen size
        self.assertEqual(im_from_storage.size, resized_img.size)
        self.assertEqual(im_from_storage.format, 'JPEG')

    def test_image_fd_is_readonly(self):
        """the filedescriptor returned by get must not allow to change the image in the storage
            either directly raise an error at write() time or allow write() calls but do not
            store it (see the different implementations in FS and Datastore Testcases)
        """
        fd = self.storage.get('demo_project', 'welcome', 'jpg')
        with self.assertRaises(IOError):
            fd.seek(0)
            fd.write(b'asdf')


if APP_ENGINE_AVAILABLE:
    """run all the storage tests on the appengine datastore too"""


    class DatastoreStorageTestCase(FSStorageTestCase):
        def setUp(self):
            super(DatastoreStorageTestCase, self).setUp()
            self.testbed = testbed.Testbed()
            self.testbed.activate()
            self.testbed.init_datastore_v3_stub()
            from storage.appengine_datastore import DatastoreImageStorage  # must be imported AFTER creating a testbed
            self.storage = DatastoreImageStorage()
            _add_test_image_to_storage(self.storage, 'demo_project', 'welcome', 'jpg')

        def tearDown(self):
            self.testbed.deactivate()
            super(DatastoreStorageTestCase, self).tearDown()

        def test_image_fd_is_readonly(self):
            """since the appengine implementation returns a io.BytesIO it is writable
               let's just test that our writes do not end up in the datastore
            """
            # overwrite the fd with a resized image
            fd = self.storage.get('demo_project', 'welcome', 'jpg')
            im = Image.open(fd)
            new_im = im.resize((im.size[0] + 1, im.size[0] + 1))
            fd.seek(0)
            new_im.save(fd, 'JPEG')
            fd.close()
            # load the image again and compare
            fd = self.storage.get('demo_project', 'welcome', 'jpg')
            im = Image.open(fd)
            self.assertNotEqual(im.size, new_im.size)

if __name__ == '__main__':
    unittest.main()

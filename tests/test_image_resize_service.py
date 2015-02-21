import base64
import json
import unittest
import io
import sys
import os
from PIL import Image

import image_service as img_service

def _add_test_image_to_storage(storage, project, name, extension):
    """adds the welcome image to a storage. used for testing empty storages"""
    with open('test_images/%s_image.%s' % (extension, extension), 'r') as f:
        storage.save(project, name, extension, f.read())


def _create_test_thumb_with_image(storage, project, name, extension):
    """adds the welcome image to a storage. used for testing empty storages"""
    with open('test_images/%s_image.%s' % (extension, extension), 'r') as f:
        storage.save(project, name, extension, f.read())


class APITestCase(unittest.TestCase):
    """tests the HTTP API using the configured storage
       make sure to configure STORAGE=APP_ENGINE if you run the code in the
       dev_appserver or on appspot. otherwise you'll get readonly
       filesystem errors.
    """

    def setUp(self):
        img_service.app.config['TESTING'] = True
        img_service.app.config['PROJECTS'] = {
            'test_project': {  # projectname
                               'auth': ('test', 'test'),  # upload_username, upload_password CHANGE THIS
                               'size': {
                                   'small': (200, 200),  # size-name  and (max_width, max_height)
                                   'medium': (500, 500),
                                   'large': (800, 800),
                                   'fullsize': (1200, 1200)
                               },
                               'auth_token': ('http://127.0.0.1:8000', 'test')
            }
        }
        self.app = img_service.app.test_client()
        if APP_ENGINE_AVAILABLE:
            # storage=appengine needs this
            self.testbed = testbed.Testbed()
            self.testbed.activate()
            self.testbed.init_datastore_v3_stub()
        self.username, self.password = \
            img_service.app.config['PROJECTS']['test_project']['auth']
        _add_test_image_to_storage(img_service._storage(), 'test_project',
                                   'test_image', 'jpg')

    def tearDown(self):
        if APP_ENGINE_AVAILABLE:
            self.testbed.deactivate()

    def test_index(self):
        """content doesn't matter. just make sure there is as welcome page"""
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)

    def test_uploadform(self):
        """just make sure we get a html response containing a form"""
        rv = self.app.get('/uploadform')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue('<form' in rv.data)

    def test_wrong_method_resized_img(self):
        """resized image url only supports GET"""
        rv = self.app.post('/img/test_project/test_image@small.jpg')
        self.assertEqual(rv.status_code, 405)  # method not allowed

    def test_wrong_method_img(self):
        """the full image url only supports GET"""
        rv = self.app.post('/img/test_project/test_image.jpg')
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
        rv = self.app.get('/img/bla/test_image@small.jpg')
        self.assertEqual(rv.status_code, 404)
        # same test for fullsize images
        rv = self.app.get('/img/bla/welcome.jpg')
        self.assertEqual(rv.status_code, 404)

    def test_invalid_size(self):
        """unsupported dimensions return a 404 error"""
        rv = self.app.get('/img/test_project/test_image@fubar.jpg')
        self.assertEqual(rv.status_code, 404)  # not found

    def test_upload_wrong_credentials(self):
        """try to upload to a valid project using wrong credentials"""
        with open('test_images/jpg_image.jpg', 'r') as f:
            rv = self.upload_with_auth('fred', 'frickler', 'test_project', f,
                                       'upload_test.jpg')
        self.assertEqual(rv.status_code, 401)  # Unauthorized

    def test_upload_wrong_project(self):
        """try to upload to an invalid project using valid credentials"""
        with open('test_images/jpg_image.jpg', 'r') as f:
            rv = self.upload_with_correct_auth('blabla', f, 'upload_test.jpg')
        self.assertEqual(rv.status_code, 401)  # Unauthorized

    def check_valid_json_response(self, json_response, expected_keys,
                                  expected_values=None):
        """checks that json_response contains ONLY the expected keys.
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
           api must reply with a json response containing
            { 'status' : 'ok', 'url' : 'url_to_the_image'}
        """
        # upload a valid image
        with open('test_images/jpg_image.jpg', 'r') as f:
            rv = self.upload_with_correct_auth('test_project', f, 'upload.jpg')
        json_response = json.loads(rv.data)
        # and download it
        url_to_image = '/img/test_project/upload.jpg'
        rv2, im = self.download_image(url_to_image)
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(rv2.status_code, 200)
        self.assertEqual(im.format, 'JPEG')
        self.check_valid_json_response(json_response,
                                       ('status', 'url', 'message'),
                                       dict(status='ok', url=url_to_image))

    def test_upload_wrong_extension(self):
        """ correct login, but filename is not an image (.exe).
            API must response with a json containing status='fail' and an
            error message 'message'. expected statuscode = 500
        """
        with open('test_images/jpg_image.jpg', 'r') as f:
            rv = self.upload_with_correct_auth('test_project', f, 'upload.exe')
        json_response = json.loads(rv.data)
        self.assertEqual(rv.status_code, 500)
        self.check_valid_json_response(json_response,
                                       ('status', 'message', 'url'),
                                       dict(status='fail'))

    def test_upload_invalid_file(self):
        """valid credentials and imagename. but uploading some data that is
            no image. API must response with a json containing status='fail'
            and an error message 'message'. expected statuscode = 500
        """
        rv = self.upload_with_correct_auth('test_project',
                                           io.BytesIO(r'theAnswerIs42'),
                                           'upload.jpg')
        json_response = json.loads(rv.data)
        self.assertEqual(rv.status_code, 500)
        self.check_valid_json_response(json_response,
                                       ('status', 'message', 'url'),
                                       dict(status='fail'))

    def test_successfully_delete(self):
        """
        the api should respond with status_code=200, status=ok, message=...
        when successfully deleted an image
        """
        _add_test_image_to_storage(img_service._storage(), 'test_project',
                                   'delete_api_test', 'jpg')
        rv = self.app.delete(
            '/api/v1.0/images/test_project/delete_api_test.jpg',
            headers={
                'Authorization': 'Basic '
                                 + base64.b64encode(self.username +
                                                    ":" + self.password)
            })
        self.assertEqual(rv.status_code, 200)
        self.check_valid_json_response(json.loads(rv.data),
                                       ('status', 'message'),
                                       dict(status='ok'))

    def test_non_authenticated_delete(self):
        """
        deleting an image without proper authentication should not succeed and
        the image must still be available
        """
        rv = self.app.delete('/api/v1.0/images/test_project/test_image.jpg')
        rv2 = self.app.get('/img/test_project/test_image.jpg')
        self.assertEqual(rv.status_code, 401)
        self.assertEqual(rv2.status_code, 200)

    def test_put_without_auth(self):
        """
        modifying an image without authentication should not succeed
        """
        with open('test_images/jpg_image.jpg', 'r') as f:
            rv = self.app.put('/api/v1.0/images/test_project/test_image.jpg',
                              content_type='multipart/form-data',
                              data={'file': (f, f.name)})
            self.assertEqual(rv.status_code, 401)

    def test_put(self):
        """
        using put an image can be created and overwritten
        checks:
            - image should not yet exist
            - put image and check that it exists
            - put resized image and check that it has been overwritten
        """
        url_to_test_image = '/img/test_project/put_test.jpg'
        with open('test_images/jpg_image.jpg', 'r') as f:
            rv = self.app.put('/api/v1.0/images/test_project/put_test.jpg',
                              headers={
                                  'Authorization': 'Basic ' + base64.b64encode(
                                      self.username +
                                      ":" + self.password)
                              },
                              content_type='multipart/form-data',
                              data={'file': (f, f.name)})
            self.assertEqual(rv.status_code, 201)
            json_response = json.loads(rv.data)
            self.check_valid_json_response(json_response,
                                           ('status', 'message', 'url'),
                                           dict(status='ok'))
            # check that image exists now
            rv, im = self.download_image(url_to_test_image)
            self.assertEqual(rv.status_code, 200)
            # now overwrite the image
            resized_img = im.resize((100, 100))
            tmp = io.BytesIO()
            resized_img.save(tmp, 'JPEG')
            tmp.seek(0)
            # now overwrite
            rv = self.app.put('/api/v1.0/images/test_project/put_test.jpg',
                              headers={
                                  'Authorization': 'Basic ' + base64.b64encode(
                                      self.username +
                                      ":" + self.password)
                              },
                              content_type='multipart/form-data',
                              data={'file': (tmp, f.name)})
            self.assertEqual(rv.status_code, 201)
            self.assertEqual(rv.status_code, 201)
            json_response = json.loads(rv.data)
            self.check_valid_json_response(json_response,
                                           ('status', 'message', 'url'),
                                           dict(status='ok'))
            # and checkt that it's overwritten
            rv, new_img = self.download_image(url_to_test_image)
            self.assertEqual(rv.status_code, 200)
            self.assertNotEqual(new_img.size, im.size)

    def test_upload_with_auth_token(self):
        rv = None
        with open('test_images/jpg_image.jpg', 'r') as _file:
            rv = self.upload_with_auth_token("http://127.0.0.1:8000", "test", 'test_project', _file, "token_upload.jpg")
        self.assertEqual(rv.status_code, 201)

    def test_upload_with_invalid_auth_token(self):
        project = 'test_project'
        rv = None
        with open('test_images/jpg_image.jpg', 'r') as _file:
            rv = self.upload_with_auth_token("http://127.0.0.1:8000", "invalid", 'test_project', _file,
                                             "invalid_upload.jpg")
        self.assertEqual(rv.status_code, 401)

    def test_upload_with_invalid_origin(self):
        project = 'test_project'
        rv = None
        with open('test_images/jpg_image.jpg', 'r') as _file:
            rv = self.upload_with_auth_token("http://some_page.com", "demo", 'test_project', _file,
                                             "invalid_upload.jpg")
        self.assertEqual(rv.status_code, 401)

    def upload_with_auth_token(self, origin, token, project, _file, filename):
        return self.app.post('/upload',
                             content_type='multipart/form-data',
                             headers={
                                 'Authorization': 'Token ' + token,
                                 'Origin': origin
                             },
                             data={'project': project,
                                   'file': (_file, filename)})

    def upload_with_auth(self, username, password, project, _file, filename):
        """try uploading the given file using http basic login"""
        return self.app.post('/upload',
                             content_type='multipart/form-data',
                             headers={
                                 'Authorization': 'Basic ' + base64.b64encode(
                                     username +
                                     ":" + password)
                             },
                             data={'project': project,
                                   'file': (_file, filename)})

    def upload_with_correct_auth(self, project, file, filename):
        """upload the file using valid credentials"""
        return self.upload_with_auth(self.username, self.password, project,
                                     file, filename)

    def download_image(self, url):
        """download the image and return response and PIL.Image objects"""
        rv = self.app.get(url)
        im = Image.open(io.BytesIO(rv.data))
        return rv, im

    def test_correct_mimetype(self):
        """make sure we get a jpeg image and it's dimension fits the config"""
        for size_name, size in \
                img_service.app.config['PROJECTS']['test_project'][
                    'size'].items():
            for mode in ("fit", "crop"):
                rv, im = self.download_image(
                    '/img/test_project/test_image@%s-%s.jpg' % (mode, size_name))
                max_width, max_height = size
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.mimetype, 'image/jpeg')
                self.assertEqual(im.format, 'JPEG')
                self.assertTrue(im.size[0] <= max_width and im.size[1] <= max_height)

    def test_resize_invalid_mode_size(self):
        rv = self.app.get('/img/test_project/test_image@small.jpg')
        self.assertEqual(rv.status_code, 404)
        rv = self.app.get('/img/test_project/test_image@fit-small-unknown.jpg')
        self.assertEqual(rv.status_code, 404)

    def test_resize_invalid_size(self):
        rv = self.app.get('/img/test_project/test_image@fit-invalid.jpg')
        self.assertEqual(rv.status_code, 404)

    def test_resize_invalid_mode(self):
        rv = self.app.get('/img/test_project/test_image@invalid-small.jpg')
        self.assertEqual(rv.status_code, 404)

    def test_resize_mode_fit(self):
        """
            test image is 1600x1200 and small is 200, 200 so size should be 200x150
        """
        rv, im = self.download_image('/img/test_project/test_image@fit-small.jpg')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(200, im.size[0])
        self.assertEqual(150, im.size[1])

    def test_resize_mode_crop(self):
        """
            test image is 1600x1200 and small is 200, 200 so size should be 200x150
        """
        rv, im = self.download_image('/img/test_project/test_image@crop-small.jpg')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(200, im.size[0])
        self.assertEqual(200, im.size[1])

    def test_full_image(self):
        """download a resized image"""
        rv, im = self.download_image('/img/test_project/test_image.jpg')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        self.assertEqual(im.format, 'JPEG')

if __name__ == '__main__':
    unittest.main()

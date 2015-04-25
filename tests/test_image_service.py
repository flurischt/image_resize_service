import unittest
import os
import shutil
import json
from StringIO import StringIO
import base64

from PIL import Image as PILImage

import image_service


class TestImageService(unittest.TestCase):
    def setUp(self):
        self.username = "user"
        self.password = "pass"
        self.auth_token = "test"
        self.origin = "http://127.0.0.1:8000"
        self.storage_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "test_storage")
        image_service.app.config['STORAGE_DIRECTORY'] = self.storage_directory
        image_service.app.config['AUTH_TOKEN'] = (self.origin, self.auth_token)
        image_service.app.config['AUTH_BASIC'] = (self.username, self.password)
        self.app = image_service.app.test_client()
        image_service._storage = None

    def tearDown(self):
        try:
            shutil.rmtree(self.storage_directory)
        except OSError:
            pass

    def _test_image_path(self, image_name):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(current_dir, "test_images", image_name)

    def _post_image(self, binary_image, image_name, origin=None, auth_token=None, auth_basic=None):
        origin = self.origin if origin is None else origin
        auth_token = self.auth_token if auth_token is None else auth_token
        authorization = 'Token ' + auth_token
        if auth_basic is not None:
            authorization = 'Basic ' + base64.b64encode(auth_basic)
        return self.app.post('/images/',
                             content_type='multipart/form-data',
                             headers={
                                 'Authorization': authorization,
                                 'Origin': origin
                             },
                             data={'file': (binary_image, image_name)})

    def _put_image(self, binary_image, image_name, origin=None, auth_token=None):
        origin = self.origin if origin is None else origin
        auth_token = self.auth_token if auth_token is None else auth_token
        return self.app.put("/images/%s" % image_name,
                            content_type='multipart/form-data',
                            headers={
                                'Authorization': 'Token ' + auth_token,
                                'Origin': origin
                            },
                            data={'file': (binary_image, image_name)})

    def _get_image(self, image_name, image_extension, mode=None, size=None):
        resource_url = "/images/%s.%s" % (image_name, image_extension)
        if mode and size:
            resource_url = "/images/%s@%s-%dx%d.%s" % (image_name, mode, size[0], size[1], image_extension)
        return self.app.get(resource_url)

    def test_create_storage(self):
        image_service.storage()
        self.assertTrue(os.path.isdir(self.storage_directory))

    def test_invalid_auth_token(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension), auth_token="invalid")
            self.assertEqual(401, response.status_code)

    def test_invalid_username_or_password(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension),
                                        auth_basic="invalid:invalid")
            self.assertEqual(401, response.status_code)

    def test_valid_username_or_password(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension),
                                        auth_basic="%s:%s" % (self.username, self.password))
            self.assertEqual(201, response.status_code)

    def test_invalid_origin(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension), origin="http://invalid.com")
            self.assertEqual(401, response.status_code)

    def test_wildcard_origin(self):
        image_name = "test_image"
        image_extension = "png"
        image_service.app.config['AUTH_TOKEN'] = ('*', 'test')
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension),
                                        origin="http://whatever.com")
            self.assertEqual(201, response.status_code)

    def test_post_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
            json_payload = json.loads(response.data)
            self.assertEqual("/images/%s.%s" % (image_name, image_extension),
                             json_payload["url"])
            image = image_service.storage().get(image_name, image_extension)
            self.assertIsNotNone(image)
            self.assertEqual("%s.%s" % (image_name, image_extension), os.path.basename(image.name))

    def test_create_identical_name_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            self._post_image(png_image, "%s.%s" % (image_name, image_extension))
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
            json_payload = json.loads(response.data)
            self.assertEqual("/images/%s-1.%s" % (image_name, image_extension),
                             json_payload["url"])

    def test_put_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._put_image(png_image, "%s.%s" % (image_name, image_extension))
        self.assertEqual(201, response.status_code)
        self.assertEqual('', response.data)

    def test_update_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            self._put_image(png_image, "%s.%s" % (image_name, image_extension))
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._put_image(png_image, "%s.%s" % (image_name, image_extension))
            self.assertEqual(200, response.status_code)

    def test_get_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._put_image(png_image, "%s.%s" % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
        response = self._get_image(image_name, image_extension)
        self.assertIsNotNone(response.data)
        self.assertEqual(200, response.status_code)
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            self.assertEqual(response.data, png_image.read())

    def test_get_manipulated_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._put_image(png_image, "%s.%s" % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
        response = self._get_image(image_name, image_extension, mode="crop", size=(200, 200))
        self.assertIsNotNone(response.data)
        self.assertEqual(200, response.status_code)
        pil_image = PILImage.open(StringIO(response.data))
        self.assertEqual((200, 200), pil_image.size)

    def test_get_manipulated_invalid_mode(self):
        image_name = "test_image"
        image_extension = "png"
        response = self._get_image(image_name, image_extension, mode="nonsense", size=(200, 200))
        self.assertEqual(404, response.status_code)
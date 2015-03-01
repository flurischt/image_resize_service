import unittest
import image_service
import os
import shutil
import json
from PIL import Image as PILImage
from StringIO import StringIO


class TestImageService(unittest.TestCase):
    def setUp(self):
        self.username = "test"
        self.password = "test"
        self.project_name = "test_project"
        self.auth_token = "test"
        self.origin = "http://127.0.0.1:8000"
        self.storage_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "test_storage")
        image_service.app.config['TESTING'] = True
        image_service.app.config['STORAGE_DIRECTORY'] = self.storage_directory
        image_service.app.config['PROJECTS'] = {
            self.project_name: {
                'auth': (self.username, self.password),  # upload_username, upload_password CHANGE THIS
                'size': {
                    'small': (200, 200),  # size-name  and (max_width, max_height)
                    'medium': (500, 500),
                    'large': (800, 800),
                    'fullsize': (1200, 1200)
                },
                'auth_token': (self.origin, self.auth_token)
            }
        }
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

    def _post_image(self, binary_image, image_name, origin=None, project=None, auth_token=None):
        origin = self.origin if origin is None else origin
        project = self.project_name if project is None else project
        auth_token = self.auth_token if auth_token is None else auth_token
        return self.app.post('/images/%s/' % project,
                             content_type='multipart/form-data',
                             headers={
                                 'Authorization': 'Token ' + auth_token,
                                 'Origin': origin
                             },
                             data={'file': (binary_image, image_name)})

    def _put_image(self, binary_image, image_name, origin=None, project=None, auth_token=None):
        origin = self.origin if origin is None else origin
        project = self.project_name if project is None else project
        auth_token = self.auth_token if auth_token is None else auth_token
        return self.app.put("/images/%s/%s" % (project, image_name),
                            content_type='multipart/form-data',
                            headers={
                                'Authorization': 'Token ' + auth_token,
                                'Origin': origin
                            },
                            data={'file': (binary_image, image_name)})

    def _get_image(self, image_name, image_extension, project=None, mode=None, size=None):
        project = self.project_name if project is None else project
        resource_url = "/images/%s/%s.%s" % (project, image_name, image_extension)
        if mode and size:
            resource_url = "/images/%s/%s@%s-%dx%d.%s" % (project, image_name, mode, size[0], size[1], image_extension)
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

    def test_invalid_origin(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension), origin="http://invalid.com")
            self.assertEqual(401, response.status_code)

    def test_wildcard_origin(self):
        image_name = "test_image"
        image_extension = "png"
        image_service.app.config['PROJECTS'][self.project_name]['auth_token'] = ('*', 'test')
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension), origin="http://invalid.com")
            self.assertEqual(201, response.status_code)

    def test_invalid_project(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension), project="invalid")
            self.assertEqual(403, response.status_code)

    def test_post_image(self):
        image_name = "test_image"
        image_extension = "png"
        with open(self._test_image_path('png_image.png'), 'r') as png_image:
            response = self._post_image(png_image, "%s.%s" % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
            json_payload = json.loads(response.data)
            self.assertEqual("/images/%s/%s.%s" % (self.project_name, image_name, image_extension),
                             json_payload["url"])
            image = image_service.storage().get(self.project_name, image_name, image_extension)
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
            self.assertEqual("/images/%s/%s-1.%s" % (self.project_name, image_name, image_extension),
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

    def test_get_invalid_project(self):
        image_name = "test_image"
        image_extension = "png"
        response = self._get_image(image_name, image_extension, project="nonsense")
        self.assertEqual(404, response.status_code)

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

    def test_get_manipulated_invalid_project(self):
        image_name = "test_image"
        image_extension = "png"
        response = self._get_image(image_name, image_extension, project="nonsense", mode="fit", size=(200, 200))
        self.assertEqual(404, response.status_code)
import unittest
import os
import shutil
import json
from io import BytesIO
import base64

from PIL import Image as PILImage

import image_service


class TestImageService(unittest.TestCase):
    def setUp(self):
        self.username = 'user'
        self.password = 'pass'
        self.auth_token = 'test'
        self.origin = 'http://127.0.0.1:8000'
        self.storage_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'test_storage')
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
        return os.path.join(current_dir, 'test_images', image_name)

    def _post_image(self, binary_image, image_name, origin=None, auth_token=None, auth_basic=None):
        origin = self.origin if not origin else origin
        auth_token = self.auth_token if not auth_token else auth_token
        authorization = 'Token ' + auth_token
        if auth_basic is not None:
            authorization = 'Basic ' + base64.b64encode(auth_basic.encode('ascii')).decode('ascii')
        return self.app.post('/images/',
                             content_type='multipart/form-data',
                             headers={
                                 'Authorization': authorization,
                                 'Origin': origin
                             },
                             data={'file': (binary_image, image_name)})

    def _put_image(self, binary_image, image_name, origin=None, auth_token=None):
        origin = self.origin if not origin else origin
        auth_token = self.auth_token if not auth_token else auth_token
        return self.app.put('/images/%s' % image_name,
                            content_type='multipart/form-data',
                            headers={
                                'Authorization': 'Token ' + auth_token,
                                'Origin': origin
                            },
                            data={'file': (binary_image, image_name)})

    def _get_image(self, image_name, image_extension, mode=None, size=None):
        resource_url = '/images/%s.%s' % (image_name, image_extension)
        if mode and size:
            resource_url = '/images/%s@%s-%dx%d.%s' % (image_name, mode, size[0], size[1], image_extension)
        return self.app.get(resource_url)


    def test_create_storage(self):
        image_service.storage()
        self.assertTrue(os.path.isdir(self.storage_directory))


    def test_invalid_auth_token(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension), auth_token='invalid')
            self.assertEqual(401, response.status_code)

    def test_no_auth_token_set(self):
        image_service.app.config['AUTH_TOKEN'] = ''
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension), auth_token='invalid')
            self.assertEqual(401, response.status_code)

    def test_invalid_username_or_password(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension),
                                        auth_basic='invalid:invalid')
            self.assertEqual(401, response.status_code)

    def test_valid_username_or_password(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension),
                                        auth_basic='%s:%s' % (self.username, self.password))
            self.assertEqual(201, response.status_code)

    def test_no_basic_auth_set(self):
        image_name = 'test_image'
        image_extension = 'png'
        image_service.app.config['AUTH_BASIC'] = ''
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension),
                                        auth_basic='%s:%s' % (self.username, self.password))
            self.assertEqual(401, response.status_code)

    def test_invalid_origin(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension), origin='http://invalid.example')
            self.assertEqual(401, response.status_code)

    def test_wildcard_origin(self):
        image_name = 'test_image'
        image_extension = 'png'
        image_service.app.config['AUTH_TOKEN'] = ('*', 'test')
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension),
                                        origin='http://whatever.example')
            self.assertEqual(201, response.status_code)

    def test_post_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
            json_payload = json.loads(response.data.decode())
            self.assertEqual('/images/%s.%s' % (image_name, image_extension),
                             json_payload['url'])
            image = image_service.storage().get(image_name, image_extension)
            self.assertIsNotNone(image)
            self.assertEqual('%s.%s' % (image_name, image_extension), os.path.basename(image.name))

    def test_create_identical_name_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            self._post_image(png_image, '%s.%s' % (image_name, image_extension))
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._post_image(png_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
            json_payload = json.loads(response.data.decode())
            self.assertEqual('/images/%s-1.%s' % (image_name, image_extension),
                             json_payload['url'])

    def test_put_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._put_image(png_image, '%s.%s' % (image_name, image_extension))
        self.assertEqual(201, response.status_code)
        self.assertEqual(b'', response.data)

    def test_update_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            self._put_image(png_image, '%s.%s' % (image_name, image_extension))
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._put_image(png_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(200, response.status_code)

    def test_get_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._put_image(png_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
        response = self._get_image(image_name, image_extension)
        self.assertIsNotNone(response.data)
        self.assertEqual(200, response.status_code)
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            self.assertEqual(response.data, png_image.read())

    def test_get_manipulated_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._put_image(png_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
        response = self._get_image(image_name, image_extension, mode='crop', size=(200, 200))
        self.assertIsNotNone(response.data)
        self.assertEqual(200, response.status_code)
        pil_image = PILImage.open(BytesIO(response.data))
        self.assertEqual((200, 200), pil_image.size)

    def test_get_manipulated_invalid_mode(self):
        image_name = 'test_image'
        image_extension = 'png'
        response = self._get_image(image_name, image_extension, mode='nonsense', size=(200, 200))
        self.assertEqual(404, response.status_code)

    def test_get_manipulated_fit_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            response = self._put_image(png_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
        response = self._get_image(image_name, image_extension, mode='fit', size=(200, 200))
        self.assertEqual(200, response.status_code)
        self.assertEqual('image/png', response.mimetype)
        pil_image = PILImage.open(BytesIO(response.data))
        self.assertEqual((200, 150), pil_image.size)

    def test_jpg_post_get_and_resize(self):
        image_name = 'photo'
        image_extension = 'jpg'
        with open(self._test_image_path('jpg_image.jpg'), 'rb') as jpg_image:
            response = self._post_image(jpg_image, '%s.%s' % (image_name, image_extension))
            self.assertEqual(201, response.status_code)
            json_payload = json.loads(response.data.decode())
            self.assertEqual('/images/%s.%s' % (image_name, image_extension),
                             json_payload['url'])
        orig_response = self._get_image(image_name, image_extension)
        self.assertEqual(200, orig_response.status_code)
        self.assertEqual('image/jpeg', orig_response.mimetype)

        fit_response = self._get_image(image_name, image_extension, mode='fit', size=(300, 300))
        self.assertEqual(200, fit_response.status_code)
        self.assertEqual('image/jpeg', fit_response.mimetype)
        pil_image = PILImage.open(BytesIO(fit_response.data))
        self.assertEqual((300, 225), pil_image.size)

    def test_get_nonexistent_image_returns_404(self):
        response = self._get_image('does_not_exist', 'png')
        self.assertEqual(404, response.status_code)

    def test_get_manipulated_nonexistent_image_returns_404(self):
        response = self._get_image('does_not_exist', 'png', mode='crop', size=(100, 100))
        self.assertEqual(404, response.status_code)

    def test_get_manipulated_non_integer_dimensions_returns_404(self):
        response = self.app.get('/images/test_image@crop-abcx200.png')
        self.assertEqual(404, response.status_code)

    def test_missing_auth_header_returns_401(self):
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            post_resp = self.app.post('/images/',
                                      content_type='multipart/form-data',
                                      data={'file': (png_image, 'test.png')})
            self.assertEqual(401, post_resp.status_code)
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            put_resp = self.app.put('/images/test.png',
                                    content_type='multipart/form-data',
                                    data={'file': (png_image, 'test.png')})
            self.assertEqual(401, put_resp.status_code)

    def test_index_demo_enabled_and_disabled(self):
        original_demo = image_service.app.config.get('ENABLE_DEMO')
        try:
            image_service.app.config['ENABLE_DEMO'] = True
            enabled_resp = self.app.get('/')
            self.assertEqual(200, enabled_resp.status_code)
            self.assertIn(b'Image Service', enabled_resp.data)

            image_service.app.config['ENABLE_DEMO'] = False
            disabled_resp = self.app.get('/')
            self.assertEqual(404, disabled_resp.status_code)
        finally:
            image_service.app.config['ENABLE_DEMO'] = original_demo

    def test_cors_headers_on_image_get(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            self._put_image(png_image, '%s.%s' % (image_name, image_extension))
        response = self.app.get('/images/%s.%s' % (image_name, image_extension),
                                headers={'Origin': 'https://client.example'})
        self.assertEqual(200, response.status_code)
        self.assertIn(response.headers.get('Access-Control-Allow-Origin'),
                      ('*', 'https://client.example'))

    def test_cors_preflight_options(self):
        response = self.app.options('/images/',
                                    headers={
                                        'Origin': 'https://client.example',
                                        'Access-Control-Request-Method': 'POST',
                                        'Access-Control-Request-Headers': 'Authorization, Content-Type'
                                    })
        self.assertEqual(200, response.status_code)
        self.assertIn('Authorization', response.headers.get('Access-Control-Allow-Headers', ''))

    def _delete_image(self, image_name, image_extension, origin=None, auth_token=None):
        origin = self.origin if origin is None else origin
        auth_token = self.auth_token if auth_token is None else auth_token
        return self.app.delete('/images/%s.%s' % (image_name, image_extension),
                               headers={
                                   'Authorization': 'Token ' + auth_token,
                                   'Origin': origin
                               })

    def test_delete_image(self):
        image_name = 'test_image'
        image_extension = 'png'
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            self.assertEqual(201, self._put_image(png_image, '%s.%s' % (image_name, image_extension)).status_code)
        self.assertEqual(200, self._get_image(image_name, image_extension, mode='crop', size=(100, 100)).status_code)
        delete_resp = self._delete_image(image_name, image_extension)
        self.assertEqual(200, delete_resp.status_code)
        self.assertEqual(404, self._get_image(image_name, image_extension).status_code)
        self.assertEqual(404, self._get_image(image_name, image_extension, mode='crop', size=(100, 100)).status_code)

    def test_delete_nonexistent_image_returns_404(self):
        delete_resp = self._delete_image('does_not_exist', 'png')
        self.assertEqual(404, delete_resp.status_code)

    def test_delete_image_requires_auth(self):
        response = self.app.delete('/images/test_image.png')
        self.assertEqual(401, response.status_code)

    def test_post_rejects_html_and_svg_uploads(self):
        html_resp = self._post_image(BytesIO(b'<script>alert(1)</script>'), 'xss.html')
        self.assertEqual(400, html_resp.status_code)
        svg_resp = self._post_image(BytesIO(b'<svg onload=alert(1)></svg>'), 'xss.svg')
        self.assertEqual(400, svg_resp.status_code)
        no_ext_resp = self._post_image(BytesIO(b'data'), 'noextension')
        self.assertEqual(400, no_ext_resp.status_code)

    def test_post_rejects_spoofed_png_and_mismatched_format(self):
        fake_png = self._post_image(BytesIO(b'<html><script>alert(1)</script></html>'), 'fake.png')
        self.assertEqual(400, fake_png.status_code)
        with open(self._test_image_path('jpg_image.jpg'), 'rb') as jpg_image:
            mismatch = self._post_image(jpg_image, 'actually_jpg.png')
            self.assertEqual(400, mismatch.status_code)

    def test_put_rejects_disallowed_extension_and_invalid_bytes(self):
        html_resp = self._put_image(BytesIO(b'<script>alert(1)</script>'), 'xss.html')
        self.assertEqual(400, html_resp.status_code)
        fake_png = self._put_image(BytesIO(b'not a real png'), 'fake.png')
        self.assertEqual(400, fake_png.status_code)

    def test_get_disallowed_extension_returns_404(self):
        self.assertEqual(404, self._get_image('evil', 'html').status_code)
        self.assertEqual(404, self._get_image('evil', 'unknownext').status_code)
        self.assertEqual(404, self._get_image('evil', 'svg', mode='crop', size=(50, 50)).status_code)

    def test_served_image_security_headers(self):
        with open(self._test_image_path('png_image.png'), 'rb') as png_image:
            self.assertEqual(201, self._put_image(png_image, 'headers_test.png').status_code)
        for resp in (
            self._get_image('headers_test', 'png'),
            self._get_image('headers_test', 'png', mode='fit', size=(100, 100)),
        ):
            self.assertEqual(200, resp.status_code)
            self.assertEqual('nosniff', resp.headers.get('X-Content-Type-Options'))
            self.assertIn("default-src 'none'", resp.headers.get('Content-Security-Policy', ''))
            self.assertIn('sandbox', resp.headers.get('Content-Security-Policy', ''))
            self.assertEqual('inline', resp.headers.get('Content-Disposition'))

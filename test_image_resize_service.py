import unittest
import io
import image_resize_service as img_service
from PIL import Image

try:
    from google.appengine.ext import testbed

    APPENGINE_AVAILABLE = True
except ImportError:
    APPENGINE_AVAILABLE = False


class APITestCase(unittest.TestCase):
    """tests the HTTP API using the configured storage
       make sure to configure STORAGE=APPENGINE if you run the code in the dev_appserver or on appspot.
       otherwise you'll get readonly filesystem errors.
    """

    def setUp(self):
        img_service.app.config['TESTING'] = True
        self.app = img_service.app.test_client()
        if APPENGINE_AVAILABLE:
            self.testbed = testbed.Testbed()
            self.testbed.activate()
            self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        if APPENGINE_AVAILABLE:
            self.testbed.deactivate()

    def test_index(self):
        """content doesn't matter. just make sure there is always a welcome page"""
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)

    def test_wrong_method(self):
        """image url only supports GET"""
        rv = self.app.post('/img/demo_project/welcome@small.jpg')
        self.assertEqual(rv.status_code, 405)  # method not allowed

    def test_invalid_project(self):
        """wrong projects return a 404 error"""
        rv = self.app.get('/img/bla/welcome@small.jpg')
        self.assertEqual(rv.status_code, 404)  # not found

    def test_invalid_size(self):
        """unsupported dimensions return a 404 error"""
        rv = self.app.get('/img/demo_project/welcome@blabla.jpg')
        self.assertEqual(rv.status_code, 404)  # not found

    def test_correct_mimetype(self):
        """make sure we get a jpeg image and it's dimension fits the configuration"""
        for dimension_name, dimension in img_service.app.config['PROJECTS']['demo_project'].items():
            rv = self.app.get('/img/demo_project/welcome@' + dimension_name + '.jpg')
            im = Image.open(io.BytesIO(rv.data))
            max_width, max_height = dimension
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, 'image/jpeg')
            self.assertEqual(im.format, 'JPEG')
            self.assertTrue(im.size[0] <= max_width and im.size[1] <= max_height)


if __name__ == '__main__':
    unittest.main()
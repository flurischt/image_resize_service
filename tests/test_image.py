import unittest
import os

from PIL import Image as PILImage

from image_service import image


class TestImage(unittest.TestCase):
    def _test_image_path(self, image_name):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(current_dir, "test_images", image_name)

    def test_fit_image(self):
        image_path = 'png_image.png'
        with open(self._test_image_path('%s' % image_path), 'rb') as png_file:
            pil_image = PILImage.open(png_file)
            self.assertEqual((640, 480), pil_image.size)
            png_file.seek(0)
            pil_image = PILImage.open(image.fit_image(png_file, [200, 200]))
            self.assertEqual((200, 150), pil_image.size)

    def test_crop_image(self):
        image_path = 'png_image.png'
        with open(self._test_image_path('%s' % image_path), 'rb') as png_file:
            pil_image = PILImage.open(png_file)
            self.assertEqual((640, 480), pil_image.size)
            png_file.seek(0)
            pil_image = PILImage.open(image.crop_image(png_file, [200, 200]))
            self.assertEqual((200, 200), pil_image.size)

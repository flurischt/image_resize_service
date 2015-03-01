import unittest

from PIL import Image as PILImage

from image_service import image


class TestImage(unittest.TestCase):
    def test_fit_image(self):
        image_path = 'png_image.png'
        with open('test_images/%s' % image_path, 'r') as png_file:
            pil_image = PILImage.open(png_file)
            self.assertEqual((640, 480), pil_image.size)
            png_file.seek(0)
            pil_image = PILImage.open(image.fit_image(png_file, [200, 200]))
            self.assertEqual((200, 150), pil_image.size)

    def test_crop_image(self):
        image_path = 'png_image.png'
        with open('test_images/%s' % image_path, 'r') as png_file:
            pil_image = PILImage.open(png_file)
            self.assertEqual((640, 480), pil_image.size)
            png_file.seek(0)
            pil_image = PILImage.open(image.crop_image(png_file, [200, 200]))
            self.assertEqual((200, 200), pil_image.size)

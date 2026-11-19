import unittest
import os

from PIL import Image as PILImage

from image_service import image


class TestImage(unittest.TestCase):
    def _test_image_path(self, image_name):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(current_dir, 'test_images', image_name)

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

    def test_fit_jpg_image(self):
        image_path = 'jpg_image.jpg'
        with open(self._test_image_path(image_path), 'rb') as jpg_file:
            pil_image = PILImage.open(jpg_file)
            self.assertEqual((1600, 1200), pil_image.size)
            jpg_file.seek(0)
            with image.fit_image(jpg_file, [200, 200]) as resized:
                pil_image = PILImage.open(resized)
                self.assertEqual((200, 150), pil_image.size)
                self.assertEqual('JPEG', pil_image.format)

    def test_crop_jpg_image(self):
        image_path = 'jpg_image.jpg'
        with open(self._test_image_path(image_path), 'rb') as jpg_file:
            pil_image = PILImage.open(jpg_file)
            self.assertEqual((1600, 1200), pil_image.size)
            jpg_file.seek(0)
            with image.crop_image(jpg_file, [200, 200]) as resized:
                pil_image = PILImage.open(resized)
                self.assertEqual((200, 200), pil_image.size)
                self.assertEqual('JPEG', pil_image.format)

    def test_pil_format_from_mime_type(self):
        self.assertEqual('JPEG', image.pil_format_from_mime_type('image/jpeg'))
        self.assertEqual('PNG', image.pil_format_from_mime_type('image/png'))
        self.assertIsNone(image.pil_format_from_mime_type('text/html'))

    def test_pil_format_from_file_extension(self):
        self.assertEqual('JPEG', image.pil_format_from_file_extension('.jpg'))
        self.assertEqual('JPEG', image.pil_format_from_file_extension('.JPG'))
        self.assertEqual('JPEG', image.pil_format_from_file_extension('.jpeg'))
        self.assertEqual('PNG', image.pil_format_from_file_extension('.png'))

import os
import tempfile
import mimetypes

from PIL import Image, ImageOps


# for now we only support the two formats ;)
def pil_format_from_mime_type(mime_type):
    if mime_type == 'image/jpeg':
        return 'JPEG'
    if mime_type == 'image/png':
        return 'PNG'
    return None


def pil_format_from_file_extension(file_extension):
    mime_type = mimetypes.types_map['%s' % file_extension.lower()]
    return pil_format_from_mime_type(mime_type)


def binary_image(pil_image, format):
    binary = tempfile.TemporaryFile()
    pil_image.save(binary, format)
    binary.seek(0)
    return binary


def fit_image(image, size):
    pil_image = Image.open(image)
    pil_image.thumbnail(size, Image.ANTIALIAS)
    pil_format = pil_format_from_file_extension(os.path.splitext(image.name)[1])
    return binary_image(pil_image, pil_format)


def crop_image(image, size):
    pil_image = Image.open(image)
    cropped_pil_image = ImageOps.fit(pil_image, size, Image.ANTIALIAS, 0.0, (0.5, 0.5))
    pil_format = pil_format_from_file_extension(os.path.splitext(image.name)[1])
    return binary_image(cropped_pil_image, pil_format)

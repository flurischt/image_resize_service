from io import BytesIO
import os
import tempfile

from PIL import Image, ImageOps, UnidentifiedImageError


ALLOWED_EXTENSIONS = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
}

ALLOWED_PIL_FORMATS = ('JPEG', 'PNG')


def mime_type_from_extension(file_extension):
    if not file_extension:
        return None
    normalized = file_extension.lstrip('.').lower()
    return ALLOWED_EXTENSIONS.get(normalized)


# for now we only support the two formats ;)
def pil_format_from_mime_type(mime_type):
    if mime_type == 'image/jpeg':
        return 'JPEG'
    if mime_type == 'image/png':
        return 'PNG'
    return None


def pil_format_from_file_extension(file_extension):
    mime_type = mime_type_from_extension(file_extension)
    if mime_type is None:
        return None
    return pil_format_from_mime_type(mime_type)


def validate_image_data(binary_data, extension):
    expected_format = pil_format_from_file_extension(extension)
    if expected_format is None:
        raise ValueError('Unsupported image extension')
    if not binary_data:
        raise ValueError('Empty image payload')
    try:
        with Image.open(BytesIO(binary_data), formats=ALLOWED_PIL_FORMATS) as pil_image:
            if pil_image.format != expected_format:
                raise ValueError('Image content does not match file extension')
            pil_image.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise ValueError('Invalid or unsupported image content') from exc


def binary_image(pil_image, format):
    binary = tempfile.TemporaryFile()
    pil_image.save(binary, format)
    binary.seek(0)
    return binary


def fit_image(image, size):
    pil_format = pil_format_from_file_extension(os.path.splitext(image.name)[1])
    if pil_format is None:
        raise ValueError('Unsupported image extension')
    with Image.open(image, formats=ALLOWED_PIL_FORMATS) as pil_image:
        pil_image.thumbnail(size, Image.Resampling.LANCZOS)
        return binary_image(pil_image, pil_format)


def crop_image(image, size):
    pil_format = pil_format_from_file_extension(os.path.splitext(image.name)[1])
    if pil_format is None:
        raise ValueError('Unsupported image extension')
    with Image.open(image, formats=ALLOWED_PIL_FORMATS) as pil_image:
        cropped_pil_image = ImageOps.fit(pil_image, size, Image.Resampling.LANCZOS, 0.0, (0.5, 0.5))
        return binary_image(cropped_pil_image, pil_format)

__author__ = 'seed'
import mimetypes


# for now we only support the two formats ;)
def pil_format_from_mime_type(mime_type):
    if mime_type == 'image/jpeg':
        return 'JPEG'
    if mime_type == 'image/png':
        return 'PNG'
    return None


def pil_format_from_file_extension(file_extension):
    mime_type = mimetypes.types_map['.%s' % file_extension]
    return pil_format_from_mime_type(mime_type)


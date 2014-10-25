import io

from werkzeug.exceptions import NotFound
from google.appengine.ext import db, blobstore
from google.appengine.ext.db import Error as DatastoreError

from storage import ImageStorage


class Image(db.Model):
    project = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    extension = db.StringProperty(required=True)
    size = db.StringProperty(default='')
    image_data = db.BlobProperty(required=True)


class DatastoreImageStorage(ImageStorage):

    def _get_single_image(self, project, name, extension, size=None):
        im = Image.gql("WHERE project = :1 AND name = :2 AND extension = :3 AND size = :4",
                       project, name, extension, self._size_for_query(size)
        )
        return im.get()

    def exists(self, project, name, extension, size=None):
        if not self._get_single_image(project, name, extension, size):
            return False
        else:
            return True

    def save(self, project, name, extension, binary_image_data, size=None):
        im = self._get_single_image(project, name, extension, size)
        if not im:
            im = Image(project=project, name=name, extension=extension, size=self._size_for_query(size),
                           image_data=binary_image_data
            )
        im.image_data = binary_image_data
        im.put()

    def get(self, project, name, extension, size=None):
        im = self._get_single_image(project, name, extension, size)
        if not im:
            raise NotFound()
        fd = io.BytesIO(im.image_data)
        fd.write(im.image_data)
        fd.seek(0)
        return fd

    def delete(self, project, name, extension, size=None):
        if not self.exists(project, name, extension, size):
            return False
        image = self._get_single_image(project, name, extension, size)
        try:
            image.delete()
            return True
        except DatastoreError:
            return False

    def _size_for_query(self, size):
        if not size:
            return ''
        else:
            return size

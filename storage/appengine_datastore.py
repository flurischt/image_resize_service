import io

from werkzeug.exceptions import NotFound
from google.appengine.ext import db
from google.appengine.ext.db import Error as DatastoreError

from storage import ImageStorage


class Image(db.Model):
    project = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    extension = db.StringProperty(required=True)
    mode = db.StringProperty(default='')
    image_data = db.BlobProperty(required=True)


class DatastoreImageStorage(ImageStorage):

    def _get_single_image(self, project, name, extension, mode=None):
        im = Image.gql("WHERE project = :1 AND name = :2 AND extension = :3 AND mode = :4",
                       project, name, extension, self._mode_for_query(mode)
        )
        return im.get()

    def exists(self, project, name, extension, mode=None):
        if not self._get_single_image(project, name, extension, mode):
            return False
        else:
            return True

    def save(self, project, name, extension, binary_image_data, mode=None):
        im = self._get_single_image(project, name, extension, mode)
        if not im:
            im = Image(project=project, name=name, extension=extension, mode=self._mode_for_query(mode),
                           image_data=binary_image_data
            )
        im.image_data = binary_image_data
        im.put()

    def get(self, project, name, extension, mode=None):
        im = self._get_single_image(project, name, extension, mode)
        if not im:
            raise NotFound()
        fd = io.BytesIO(im.image_data)
        fd.write(im.image_data)
        fd.seek(0)
        return fd

    def delete(self, project, name, extension, mode=None):
        if not self.exists(project, name, extension, mode):
            return False
        image = self._get_single_image(project, name, extension, mode)
        try:
            image.delete()
            return True
        except DatastoreError:
            return False

    def _mode_for_query(self, mode):
        if not mode:
            return ''
        else:
            return mode

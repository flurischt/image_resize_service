import io
from image_storage import ImageStorage
from werkzeug.exceptions import NotFound
from google.appengine.ext import db


class Image(db.Model):
    project = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    extension = db.StringProperty(required=True)
    size = db.StringProperty(default='')
    image_data = db.BlobProperty(required=True)


class DatastoreImageStore(ImageStorage):
    @staticmethod
    def _get_single_image(project, name, extension, size=None):
        im = Image.gql("WHERE project = :1 AND name = :2 AND extension = :3 AND size = :4",
                       project, name, extension, DatastoreImageStore._size_for_query(size)
        )
        return im.get()

    @staticmethod
    def exists(project, name, extension, size=None):
        if not DatastoreImageStore._get_single_image(project, name, extension, size):
            return False
        else:
            return True

    @staticmethod
    def save(project, name, extension, binary_image_data, size=None):
        im = DatastoreImageStore._get_single_image(project, name, extension, size)
        if not im:
            im = Image(project=project, name=name, extension=extension, size=DatastoreImageStore._size_for_query(size),
                           image_data=binary_image_data
            )
        im.image_data = binary_image_data
        im.put()

    @staticmethod
    def get(project, name, extension, size=None):
        im = DatastoreImageStore._get_single_image(project, name, extension, size)
        if not im:
            raise NotFound()
        fd = io.BytesIO(im.image_data)
        fd.write(im.image_data)
        fd.seek(0)
        return fd

    @staticmethod
    def _size_for_query(size):
        if not size:
            return ''
        else:
            return size

# TODO evil stuff here... rewrite
# do an initial datastore update to push the model into the database
# this way the app engine admin interface displays the model...
if not DatastoreImageStore.exists('demo_project', 'welcome', 'jpg'):
    f = file('demo_image_dir/images/demo_project/welcome.jpg', 'r')
    DatastoreImageStore.save('demo_project', 'welcome', 'jpg', f.read())
    f.close()
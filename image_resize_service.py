import os.path as op

from flask import Flask, render_template, send_from_directory, safe_join
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename
from PIL import Image


app = Flask(__name__)


def _path_to_image(name, extension, project, size=None, join_path=False):
    if size:
        filename = secure_filename('%s_%s.%s' % (name, size, extension))
        directory = app.config['RESIZED_DIR']
    else:
        filename = secure_filename(name + '.' + extension)
        directory = app.config['SOURCE_DIR']
    directory = directory + '/' + project
    if join_path:
        return safe_join(directory, filename)
    else:
        return directory, filename


def _calc_size(target_size, image):
    max_width, max_height = target_size
    width, height = image.size
    if max_width >= width and max_height >= height:
        return image.size  # no resize needed
    scale = min(max_width/float(width), max_height/float(height))
    return int(width*scale), int(height*scale)


def _resize_image(project, name, extension, size):
    source_image = _path_to_image(name, extension, project, join_path=True)
    target_image = _path_to_image(name, extension, project, size=size, join_path=True)
    if not op.isfile(source_image):
        raise NotFound()
    im = Image.open(source_image)
    im = im.resize(_calc_size(app.config['PROJECTS'][project][size], im))
    im.save(target_image, 'JPEG')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/img/<project>/<name>@<size>.<extension>', methods=['GET'])
def serve_image(project, name, size, extension):
    if not project in app.config['PROJECTS'] or not size in app.config['PROJECTS'][project]:
        raise NotFound()
    (source_dir, requested_file) = _path_to_image(name, extension, project, size)
    if not op.isfile(safe_join(source_dir, requested_file)):
        _resize_image(project, name, extension, size)
    return send_from_directory(source_dir, requested_file, mimetype='image/jpeg')


if __name__ == '__main__':
    config = op.join(app.root_path, 'production.cfg')
    app.config.from_pyfile(config)
    app.run()

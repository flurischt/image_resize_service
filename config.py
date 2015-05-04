import os

# the following two lines are just for demo purposes
# remove this import and __STATIC_DIR_FOR_DEMO out of your production config
# and configure SOURCE_DIR and RESIZED_DIR for your needs.
import os.path as op

BASE_DIR = op.dirname(op.realpath(__file__))

# the directory where you want to store the source images (if using FILESYSTEM storage)
STORAGE_DIRECTORY = os.path.join(BASE_DIR, 'storage')

# enables demo
STORAGE_DIRECTORY = os.environ.get('STORAGE_DIR', os.path.join(BASE_DIR, 'storage'))
ENABLE_DEMO = os.environ.get('ENABLE_DEMO', 'True') == 'True'
AUTH_TOKEN = os.environ.get('AUTH_TOKEN', '*:demo').split(":") \
    if ":" in os.environ.get('AUTH_TOKEN', '*:demo') else ""
AUTH_BASIC = os.environ.get('AUTH_BASIC', 'uploader:uploader').split(":") \
    if ":" in os.environ.get('AUTH_BASIC', 'uploader:uploader') else ""
import os

# the following two lines are just for demo purposes
# remove this import and __STATIC_DIR_FOR_DEMO out of your production config
# and configure SOURCE_DIR and RESIZED_DIR for your needs.
import os.path as op

BASE_DIR = op.dirname(op.realpath(__file__))

# the directory where you want to store the source images (if using FILESYSTEM storage)
STORAGE_DIRECTORY = os.environ.get('STORAGE_DIR', os.path.join(BASE_DIR, 'storage'))

# demo page is disabled by default; configure auth via environment variables
ENABLE_DEMO = os.environ.get('ENABLE_DEMO', 'False').lower() == 'true'
_raw_auth_token = os.environ.get('AUTH_TOKEN', '')
AUTH_TOKEN = _raw_auth_token.split(":") if ":" in _raw_auth_token else ""
_raw_auth_basic = os.environ.get('AUTH_BASIC', '')
AUTH_BASIC = _raw_auth_basic.split(":") if ":" in _raw_auth_basic else ""
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
if ':' in _raw_auth_token:
    _origin, _token = _raw_auth_token.rsplit(':', 1)
    AUTH_TOKEN = (_origin, _token) if _origin and _token else ""
else:
    AUTH_TOKEN = ""

_raw_auth_basic = os.environ.get('AUTH_BASIC', '')
if ':' in _raw_auth_basic:
    _user, _password = _raw_auth_basic.split(':', 1)
    AUTH_BASIC = (_user, _password) if _user and _password else ""
else:
    AUTH_BASIC = ""

# Resource limits (DoS protection)
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
MAX_IMAGE_PIXELS = int(os.environ.get('MAX_IMAGE_PIXELS', 25_000_000))
MAX_IMAGE_DIMENSION = int(os.environ.get('MAX_IMAGE_DIMENSION', 4096))

_raw_allowed_dims = os.environ.get('ALLOWED_DIMENSIONS', '').strip()
if _raw_allowed_dims:
    ALLOWED_DIMENSIONS = frozenset(
        tuple(int(part) for part in item.strip().lower().split('x', 1))
        for item in _raw_allowed_dims.split(',')
        if 'x' in item.lower()
    )
else:
    ALLOWED_DIMENSIONS = None
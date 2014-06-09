"""package for the storage backends

see ImageStorage for the interface.
FileImageStorage implements the configuration value STORAGE=FILESYSTEM
and DatastoreImageStorage implements access to the app engine datastore

:copyright: (c) 2014 by Flurin Rindisbacher.
:license: BSD 2-Clause, see LICENSE for more details.
"""

from image_storage import ImageStorage
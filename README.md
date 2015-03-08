Image Service
========
A flask based and google app engine compatible webapp to resize images.

Requirements available in pip:
 - Pillow (or PIL on app engine)
 - flask
 
for Pillow you'll need at least libjpeg: 
 - osx: brew install libpjeg
 - linux: use your packet manager
 - windows: use google, or just don't use windows ;)

Installation (OSX)
-----
brew install libjpeg
pip install -r requirements.txt
 
Usage (flask built in server)
-----
 - python runserver.py
 - open http://127.0.0.1:5000/

API
-----
Legend:
---

<project> = project name added in config
<image_name> = image name without extension
<extension> = image file extension
<width> = Desired image width
<height> = Desired image height

uploading images
---
POST /images/<project>

Notice: enctype must be "multipart/form-data"

Updating images
---
PUT /images/<project>/<image_name>.<extension>

Deleting images
---
DELETE /images/<project>/<image_name>.<extension>

Orginal image
---
GET /images/<project>/<image_name>.<extension>

fitting images
---
GET /images/<project>/<image_name>@fit-<width>x<height>.<extension>

cropping images
---
GET /images/<project>/<image_name>@crop-<with>x<height>.<extension>


TODO
-----
 - add some info on how to run this app using a webserver

Copyright
-------
- demo image taken from http://www.reddit.com/r/EarthPorn/comments/20vygp/the_eiger_switzerland_1600x1200/

License
-------
BSD 2-Clause, see the LICENSE file


Copyright 2014 Flurin Rindisbacher

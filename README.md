image_resize_service
========
a flask based and google app engine compatible webapp to resize images. specify a project and some image dimensions (production.cfg), put your images into the source directory and then use "/img/image_name@dimension.extension" as image-src to get resized images.
depending on your images you won't get images that exactly match the configured dimension but all images will fit into the bounding box.

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

for the python dependencies you might want to use virtualenv:
 - virtualenv test_env
 - source test_env/bin/activate 

and then:
pip install -r requirements.txt
 
Usage (flask built in server)
-----
 - python image_resize_service.py
 - open http://127.0.0.1:5000/

make sure to source bin/activate if using virtualenv

make sure that PIL is in your pythonpath too. (virtualenv?)

Production use
-----
Apache
---
Not yet. search google to see how a flask app can be hosted. 
for performance reasons it would make sense to have the webserver serve your images and only use this service for non-existing images.
on apache this could be implemented using .htaccess and some rewrite if not exists rules.

API
-----
fitting images
---
GET /img/PROJECTNAME/image_name_without_extension@fit-<width>x<height>.extension

cropping images
---
GET /img/PROJECTNAME/image_name_without_extension@crop-<with>x<height>.extension

uploading images
---
POST /upload
project=THE_NAME_OF_THE_PROJECT
file=your image

enctype must be "multipart/form-data"
check /uploadform to see an example

/upload is HTTP basic protected. you need to use the username/password configured in production.cfg
Output is json containing either { 'status' : 'OK', 'url' : 'url_to_uploaded_fullsize_image' } (HTTP Statuscode 200)
or { 'status' : 'fail', 'message' : 'some_error_message' } (HTTP Statuscode 500)

checkout /api/spec.html#!/spec.json for the full documentation

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

image_resize_service
========
[![Build Status](https://travis-ci.org/flurischt/image_resize_service.svg?branch=master)](https://travis-ci.org/flurischt/image_resize_service)

a flask based and google app engine compatible webapp to resize images. specify a project and some image dimensions (production.cfg), put your images into the source directory and then use "/img/image_name@dimension.extension" as image-src to get resized images.
depending on your images you won't get images that exactly match the configured dimension but all images will fit into the bounding box.

Requirements available in pip:
 - Pillow (or PIL on app engine)
 - flask
 
for Pillow you'll need at least libjpeg: 
 - osx: brew install libpjeg
 - linux: use your packet manager
 - windows: use google

Installation (OSX)
-----
brew install libjpeg

for the python dependencies you might want to use virtualenv:
 - virtualenv test_env
 - source test_env/bin/activate 

and then:
pip install flask Pillow
 
Usage (flask built in server)
-----
 - configure STORAGE='FILESYSTEM' in production.cfg
 - python image_resize_service.py
 - open http://127.0.0.1:5000/

make sure to source bin/activate if using virtualenv

Usage (app engine)
-----
 - configure STORAGE='APPENGINE' in production.cfg
 - cd image_resize_service_source_directory
 - mkdir lib
 - pip install -r requirements_appengine.txt -t lib
 - dev_appserver.py .
 - open http://127.0.0.1:8080/

make sure that PIL is in your pythonpath too. (virtualenv?)

Production use
-----
Apache
---
Not yet. search google to see how a flask app can be hosted. 
for performance reasons it would make sense to have the webserver serve your images and only use this service for non-existing images.
on apache this could be implemented using .htaccess and some rewrite if not exists rules.

App engine
--- 
you need to deploy this application and also the required libraries inside the lib/ folder. 
DO NOT install Pillow into lib/. use virtualenv for development or install it globally on your machine. but not on app engine.
 - make sure the required libraries are installed in the lib/ folder (see USAGE above)
 - add your own application id to app.yaml (replace image-resize-service on the first line)
 - deploy using "appcfg.py update ."

API
-----
resizing images
---
GET /img/PROJECTNAME/image_name_without_extension@dimension.extension

uploading images
---
POST /upload
project=THE_NAME_OF_THE_PROJECT
file=your image

enctype must be "multipart/form-data"
check /uploadform to see an example

/upload is HTTP basic protected. you need to use the username/password configured in production.cfg

TODO
-----
 - currently image_resize_service will always output "image/jpeg" the file extension is just ignored...
 - add some info on how to run this app using a webserver
 - write a frontend for uploading source_images and make the projects and dimensions configurable AND remove the hack in storage/appengine_datastore...
 
License
-------
BSD 2-Clause, see the LICENSE file

Copyright 2014 Flurin Rindisbacher

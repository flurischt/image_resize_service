image_resize_service
========
a flask based webapp to resize images. specify a project and some image dimensions (production.cfg), put your images into the source directory and then use "/img/image_name@dimension.extension" as image-src to get resized images.
depending on your images you won't get images that exactly match the configured dimension but all images will fit into the bounding box.

Requirements available in pip:
 - Pillow
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
 
Usage
-----
python image_resize_service.py
open http://127.0.0.1:5000/

make sure to source bin/activate if using virtualenv

Production use
-----
Not yet. search google to see how a flask app can be hosted. 
for performance reasons it would make sense to have the webserver serve your images and only use this service for non-existing images.
on apache this could be implemented using .htaccess and some rewrite if not exists rules.

TODO
-----
 - currently image_resize_service will always output "image/jpeg" the file extension is just ignored...
 - add some info on how to run this app using a webserver 
 
License
-------
BSD 2-Clause, see the LICENSE file

Copyright 2014 Flurin Rindisbacher

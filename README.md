Image Service
========
A flask based and google app engine compatible webapp to resize images.

Requirements available in pip:
 - Pillow (or PIL on app engine)
 - flask
 
for Pillow you'll need at least libjpeg: 

 - brew install libpjeg #OS X
 - linux: use your packet manager
 - windows: use google, or just don't use windows ;)

Installation (OSX)
-----

	brew install libjpeg
	pip install -r requirements.txt

 
Usage (flask built in server)
-----

	python runserver.py
	open http://127.0.0.1:5000/
 
 
Docker
-----
To run the service on docker you can use the Dockerfile from this project. The service will run with uwsgi and will be linked into an nginx webserver:

    # Create docker image for uwsgi image_service
    docker build -t image_service .
    
    # create volume container for the image data
    docker create --name="image_service_data" image_service /bin/true
    
    # run the image_service
    docker run -d -t --volumes-from image_service_data --name="image_service" image_service 
    
    # Create docker image for the nginx webserver
    docker build -t nginx ./nginx/
    
    # run nginx by linking it with the image_service
    docker run -d -t -p 80:80 --link image_service:image_service --name="nginx" nginx


API
-----
Legend:
---

\<image_name\> = image name without extension
\<extension\> = image file extension
\<width\> = Desired image width
\<height\> = Desired image height

uploading images
---
POST /images/

Notice: enctype must be "multipart/form-data"

Updating images
---
PUT /images/\<image_name\>.\<extension\>

Deleting images
---
DELETE /images/\<image_name\>.\<extension\>

Orginal image
---
GET /images/\<image_name\>.\<extension\>

fitting images
---
GET /images/\<image_name\>@fit-\<width\>x\<height\>.\<extension\>

cropping images
---
GET /images/\<image_name\>@crop-\<with\>x\<height\>.\<extension\>


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

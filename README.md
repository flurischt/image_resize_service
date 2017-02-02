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
To run the service on docker you can use the Dockerfile from this project. This will create a container running a uwsgi service

    # Create docker image for uwsgi image_service
    docker build -t image_service .
    
    # create volume container for the image data
    docker create --name="image_service_data" image_service /bin/true
    
    # run the image_service
    docker run -d -t --volumes-from image_service_data --name="image_service" image_service 
    
You can now for example use a nginx Server...

nginx.conf:

    upstream image_service {
        server image_service:8000;
	}
	server {
	    listen 8000;
	    server_name localhost;
	    client_max_body_size 10M;
	    location / {
		     uwsgi_pass image_service;
		     include uwsgi_params;
        }
    }
    
Dockerfile:
    
    FROM nginx
    EXPOSE 80

    RUN rm -f /etc/nginx/conf.d/default.conf
    COPY ./nginx.conf /etc/nginx/conf.d/nginx.conf
    
Create nginx container:

    docker build -t "nginx" .
    docker run -d -t -p 80:80 --name="nginx" --link image_service:image_service nginx

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

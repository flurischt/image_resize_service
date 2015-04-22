############################################################
# Dockerfile to build Python WSGI Application Containers
# Based on Ubuntu
############################################################

# Set the base image to Ubuntu
FROM ubuntu

# File Author / Maintainer
MAINTAINER Chris Weber

# Add the application resources URL
RUN echo "deb http://archive.ubuntu.com/ubuntu/ $(lsb_release -sc) main universe" >> /etc/apt/sources.list

# Update the sources list
RUN apt-get update

# Install basic applications
RUN apt-get install -y libjpeg-dev zlib1g-dev python2.7 python-pip

# Install Python and Basic Python Tools
RUN apt-get install -y  

# Create the volume
VOLUME /image_data

# Set envoronment variables
ENV IMAGE_SERVICE_CONFIG /app/docker.cfg
ENV IMAGE_SERVICE_STORAGE_DIR /image_data

# Expose ports
EXPOSE 5000

# Copy the application folder inside the container
ADD . /app

# Set the default directory where CMD will execute
WORKDIR /app

# Get pip to download and install requirements:
RUN pip install -r /app/requirements.txt

# Set the default command to execute
CMD python runserver.py


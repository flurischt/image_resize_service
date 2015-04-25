FROM python:2.7.9
MAINTAINER Chris Weber

# Install UWSGI
RUN pip install uwsgi 

# Create the volume
VOLUME /image_data

# Set environment variables
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


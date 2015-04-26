FROM python:2.7.9
MAINTAINER Chris Weber

# Set environment variables
ENV IMAGE_SERVICE_CONFIG "/app/docker.cfg"
ENV IMAGE_SERVICE_STORAGE_DIR "/data/image_service
ENV IMAGE_SERVICE_ENABLE_DEMO True
ENV IMAGE_SERVICE_AUTH_TOKEN "*:token"
ENV IMAGE_SERVICE_AUTH_BASIC "uploader:uploader"

VOLUME data/image_service

# Expose ports
EXPOSE 80

# Copy the application folder inside the container
ADD ./image_service /app/image_service
ADD ./requirements.txt /app/
ADD ./config.py /app/

# Set the default directory where CMD will execute
WORKDIR /app

# Install UWSGI
RUN pip install uwsgi
RUN pip install -r /app/requirements.txt

# Set the default command to execute
CMD uwsgi --uwsgi-socket 0.0.0.0:80 -w "image_service:app"

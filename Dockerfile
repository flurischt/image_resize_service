FROM python:2.7.9
MAINTAINER Chris Weber

# Install UWSGI
RUN pip install uwsgi

# Expose ports
EXPOSE 5000

# Set environment variables
ENV IMAGE_SERVICE_CONFIG "/app/docker.cfg"
ENV IMAGE_SERVICE_STORAGE_DIR "/image_data"
ENV IMAGE_SERVICE_ENABLE_DEMO True
ENV IMAGE_SERVICE_AUTH_TOKEN "*:token"
ENV IMAGE_SERVICE_AUTH_BASIC "uploader:uploader"


# Expose ports
EXPOSE 5000

# Copy the application folder inside the container
ADD ./image_service /app/image_service
ADD ./requirements.txt /app

# Set the default directory where CMD will execute
WORKDIR /app



# Set the default command to execute
CMD uwsgi --uwsgi-socket 0.0.0.0:5000 -w ${WSGI_MODULE:-wsgi:application}
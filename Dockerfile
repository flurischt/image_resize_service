FROM python:2.7.9
MAINTAINER Chris Weber

# Set environment variables
ENV STORAGE_DIR "/data/image_service
ENV ENABLE_DEMO True
ENV AUTH_TOKEN "*:token"
ENV AUTH_BASIC "uploader:uploader"

VOLUME $STORAGE_DIR

# Expose ports
EXPOSE 8000

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
CMD uwsgi --uwsgi-socket 0.0.0.0:8000 -w "image_service:app"

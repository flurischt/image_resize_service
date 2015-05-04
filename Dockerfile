FROM python:2.7.9
MAINTAINER Chris Weber

# Set environment variables
ENV STORAGE_DIR "/data/image_service/storage"
ENV ENABLE_DEMO True
ENV AUTH_TOKEN "*:demo"
ENV AUTH_BASIC "uploader:uploader"

# PIP Install
COPY ./requirements.txt /app/
RUN pip install uwsgi -r /app/requirements.txt

# Copy the application folder inside the container
COPY ./image_service /app/image_service
COPY ./config.py /app/

# Set the default directory where CMD will execute
VOLUME $STORAGE_DIR
# Expose ports
EXPOSE 8000

WORKDIR /app
ENTRYPOINT ["/usr/local/bin/uwsgi","--uwsgi-socket", "0.0.0.0:8000", "-w", "image_service:app"]
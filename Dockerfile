FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt /app/
RUN pip install --no-cache-dir uwsgi==2.0.31 -r /app/requirements.txt

FROM python:3.12-slim
LABEL org.opencontainers.image.authors="Flurin Ineichen"

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV STORAGE_DIR="/var/lib/image_service/data"
ENV ENABLE_DEMO="True"
ENV AUTH_TOKEN="*:demo"
ENV AUTH_BASIC="uploader:uploader"

COPY --from=builder /opt/venv /opt/venv

# Copy the application folder inside the container
COPY ./image_service /app/image_service
COPY ./config.py /app/

# Set the default directory where CMD will execute
VOLUME $STORAGE_DIR
# Expose ports
EXPOSE 8000

WORKDIR /app
ENTRYPOINT ["/opt/venv/bin/uwsgi", "--uwsgi-socket", "0.0.0.0:8000", "--enable-threads", "--module", "image_service:app"]
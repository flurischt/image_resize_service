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

RUN groupadd --system image_service && \
    useradd --system --gid image_service --home-dir /app --shell /usr/sbin/nologin image_service && \
    mkdir -p "$STORAGE_DIR" && \
    chown -R image_service:image_service /var/lib/image_service

COPY --from=builder /opt/venv /opt/venv

# Copy the application folder inside the container (read-only for runtime user)
COPY ./image_service /app/image_service
COPY ./config.py /app/

# Set the default directory where CMD will execute
VOLUME $STORAGE_DIR
# Expose ports
EXPOSE 8000

WORKDIR /app
USER image_service
ENTRYPOINT ["/opt/venv/bin/uwsgi", "--uwsgi-socket", "0.0.0.0:8000", "--enable-threads", "--module", "image_service:app"]
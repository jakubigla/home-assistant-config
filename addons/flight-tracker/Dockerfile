ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM ${BUILD_FROM}

WORKDIR /app

# Install build dependencies for pandas, then clean up
RUN apk add --no-cache --virtual .build-deps \
        gcc musl-dev python3-dev && \
    pip install --no-cache-dir \
        pandas==2.2.3 \
        FlightRadarAPI==1.3.48 \
        aiohttp==3.11.18 && \
    apk del .build-deps

COPY run.py flight_tracker.py fr24_client.py processing.py ./
COPY static/ ./static/

CMD ["python", "-u", "run.py"]

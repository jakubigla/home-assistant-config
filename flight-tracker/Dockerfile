ARG BUILD_FROM
FROM ${BUILD_FROM}

WORKDIR /app

# Install Python and pip permanently, build deps temporarily
RUN apk add --no-cache python3 py3-pip && \
    apk add --no-cache --virtual .build-deps \
        gcc musl-dev python3-dev && \
    pip install --no-cache-dir --break-system-packages \
        pandas==2.2.3 \
        FlightRadarAPI==1.4.0 \
        beautifulsoup4 \
        aiohttp==3.11.18 && \
    apk del .build-deps

COPY run.py flight_tracker.py fr24_client.py processing.py ./
COPY static/ ./static/

# s6-overlay run script
RUN mkdir -p /etc/services.d/flight-tracker
COPY run.sh /etc/services.d/flight-tracker/run
RUN chmod a+x /etc/services.d/flight-tracker/run

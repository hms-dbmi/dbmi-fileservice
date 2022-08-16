FROM hmsdbmitc/dbmisvc:debian11-slim-python3.10-0.5.0 AS builder

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bzip2 \
        gcc \
        default-libmysqlclient-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Add requirements
ADD requirements.* /

# Build Python wheels with hash checking
RUN pip install -U wheel \
    && pip wheel -r /requirements.txt \
        --wheel-dir=/root/wheels

FROM hmsdbmitc/dbmisvc:debian11-slim-python3.10-0.5.0

# Copy Python wheels from builder
COPY --from=builder /root/wheels /root/wheels

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Add requirements files
ADD requirements.* /

# Install Python packages from wheels
RUN pip install --no-index \
        --find-links=/root/wheels \
        --force-reinstall \
        # Use requirements without hashes to allow using wheels.
        # For some reason the hashes of the wheels change between stages
        # and Pip errors out on the mismatches.
        -r /requirements.in

# Copy app source
COPY /fileservice /app

# Set app parameters. These can be overridden in the ECS Task Definition's container environment variables.
ENV DBMI_ENV=prod
ENV DBMI_PARAMETER_STORE_PREFIX=dbmi.fileservice.${DBMI_ENV}
ENV DBMI_PARAMETER_STORE_PRIORITY=true
ENV DBMI_AWS_REGION=us-east-1
ENV DBMI_APP_WSGI=fileservice
ENV DBMI_APP_ROOT=/app
ENV DBMI_APP_DB=true
ENV DBMI_APP_DOMAIN=fileservice.dbmi.hms.harvard.edu

# Static files
ENV DBMI_STATIC_FILES=true
ENV DBMI_APP_STATIC_URL_PATH=/static
ENV DBMI_APP_STATIC_ROOT=/app/assets

# Set nginx and network parameters
ENV DBMI_NGINX_USER=nginx
ENV DBMI_PORT=443
ENV DBMI_LB=true
ENV DBMI_SSL=true
ENV DBMI_CREATE_SSL=true
ENV DBMI_HEALTHCHECK=true
ENV DBMI_FILE_PROXY=true
ENV DBMI_FILE_PROXY_PATH=/proxy
ENV S3_USE_SIGV4=true

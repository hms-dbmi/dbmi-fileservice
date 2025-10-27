ARG DBMISVC_IMAGE=hmsdbmitc/dbmisvc:debian12-slim-python3.11-0.7.2

FROM ${DBMISVC_IMAGE} AS builder

# Install requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bzip2 \
        gcc \
        default-libmysqlclient-dev \
        libssl-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Add requirements
ADD requirements.* /

# Build Python wheels with hash checking
RUN pip install -U wheel \
    && pip wheel -r /requirements.txt \
        --wheel-dir=/root/wheels

FROM ${DBMISVC_IMAGE}

ARG APP_NAME="dbmi-fileservice"
ARG APP_CODENAME="dbmi-fileservice"
ARG VERSION
ARG COMMIT
ARG DATE

LABEL org.label-schema.schema-version=1.0 \
    org.label-schema.vendor="HMS-DBMI" \
    org.label-schema.version=${VERSION} \
    org.label-schema.name=${APP_NAME} \
    org.label-schema.build-date=${DATE} \
    org.label-schema.description="DBMI Fileservice" \
    org.label-schema.url="https://github.com/hms-dbmi/dbmi-fileservice" \
    org.label-schema.vcs-url="https://github.com/hms-dbmi/dbmi-fileservice" \
    org.label-schema.vcf-ref=${COMMIT}

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

# Setup entry scripts
ADD docker-entrypoint-init.d/* /docker-entrypoint-init.d/

# Copy app source
COPY /fileservice /app

# Set app parameters. These can be overridden in the ECS Task Definition's container environment variables.
ENV DBMI_APP_NAME=${APP_NAME}
ENV DBMI_APP_CODENAME=${APP_CODENAME}
ENV DBMI_APP_VERSION=${VERSION}
ENV DBMI_APP_COMMIT=${COMMIT}
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

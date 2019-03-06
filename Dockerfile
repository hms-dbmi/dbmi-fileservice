FROM python:3.6-alpine3.8 AS builder

# Install dependencies
RUN apk add --update \
    build-base \
    g++ \
    libffi-dev \
    mariadb-dev \
    git

# Add requirements
ADD requirements.txt /requirements.txt

# Install Python packages
RUN pip install -r /requirements.txt

FROM hmsdbmitc/dbmisvc:3.6-alpine-zip

RUN apk add --no-cache --update \
    mariadb-connector-c git libffi-dev git \
  && rm -rf /var/cache/apk/*

# Copy pip packages from builder
COPY --from=builder /root/.cache /root/.cache

# Add requirements
ADD requirements.txt /requirements.txt

# Install Python packages
RUN pip install -r /requirements.txt

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
ENV DBMI_PORT=443
ENV DBMI_LB=true
ENV DBMI_SSL=true
ENV DBMI_CREATE_SSL=true
ENV DBMI_HEALTHCHECK=true
ENV DBMI_FILE_PROXY=true
ENV DBMI_FILE_PROXY_PATH=/proxy

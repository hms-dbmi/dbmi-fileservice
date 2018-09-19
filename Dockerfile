FROM python:2.7-alpine3.8 AS builder

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

FROM hmsdbmitc/dbmisvc:2.7-alpine

RUN apk add --no-cache --update \
    mariadb-connector-c git libffi-dev \
  && rm -rf /var/cache/apk/*

# Copy pip packages from builder
COPY --from=builder /root/.cache /root/.cache

# Add requirements
ADD requirements.txt /requirements.txt

# Install Python packages
RUN pip install -r /requirements.txt

# Add additional init scripts
ADD /docker-entrypoint-init.d/* /docker-entrypoint-init.d/

# Copy app source
COPY /fileservice /app

# Set the build env
ENV DBMI_ENV=prod

# Set app parameters
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

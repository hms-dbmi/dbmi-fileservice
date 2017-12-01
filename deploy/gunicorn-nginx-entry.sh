#!/bin/bash

export SECRET_KEY=$(aws ssm get-parameters --names $PS_PATH.django_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export ALLOWED_HOSTS=$(aws ssm get-parameters --names $PS_PATH.allowed_hosts --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export ADMIN_EMAILS=$(aws ssm get-parameters --names $PS_PATH.admin_emails --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export AWS_S3_UPLOAD_BUCKET=$(aws ssm get-parameters --names $PS_PATH.aws_s3_upload_bucket --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export AUTH0_DOMAIN=$(aws ssm get-parameters --names $PS_PATH.auth0_domain --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export AUTH0_CLIENT_ID=$(aws ssm get-parameters --names $PS_PATH.auth0_client_id --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export AUTH0_SECRET=$(aws ssm get-parameters --names $PS_PATH.auth0_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export AUTH0_CLIENT_SECRET=$(aws ssm get-parameters --names $PS_PATH.auth0_client_secret --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export AUTH0_SUCCESS_URL=$(aws ssm get-parameters --names $PS_PATH.auth0_success_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export AUTH0_CALLBACK_URL=$(aws ssm get-parameters --names $PS_PATH.auth0_callback_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export ACCOUNT_SERVER_URL=$(aws ssm get-parameters --names $PS_PATH.account_server_url --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

export MYSQL_HOST=$(aws ssm get-parameters --names $PS_PATH.mysql_host --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export MYSQL_NAME=$(aws ssm get-parameters --names $PS_PATH.mysql_name --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export MYSQL_USER=$(aws ssm get-parameters --names $PS_PATH.mysql_user --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
export MYSQL_PASSWORD=$(aws ssm get-parameters --names $PS_PATH.mysql_password --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')


# Get SSL certs and prepare nginx
SSL_KEY=$(aws ssm get-parameters --names $PS_PATH.ssl_key --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN1=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain1 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN2=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain2 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')
SSL_CERT_CHAIN3=$(aws ssm get-parameters --names $PS_PATH.ssl_cert_chain3 --with-decryption --region us-east-1 | jq -r '.Parameters[].Value')

SSL_CERT_CHAIN="$SSL_CERT_CHAIN1$SSL_CERT_CHAIN2$SSL_CERT_CHAIN3"

echo $SSL_KEY | base64 -d >> /etc/nginx/ssl/server.key
echo $SSL_CERT_CHAIN | base64 -d >> /etc/nginx/ssl/server.crt

# Specify the settings.
export DJANGO_SETTINGS_MODULE=fileservice.settings.dbmi

cd /app/

python manage.py migrate
python manage.py loaddata initial_data
python manage.py collectstatic --noinput

# Add admin users
for i in $(echo $ADMIN_EMAILS | sed "s/,/ /g")
do
    python /app/manage.py shell <<EOF
from django.contrib.auth import get_user_model
get_user_model().objects.create_superuser(username=next(iter('$i'.split('@')), '$i'[:30]), email='$i', password=None)
EOF

done

# Link nginx logs to stdout/stderr
ln -sf /dev/stdout /var/log/nginx/access.log
ln -sf /dev/stderr /var/log/nginx/error.log

/etc/init.d/nginx restart

gunicorn fileservice.wsgi:application -b 0.0.0.0:8000 --chdir=/app --log-level=debug --log-file=- --access-logfile=- --timeout 600
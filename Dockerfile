FROM python:2.7

# Installing os packages
RUN	apt-get -y update && \
 	nginx apache2-utils unzip && \
 	apt-get clean && \
 	rm -rf /tmp/* /var/lib/apt/lists/*

# Installing python packages
RUN pip install gunicorn

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY fileservice /app/

WORKDIR /app/

# Copying files required for NGINX.
RUN rm -rf /etc/nginx/sites-available/default
RUN mkdir /etc/nginx/ssl/
RUN chmod 710 /etc/nginx/ssl/
COPY deploy/app.conf /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/app.conf /etc/nginx/sites-enabled/app.conf

RUN mkdir /entry_scripts/
COPY deploy/gunicorn-nginx-entry.sh /entry_scripts/
RUN chmod u+x /entry_scripts/gunicorn-nginx-entry.sh

ENTRYPOINT ["/entry_scripts/gunicorn-nginx-entry.sh"]
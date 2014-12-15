#!/bin/bash
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

install() {
 apt-get update
 apt-get install -y libpq-dev wget
 apt-get install -y python-dev
 apt-get install -y libxml2-dev
 apt-get install -y libxslt1-dev
 apt-get install -y python-pip
 apt-get install -y zip
 apt-get install -y python-setuptools
 pip install --upgrade awscli
 wget -qO - https://packages.elasticsearch.org/GPG-KEY-elasticsearch | apt-key add -
 add-apt-repository "deb http://packages.elasticsearch.org/elasticsearch/1.4/debian stable main"
 apt-get update && apt-get install elasticsearch
 update-rc.d elasticsearch defaults 95 10
}

install >/tmp/startup.log 2>&1

cd ${BAMBOODIR}
pip install -r requirements.txt
cd fileservice
./manage.py test filemaster --settings fileservice.settings.local
cd ${BAMBOODIR}
zip -r fileservice.zip .

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/latest/$ARTIFACT

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/${BAMBOOBUILD}/$ARTIFACT

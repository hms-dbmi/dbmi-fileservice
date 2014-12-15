#!/bin/bash
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

install() {
 yum -y update
 yum install -y postgresql-devel
 yum install -y wget
 yum install -y python-devel
 yum install -y libxml2-devel
 yum install -y libxslt-devel
 yum install -y python-pip
 yum install -y zip
 yum install -y python-setuptools
 pip install --upgrade awscli
 yum install -y mysql-client
 rpm --import https://packages.elasticsearch.org/GPG-KEY-elasticsearch
 cat <<< '
[elasticsearch-1.4]
name=Elasticsearch repository for 1.4.x packages
baseurl=http://packages.elasticsearch.org/elasticsearch/1.4/centos
gpgcheck=1
gpgkey=http://packages.elasticsearch.org/GPG-KEY-elasticsearch
enabled=1' > /etc/yum.repos.d/elasticsearch.repo
 yum install -y elasticsearch
 chkconfig --add elasticsearch
 export JAVA_HOME=/usr/lib/jvm/jre-1.7.0
 /etc/init.d/elasticsearch restart
}

install >/tmp/startup.log 2>&1

cd ${BAMBOODIR}
sudo pip install -r requirements.txt
cd fileservice
./manage.py test filemaster --settings fileservice.settings.local
cd ${BAMBOODIR}
zip -r fileservice.zip .

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/latest/$ARTIFACT

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/${BAMBOOBUILD}/$ARTIFACT

#!/bin/bash
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

sudo  yum -y update
sudo  yum install -y postgresql-devel
sudo  yum install -y wget
sudo  yum install -y python-devel python27 python27-devel libyaml-devel
sudo  yum install -y libxml2-devel
sudo  yum install -y libxslt-devel
sudo  yum install -y python-pip
sudo  yum install -y zip
sudo  yum install -y python-setuptools
sudo  pip install --upgrade awscli
sudo  pip install --upgrade virtualenv
sudo  yum install -y mysql-devel
sudo  rpm --import https://packages.elasticsearch.org/GPG-KEY-elasticsearch

sudo bash -c 'cat << EOF > /etc/yum.repos.d/elasticsearch.repo
[elasticsearch-1.4]
name=Elasticsearch repository for 1.4.x packages
baseurl=http://packages.elasticsearch.org/elasticsearch/1.4/centos
gpgcheck=1
gpgkey=http://packages.elasticsearch.org/GPG-KEY-elasticsearch
enabled=1
EOF'

sudo  yum install -y elasticsearch
sudo  chkconfig --add elasticsearch
JAVA_HOME=/usr/lib/jvm/jre-1.7.0 sudo /etc/init.d/elasticsearch restart
cd ~
wget https://bootstrap.pypa.io/ez_setup.py -O - |sudo python27
sudo  /usr/bin/easy_install-2.7 pip
sudo  /usr/bin/pip2.7 install --upgrade awscli
sudo  /usr/bin/pip2.7 install --upgrade virtualenv

cd ~
virtualenv -p /usr/bin/python2.7 python

cd ~/python
. bin/activate
pip install -r ${BAMBOODIR}/requirements.txt
cd ${BAMBOODIR}/fileservice
./manage.py migrate --settings fileservice.settings.local
./manage.py syncdb --settings fileservice.settings.local
DJANGO_SETTINGS_MODULE="fileservice.settings.local_dev" celery  worker -A fileservice --loglevel=info -b django:// &
TEST_AWS_KEY=${TEST_AWS_KEY} TEST_AWS_SECRET=${TEST_AWS_SECRET}  ./manage.py test filemaster --settings fileservice.settings.local
TESTCODE=$?
echo $TESTCODE
cd ${BAMBOODIR}
zip -r fileservice.zip .
killall -9 celery

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/latest/$ARTIFACT

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/${BAMBOOBUILD}/$ARTIFACT

exit $TESTCODE
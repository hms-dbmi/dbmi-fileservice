#!/bin/bash
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

sudo  yum -y update
sudo  yum install -y postgresql-devel
sudo  yum install -y wget
sudo  yum install -y python-devel python27 python27-devel
sudo  yum install -y libxml2-devel
sudo  yum install -y libxslt-devel
sudo  yum install -y python-pip
sudo  yum install -y zip
sudo  yum install -y python-setuptools
sudo  pip install --upgrade awscli
sudo  pip install --upgrade virtualenv
sudo  yum install -y mysql-devel
sudo  rpm --import https://packages.elasticsearch.org/GPG-KEY-elasticsearch

sudo  cat <<< '
[elasticsearch-1.4]
name=Elasticsearch repository for 1.4.x packages
baseurl=http://packages.elasticsearch.org/elasticsearch/1.4/centos
gpgcheck=1
gpgkey=http://packages.elasticsearch.org/GPG-KEY-elasticsearch
enabled=1' > /etc/yum.repos.d/elasticsearch.repo

sudo  yum install -y elasticsearch
sudo  chkconfig --add elasticsearch
JAVA_HOME=/usr/lib/jvm/jre-1.7.0 /etc/init.d/elasticsearch restart
cd ~
wget https://bootstrap.pypa.io/ez_setup.py -O - |sudo python27
sudo  /usr/bin/easy_install-2.7 pip
sudo  /usr/bin/pip2.7 install --upgrade awscli
sudo  /usr/bin/pip2.7 install --upgrade virtualenv

cd ~
/usr/bin/virtualenv-2.7 python

cd ~/python
. bin/activate
cd ~
pip install -r ${BAMBOODIR}/requirements.txt
pip install --upgrade drf-compound-fields
cd ${BAMBOODIR}/fileservice
python27 manage.py test filemaster --settings fileservice.settings.local
TESTCODE=$?
echo $TESTCODE
cd ${BAMBOODIR}
zip -r fileservice.zip .

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/latest/$ARTIFACT

AWS_ACCESS_KEY_ID=${ACCESS_KEY} AWS_SECRET_ACCESS_KEY=${SECRET_KEY} aws s3 cp ${BAMBOODIR}/${ORIGARTIFACT} s3://cbmi_artifacts/${KEYNAME}/${DEVENV}/${BAMBOOBUILD}/$ARTIFACT

exit $TESTCODE
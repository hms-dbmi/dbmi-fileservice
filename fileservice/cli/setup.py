#!/usr/bin/env python

PROJECT = 'fileservice'

# Change docs/sphinx/conf.py too!
VERSION = '0.1'

from setuptools import setup, find_packages

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='FileServiceCLI',
    long_description=long_description,

    author='David Bernick',
    author_email='david_bernick@hms.harvard.edu',

    url='https://github.com/hms-dbmi/fileservice',

    classifiers=['Development Status :: 3 - Alpha',
                 'License :: OSI Approved :: Apache Software License',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['cliff','requests','jsonschema','boto','nose','coverage','python-magic','libmagic'],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'fileservice = fileservice.main:main'
        ],
        'fileservice.application': [
            #'uploadfile = genomebridge.files:UploadFile',
            #'attributes = genomebridge.dataset:Attributes'
        ],
    },

    zip_safe=False,
)
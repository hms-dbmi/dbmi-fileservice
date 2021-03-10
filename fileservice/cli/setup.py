#!/usr/bin/env python

PROJECT = 'fileservice'

# Change docs/sphinx/conf.py too!
VERSION = '0.2'

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
    author='Daniel Traviglia',
    author_email='daniel_traviglia@hms.harvard.edu',
    url='https://github.com/hms-dbmi/dbmi-fileservice',
    classifiers=[
        'Development Status :: 3 - Alpha',
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
    install_requires=[
        'pyparsing',
        'cliff',
        'requests',
        'jsonschema',
        'boto',
        'coverage',
        'python-magic',
        'libmagic',
        'requests',
        'requests-toolbelt',
        'furl',
        'filechunkio',
    ],
    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'fileservice = fileservice.main:main'
        ],
        'fileservice.application': [
            'search = fileservice.files:SearchFiles',
            'list = fileservice.files:ListFiles',
            'view = fileservice.files:ReadFile',
            'write = fileservice.files:WriteFile',
            'download = fileservice.files:DownloadFile',
            'upload = fileservice.files:UploadFile',
            'post = fileservice.files:PostFile',
            'udn = fileservice.udn:RegisterFile',
        ],
    },
    zip_safe=False,
)

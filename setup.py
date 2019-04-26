# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2018 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from setuptools import setup


def read_description(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fp:
        return fp.read()


setup(name='er-calvin',
      version='1.1.1',
      url="http://github.com/EricssonResearch/calvin-base",
      license="Apache Software License",
      author="Team Calvin @ Ericsson Research",
      author_email="labs@ericsson.com",
      tests_require=[
          'pytest>=4.3.1',
          'pytest-twisted>=1.9'
      ],
      install_requires=[
        'colorlog==4.0.2',
        'ply==3.11',
        'Twisted==18.9.0',
        'requests==2.21.0',
        'requests-futures==0.9.9',
        'wrapt==1.11.1',
        'netifaces==0.10.9',
        'pyOpenSSL==19.0.0',
        'cryptography==2.6.1',
        'passlib==1.7.1',
        'PyJWT==1.7.1',
        'service-identity==18.1.0',
        'ndg-httpsclient==0.5.1',
        'pyasn1==0.4.5',
        'pystache==0.5.4',
        'jsonschema==3.0.1',
        'u-msgpack-python==2.5.1',
        'cbor==1.0.0',
        'PyYAML==5.1',
        'Flask==1.0.2'
      ],
      description="Calvin is a distributed runtime and development framework for an actor based dataflow"
                  "programming methodology",
      long_description=read_description('README.md'),
      long_description_content_type="text/markdown",
      packages=["calvin", "calvinextras", "calvinservices"],
      include_package_data=True,
      platforms='any',
      test_suite="calvin.test.test_calvin",
      classifiers=[
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.7",
          "Development Status :: 4 - Beta",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
          "Framework :: Twisted",
          "Natural Language :: English",
          "Intended Audience :: Developers",
          "Topic :: Software Development",
      ],
      python_requires=">=3.7",
      keywords="iot dataflow actors distributed internet-of-things cloud-computing programming",
      entry_points={
          'console_scripts': [
              'csruntime=tools.csruntime:main',
              'cscontrol=tools.cscontrol:main',
              'csdocs=tools.calvindoc:main',
              'cssysdocs=tools.calvinsysdoc:main',
              'cscompile=calvinservices.csparser.cscompiler:main',
              'csmanage=tools.csmanage:main',
              'csweb=tools.www.csweb:main',
              'csviz=tools.csviz:main',
              'csactorstore=calvinservices.actorstore.store_app:main',
              'csregistry=calvinservices.registry.registry_app:main',
          ]
      }
)

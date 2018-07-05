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
      version='1.0.1',
      url="http://github.com/EricssonResearch/calvin-base",
      license="Apache Software License",
      author="Team Calvin @ Ericsson Research",
      author_email="labs@ericsson.com",
      tests_require=[
          'mock>1.0.1',
          'pytest>=1.4.25',
          'pytest-twisted'
      ],
      install_requires=[
        'colorlog==2.6.1',
        'rpcudp==1.0',
        'kademlia==0.5',
        'ply==3.8',
        'Twisted==15.5.0',
        'requests==2.9.1',
        'infi.traceback==0.3.12',
        'wrapt==1.10.2',
        'netifaces==0.10.4',
        'pyOpenSSL==17.1.0',
        'cryptography==1.9.0',
        'passlib==1.7.0',
        'PyJWT==1.4.0',
        'service-identity==17.0.0',
        'ndg-httpsclient==0.4.2',
        'pyasn1>=0.4.2',
        'pystache==0.5.4',
        'jsonschema==2.6.0',
        'u-msgpack-python==2.4.1',
        'cbor==1.0.0'
      ],
      description="Calvin is a distributed runtime and development framework for an actor based dataflow"
                  "programming methodology",
      long_description=read_description('README.md'),
      long_description_content_type="text/markdown",
      packages=["calvin"],
      include_package_data=True,
      platforms='any',
      test_suite="calvin.test.test_calvin",
      classifiers=[
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Development Status :: 4 - Beta",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
          "Framework :: Twisted",
          "Natural Language :: English",
          "Intended Audience :: Developers",
          "Topic :: Software Development",
      ],
      python_requires=">=2.7",
      keywords= "iot dataflow actors distributed internet-of-things cloud-computing programming",
      entry_points={
          'console_scripts': [
              'csruntime=calvin.Tools.csruntime:main',
              'cscontrol=calvin.Tools.cscontrol:main',
              'csdocs=calvin.Tools.calvindoc:main',
              'cssysdocs=calvin.Tools.calvinsysdoc:main',
              'cscompile=calvin.Tools.cscompiler:main',
              'csmanage=calvin.Tools.csmanage:main',
              'csweb=calvin.Tools.www.csweb:main',
              'csviz=calvin.Tools.csviz:main'
          ]
      }
      )

# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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


setup(name='calvin',
      version='0.5',
      url="http://github.com/EricssonResearch/calvin-base",
      license="Apache Software License",
      author="Ericsson Research",
      author_email="N/A",
      tests_require=[
          'mock>1.0.1',
          'pytest>=1.4.25',
          'pytest-twisted'
      ],
      install_requires=[
          'colorlog==2.6.1',
          'kademlia==0.5',
          'ply==3.8',
          'Twisted==15.5.0',
          'requests==2.9.1',
          'infi.traceback==0.3.12',
          'wrapt==1.10.2',
          'pyserial==3.0.1',
          'netifaces==0.10.4',
          'pyOpenSSL==0.15.1',
          'service-identity==16.0.0'
      ],
      description="Calvin is a distributed runtime and development framework for an actor based dataflow"
                  "programming methodology",
      long_description=read_description('README.md'),
      packages=["calvin"],
      include_package_data=True,
      platforms='any',
      test_suite="calvin.test.test_calvin",
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.7",
          "Development Status :: 3 - Alpha",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
          "Framework :: Twisted",
          "Natural Language :: English",
          "Intended Audience :: Developers",
          "Topic :: Software Development",
      ],
      entry_points={
          'console_scripts': [
              'csruntime=calvin.Tools.csruntime:main',
              'cscontrol=calvin.Tools.cscontrol:main',
              'csdocs=calvin.Tools.calvindoc:main',
              'cscompile=calvin.Tools.cscompiler:main',
              'csinstall=calvin.Tools.csinstaller:main',
              'csmanage=calvin.Tools.csmanage:main',
              'csweb=calvin.Tools.www.csweb:main',
              'csviz=calvin.Tools.csviz:main'
          ]
      }
      )

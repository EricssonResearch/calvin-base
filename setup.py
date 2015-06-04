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


def make_parser():
    from calvin.csparser.parser import make_parser
    make_parser()


def read_desc(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def read_reqs(fname):
    with open(fname, "r") as f:
        requirements = f.readlines()
    return requirements

# Create parsetab before setup
make_parser()

setup(name='calvin',
      version='0.1',
      url="http://github.com/EricssonResearch/calvin-base",
      license="Apache Software License",
      author="Ericsson Research",
      author_email="N/A",
      tests_require=read_reqs('test-requirements.txt'),
      install_requires=read_reqs('requirements.txt'),
      description="Calvin is a distributed runtime and development framework for an actor based dataflow"
                  "programming methodology",
      long_description=read_desc('README.md'),
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
      extras_require={
          'testing': ['pytest', 'mock']
      },
      entry_points={
          'console_scripts': [
              'csdeploy=calvin.Tools.deploy_app:main',
              'csdocs=calvin.Tools.calvindoc:main',
              'cscompile=calvin.Tools.cscompiler:main',
              'csinstall=calvin.Tools.csinstaller:main',
              'csweb=calvin.Tools.www.csweb:main'
          ]
      }
      )

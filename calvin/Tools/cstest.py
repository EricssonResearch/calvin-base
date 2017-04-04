#!/usr/bin/env python
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

import argparse as Argparse
import calvin.actorstore.tests.test_actors as Test
import os.path as Path

def main():
  argparser = Argparse.ArgumentParser(description="Run actor unit tests")
  argparser.add_argument('path', type=str, nargs='*',
                       help='path(s) below which to run actor tests')
  args = argparser.parse_args()
  results = None
  files = [];

  if len(args.path) == 0:
    args.path.append(".")

  # Collect python files
  def collect(arg, path, files):
    for file in files:
      name,ext = Path.splitext(file)
      if ext == '.py' and name != '__init__':
        arg.append(Path.join(path, file))

  for path in args.path:
    if Path.isdir(path):
      Path.walk(path, collect, files)
    else:
      files.append(path)

  files = set(files)

  def merge(res1, res2):
    if res1 == None:
      return res2
    return Test.merge_results(res1, res2)

  for file in files:
    print(">>>>> "+file)
    results = merge(results, Test.test_actors(path=file, show=True))

  Test.show_results(results)

if __name__ == '__main__':
  main()

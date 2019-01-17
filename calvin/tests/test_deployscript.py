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

from calvin.csparser.dscodegen import calvin_dscodegen
import pytest


tests = [
    (
        'CheckSimpleScript1',
        r"""
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
    
        rule simple: node_attr(node_name={"name": "simple_rt"})
        apply a, b: simple 
        """
    ),
    (
        'CheckSimpleScript2',
        r"""
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
    
        rule simple: node_attr(node_name={"name": "simple_rt"}) & node_attr(owner={"personOrGroup": "me"})
        apply a, b: simple 
        """
    ),
    (
        'CheckSimpleScript3',
        r"""
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
    
        rule simple: node_attr(node_name={"name": "simple_rt1"}) | node_attr(node_name={"name": "simple_rt2"})
        apply a, b: simple 
        """
    ),
    (
        'CheckHierarchicalScript1',
        r"""
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
    
        rule union: node_attr(node_name={"name": "simple_rt1"}) | node_attr(node_name={"name": "simple_rt2"})
        rule hierarchical: union & ~current()
        apply a, b: hierarchical 
        """
    ),
    (
        'CheckOnlyDeployScript',
        r"""
        rule union: node_attr(node_name={"name": "simple_rt1"}) | node_attr(node_name={"name": "simple_rt2"})
        rule hierarchical: union & ~current()
        apply a, b: hierarchical 
        """
    ),
    (
        'CheckOnlyCalvinScript',
        r"""
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        """
    )
]

@pytest.mark.parametrize('test', tests)
def test_script(actorstore, test):
    name, script = test
    requirements, issuetracker = calvin_dscodegen(script, name)
    assert issuetracker.error_count == 0


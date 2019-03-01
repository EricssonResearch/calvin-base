# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
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


from __future__ import print_function
from __future__ import absolute_import
from copy import copy, deepcopy

class BaseNode(object):
    
    _verbose_desc = False

    """Base class for all nodes in CS AST"""
    def __init__(self, **kwargs):
        super(BaseNode, self).__init__()
        self.parent = None
        self.children = []
        self.debug_info = kwargs.get('debug_info')

    def delete(self):
        if not self.parent:
            raise Exception("Can't remove root node {}".format(self))
        self.parent.remove_child(self)
    
    def clone(self):
        x = copy(self)
        x.parent = None
        return x

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {}".format(self.__class__.__name__, hex(id(self)), self.debug_info)
        else:
            return "{}".format(self.__class__.__name__)
    
class LeafNode(BaseNode):
    pass

class Node(BaseNode):
    
    def add_child(self, child):
        if child:
            child.parent = self
        self.children.append(child)

    def add_children(self, children):
        for child in children:
            self.add_child(child)

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def remove_children(self, children):
        for child in children:
            self.remove_child(child)

    def replace_child(self, old, new):
        if not old in self.children:
            return False
        i = self.children.index(old)
        self.children[i] = new
        new.parent = self
        return True
        
    
class IdValuePair(Node):
    """Abstract: don't use directly, use NamedArg or Constant"""
    def __init__(self, **kwargs):
        super(IdValuePair, self).__init__(**kwargs)
        self.add_children([kwargs.get('ident'), kwargs.get('arg')])

    @property
    def ident(self):
        return self.children[0]

    @ident.setter
    def ident(self, value):
        value.parent = self
        self.ident.parent = None
        self.children[0] = value

    @property
    def arg(self):
        return self.children[1]

    @arg.setter
    def inport(self, value):
        value.parent = self
        self.arg.parent = None
        self.children[1] = value

class NamedArg(IdValuePair):
    """docstring for ConstNode"""
    pass
    
class Constant(IdValuePair):
    """docstring for ConstNode"""
    pass
    
class Id(LeafNode):
    """docstring for IdNode"""
    def __init__(self, **kwargs):
        super(Id, self).__init__(**kwargs)
        self.ident = kwargs.get('ident')

class Value(LeafNode):
    """docstring for ValueNode"""
    def __init__(self, **kwargs):
        super(Value, self).__init__(**kwargs)
        self.value = kwargs.get('value')

class Assignment(Node):
    """docstring for AssignmentNode"""
    def __init__(self, **kwargs):
        super(Assignment, self).__init__(**kwargs)
        self.metadata = None
        self.ident = kwargs.get('ident')
        self.actor_type = kwargs.get('actor_type')
        self.add_children(kwargs.get('args', {}))

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {} {}".format(self.__class__.__name__, hex(id(self)), self.metadata, self.debug_info)
        else:
            return "{} {}".format(self.__class__.__name__, self.metadata)

class PortProperty(Node):
    """docstring for PortPropertyNode"""
    def __init__(self, **kwargs):
        super(PortProperty, self).__init__(**kwargs)
        self.actor = kwargs.get('actor')
        self.port = kwargs.get('port')
        self.direction = kwargs.get('direction')
        self.add_children(kwargs.get('args', {}))

    def __str__(self):
        if self._verbose_desc:
            return "{} {}.{} {} {}".format(self.__class__.__name__, str(self.actor), self.port, hex(id(self)),
                                                self.debug_info)
        else:
            return "{} {}.{}".format(self.__class__.__name__, str(self.actor), self.port)

class Link(Node):
    """docstring for LinkNode"""
    def __init__(self, **kwargs):
        super(Link, self).__init__(**kwargs)
        self.add_children([kwargs.get('outport'), kwargs.get('inport')])

    def remove_child(self, child):
        raise Exception("Can't remove child from {}".format(self))

    @property
    def outport(self):
        return self.children[0]

    @outport.setter
    def outport(self, value):
        value.parent = self
        self.outport.parent = None
        self.children[0] = value

    @property
    def inport(self):
        return self.children[1]

    @inport.setter
    def inport(self, value):
        value.parent = self
        self.inport.parent = None
        self.children[1] = value

    def __str__(self):
        if self._verbose_desc:
            return "{} {} > {} {} {}".format(self.__class__.__name__, str(self.outport), str(self.inport),
                                                hex(id(self)), self.debug_info)
        else:
            return "{} {} > {}".format(self.__class__.__name__, str(self.outport), str(self.inport))

class Void(LeafNode):
    """docstring for Void"""
    pass

class TransformedPort(LeafNode):
    def __init__(self, **kwargs):
        super(TransformedPort, self).__init__(**kwargs)
        self.port = kwargs.get('port')
        self.value = kwargs.get('value')
        self.label = kwargs.get('label')


class ImplicitPort(Node):
    """docstring for ImplicitPortNode"""
    def __init__(self, **kwargs):
        super(ImplicitPort, self).__init__(**kwargs)
        self.add_child(kwargs.get('arg'))
        self.add_child(kwargs.get('label'))

    @property
    def arg(self):
        return self.children[0]

    @arg.setter
    def arg(self, value):
        value.parent = self
        self.arg.parent = None
        self.children[0] = value

    @property
    def label(self):
        return self.children[1]

class PortList(Node):
    """docstring for LinkNode"""
    pass
    
# FIXME: Abstract
class Port(Node):
    """
    Port have properties: actor, port, tag
    Port propeties are stored as children
    """
    def __init__(self, **kwargs):
        super(Port, self).__init__(**kwargs)
        self.actor = kwargs.get('actor')
        self.port = kwargs.get('port')
        self.tag = kwargs.get('tag')

    @property
    def name(self):
        return "{}.{}".format(self.actor, self.port)

    def __str__(self):
        if self._verbose_desc:
            return "{} {}.{} {} {}".format(self.__class__.__name__, str(self.actor), self.port,
                                                hex(id(self)), self.debug_info)
        else:
            return "{} {}.{}".format(self.__class__.__name__, str(self.actor), self.port)

class InPort(Port):
    """docstring for LinkNode"""
    pass
    
class OutPort(Port):
    """docstring for LinkNode"""
    pass
    
class InternalInPort(InPort):
    """docstring for InternalPortNode"""
    def __init__(self, **kwargs):
        super(InternalInPort, self).__init__(actor='', **kwargs)

class InternalOutPort(OutPort):
    """docstring for InternalPortNode"""
    def __init__(self, **kwargs):
        super(InternalOutPort, self).__init__(actor='', **kwargs)

class Block(Node):
    """docstring for ComponentNode"""
    def __init__(self, **kwargs):
        super(Block, self).__init__(**kwargs)
        self.namespace = kwargs.get('namespace', '')
        self.args = kwargs.get('args', {})
        self.add_children(kwargs.get('program', []))

    def clone(self):
        x = deepcopy(self)
        x.parent = None
        return x

class Component(Node):
    """docstring for ComponentNode"""
    def __init__(self, **kwargs):
        super(Component, self).__init__(**kwargs)
        self.name = kwargs.get('name')
        self.namespace = None # For installer # FIXME: Remove, likely cruft
        self.arg_names = kwargs.get('arg_names')
        self.inports = kwargs.get('inports')
        self.outports = kwargs.get('outports')
        self.docstring = kwargs.get('docstring')
        self.add_child(Block(program=kwargs.get('program', [])))

class RuleDefinition(Node):
    def __init__(self, **kwargs):
        super(RuleDefinition, self).__init__(**kwargs)
        self.add_children([kwargs.get('name'), kwargs.get('rule')])

    @property
    def name(self):
        return self.children[0]

    @property
    def rule(self):
        return self.children[1]


class SetOp(Node):
    def __init__(self, **kwargs):
        super(SetOp, self).__init__(**kwargs)
        self.op = kwargs.get('op')
        self.add_children([kwargs.get('left'), kwargs.get('right')])

    @property
    def left(self):
        return self.children[0]

    @left.setter
    def left(self, value):
        value.parent = self
        self.left.parent = None
        self.children[0] = value

    @property
    def right(self):
        return self.children[1]

    @right.setter
    def right(self, value):
        value.parent = self
        self.right.parent = None
        self.children[1] = value

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {} {}".format(self.__class__.__name__, str(self.op), hex(id(self)), self.debug_info)
        else:
            return "{} {}".format(self.__class__.__name__, str(self.op))


class UnarySetOp(Node):
    def __init__(self, **kwargs):
        super(UnarySetOp, self).__init__(**kwargs)
        self.op = kwargs.get('op')
        self.add_children([kwargs.get('rule')])

    @property
    def rule(self):
        return self.children[0]

    @rule.setter
    def rule(self, value):
        value.parent = self
        self.rule.parent = None
        self.children[0] = value

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {} {}".format(self.__class__.__name__, str(self.op), hex(id(self)), self.debug_info)
        else:
            return "{} {}".format(self.__class__.__name__, str(self.op))


class RulePredicate(Node):
    def __init__(self, **kwargs):
        super(RulePredicate, self).__init__(**kwargs)
        self.predicate = kwargs.get('predicate')
        self.add_children(kwargs.get('args', []))

    @property
    def args(self):
        return self.children

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {} {}".format(self.__class__.__name__, self.predicate.ident, hex(id(self)), self.debug_info)
        else:
            return "{} {}".format(self.__class__.__name__, self.predicate.ident)


class Group(Node):
    def __init__(self, **kwargs):
        super(Group, self).__init__(**kwargs)
        self.group = kwargs.get('group')
        self.add_children(kwargs.get('members'))

class RuleApply(Node):
    def __init__(self, **kwargs):
        super(RuleApply, self).__init__(**kwargs)
        self.optional = kwargs.get('optional')
        self.add_children([kwargs.get('rule')] + kwargs.get('targets'))

    @property
    def rule(self):
        return self.children[0]

    @property
    def targets(self):
        return self.children[1:]



################################
#
# Helpers for JSON serialization
#
################################
def node_encoder(instance):
    """
    Use with json.dump(s) like so:
    s = json.dumps(tree, default=node_encoder, indent=2)
    where tree is an AST.
    """
    instance.parent = None
    return {'class':instance.__class__.__name__, 'data':instance.__dict__}

def node_decoder(o):
    """
    Use with json.load(s) like so:
    tree = json.loads(s, object_hook=node_decoder)
    where s is a JSON-formatted string representing an AST.
    """
    if 'class' not in o:
        return o
    instance = {
        'Node':Node,
        'Constant':Constant,
        'Id':Id,
        'Value':Value,
        'Assignment':Assignment,
        'PortProperty':PortProperty,
        'IdValuePair':IdValuePair,
        'NamedArg':NamedArg,
        'Link':Link,
        'Void':Void,
        'TransformedPort':TransformedPort,
        'Port':Port,
        'InPort':InPort,
        'OutPort':OutPort,
        'ImplicitPort':ImplicitPort,
        'InternalInPort':InternalInPort,
        'InternalOutPort':InternalOutPort,
        'Block':Block,
        'Component':Component,
        'RuleApply':RuleApply,
        'Group':Group,
        'SetOp':SetOp,
        'RulePredicate':RulePredicate,
        'UnarySetOp':UnarySetOp
    }.get(o['class'])()
    instance.__dict__ = o['data']
    return instance


if __name__ == '__main__':
    import json
    from . import astprint
    from . import astnode as ast

    Node._verbose_desc = True

    bp = astprint.BracePrinter()

    root = ast.Node()
    root.add_child(ast.Constant(ident=ast.Id(ident="foo"), arg=ast.Value(value=1)))
    bp.process(root)

    s = json.dumps(root, default=ast.node_encoder, indent=2)

    print()
    print(s)
    print()

    tree = json.loads(s, object_hook=ast.node_decoder)
    bp.visit(tree)







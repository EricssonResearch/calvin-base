import inspect
from copy import copy, deepcopy
from calvin.requests import calvinresponse


class Node(object):

    _verbose_desc = False

    """Base class for all nodes in CS AST"""
    def __init__(self, **kwargs):
        super(Node, self).__init__()
        self.parent = None
        self.children = []
        self.debug_info = kwargs.get('debug_info')

    def matches(self, kind=None, attr_dict=None):
        """
        Return True if node type is <kind> and its attributes matches <attr_dict>
        If <kind> or <attr_dict> evaluates to False it will match anything,
        if both evaluates to False this method will always return True.
        If an attribute value is a class, it will match of the property is an instance of that class
        """
        if kind and type(self) is not kind:
            return False
        if not attr_dict:
            # No or empty attr dict matches.
            return True
        for key, value in attr_dict.iteritems():
            if isinstance(key, tuple):
                # Allow matching of sub attributes, usefull when having Id values
                try:
                    attr_value = self
                    for inner_key in key:
                        attr_value = getattr(attr_value, inner_key, None)
                    if inspect.isclass(value):
                        attr_value = type(attr_value)
                    if value != attr_value:
                        return False
                except:
                    return False
            else:
                attr_value = getattr(self, key, None)
                if inspect.isclass(value):
                    attr_value = type(attr_value)
                if value != attr_value:
                    return False
        return True

    def is_leaf(self):
        return self.children is None

    def add_child(self, child):
        if self.is_leaf():
            raise Exception("Can't add children to leaf node {}".format(self))
        if child:
            child.parent = self
        self.children.append(child)

    def add_children(self, children):
        for child in children:
            self.add_child(child)

    def remove_child(self, child):
        if self.is_leaf():
            raise Exception("Can't remove children from leaf node {}".format(self))
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def remove_children(self, children):
        for child in children:
            self.remove_child(child)

    def delete(self):
        if not self.parent:
            raise Exception("Can't remove root node {}".format(self))
        self.parent.remove_child(self)

    def replace_child(self, old, new):
        if self.is_leaf():
            raise Exception("Can't replace child in leaf node {}".format(self))
        if not old in self.children:
            return False
        i = self.children.index(old)
        self.children[i] = new
        new.parent = self
        return True

    def clone(self):
        x = copy(self)
        x.parent = None
        return x

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {}".format(self.__class__.__name__, hex(id(self)), self.debug_info)
        else:
            return "{}".format(self.__class__.__name__)

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
    def __init__(self, **kwargs):
        super(NamedArg, self).__init__(**kwargs)

class Constant(IdValuePair):
    """docstring for ConstNode"""
    def __init__(self, **kwargs):
        super(Constant, self).__init__(**kwargs)

class Id(Node):
    """docstring for IdNode"""
    def __init__(self, **kwargs):
        super(Id, self).__init__(**kwargs)
        self.children = None
        self.ident = kwargs.get('ident')

class Value(Node):
    """docstring for ValueNode"""
    def __init__(self, **kwargs):
        super(Value, self).__init__(**kwargs)
        self.children = None
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

class Void(Node):
    """docstring for Void"""
    def __init__(self, **kwargs):
        super(Void, self).__init__(**kwargs)
        self.children = None

class TransformedPort(Node):
    def __init__(self, **kwargs):
        super(TransformedPort, self).__init__(**kwargs)
        self.children = None
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
    def __init__(self, **kwargs):
        super(PortList, self).__init__(**kwargs)

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
    def __init__(self, **kwargs):
        super(InPort, self).__init__(**kwargs)

class OutPort(Port):
    """docstring for LinkNode"""
    def __init__(self, **kwargs):
        super(OutPort, self).__init__(**kwargs)

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
    import astprint
    import astnode as ast

    Node._verbose_desc = True

    bp = astprint.BracePrinter()

    root = ast.Node()
    root.add_child(ast.Constant(ident=ast.Id(ident="foo"), arg=ast.Value(value=1)))
    bp.process(root)

    s = json.dumps(root, default=ast.node_encoder, indent=2)

    print
    print s
    print

    tree = json.loads(s, object_hook=ast.node_decoder)
    bp.visit(tree)







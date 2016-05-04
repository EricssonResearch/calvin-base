import inspect
from copy import deepcopy

class Node(object):

    _verbose_desc = False

    """Base class for all nodes in CS AST"""
    def __init__(self):
        super(Node, self).__init__()
        self.parent = None
        self.children = []

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
        x = deepcopy(self)
        x.parent = None
        return x

    def __str__(self):
        if self._verbose_desc:
            return "{} {}".format(self.__class__.__name__, hex(id(self)))
        else:
            return "{}".format(self.__class__.__name__)

class Constant(Node):
    """docstring for ConstNode"""
    def __init__(self, ident=None, arg=None):
        super(Constant, self).__init__()
        self.add_children([ident, arg])

class Id(Node):
    """docstring for IdNode"""
    def __init__(self, ident=None):
        super(Id, self).__init__()
        self.children = None
        self.ident = ident

class Value(Node):
    """docstring for ValueNode"""
    def __init__(self, value=None):
        super(Value, self).__init__()
        self.children = None
        self.value = value

class Assignment(Node):
    """docstring for AssignmentNode"""
    def __init__(self, ident=None, actor_type=None, args=None):
        super(Assignment, self).__init__()
        self.ident = ident
        self.actor_type = actor_type
        self.add_children(args or {})

class NamedArg(Node):
    """docstring for ConstNode"""
    def __init__(self, ident=None, arg=None):
        super(NamedArg, self).__init__()
        self.add_children([ident, arg])

class Link(Node):
    """docstring for LinkNode"""
    def __init__(self, outport=None, inport=None):
        super(Link, self).__init__()
        self.add_children([outport, inport])

    def remove_child(self, child=None):
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

# FIXME: Redundant
class Portmap(Link):
    """docstring for Portmap"""
    def __init__(self, outport=None, inport=None):
        super(Portmap, self).__init__(outport, inport)

# FIXME: Abstract
class Port(Node):
    """docstring for LinkNode"""
    def __init__(self, actor=None, port=None):
        super(Port, self).__init__()
        self.children = None
        self.actor = actor
        self.port = port

class InPort(Port):
    """docstring for LinkNode"""
    def __init__(self, actor=None, port=None):
        super(InPort, self).__init__(actor, port)

class OutPort(Port):
    """docstring for LinkNode"""
    def __init__(self, actor=None, port=None):
        super(OutPort, self).__init__(actor, port)

class ImplicitPort(Node):
    """docstring for ImplicitPortNode"""
    def __init__(self, arg=None):
        super(ImplicitPort, self).__init__()
        self.add_child(arg)

class InternalInPort(InPort):
    """docstring for InternalPortNode"""
    def __init__(self, port=None):
        super(InternalInPort, self).__init__('', port)

class InternalOutPort(OutPort):
    """docstring for InternalPortNode"""
    def __init__(self, port=None):
        super(InternalOutPort, self).__init__('', port)

class Block(Node):
    """docstring for ComponentNode"""
    def __init__(self, program = None, namespace="", args=None):
        super(Block, self).__init__()
        self.namespace = namespace
        self.args = args or {}
        self.add_children(program or [])

class Component(Node):
    """docstring for ComponentNode"""
    def __init__(self, name=None, arg_names=None, inports=None, outports=None, docstring=None, program=None):
        super(Component, self).__init__()
        self.name = name
        self.namespace = None # For installer
        self.arg_names = arg_names
        self.inports = inports
        self.outports = outports
        self.docstring = docstring
        self.add_child(Block(program))

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
        'NamedArg':NamedArg,
        'Link':Link,
        'Portmap':Portmap,
        'Port':Port,
        'InPort':InPort,
        'OutPort':OutPort,
        'ImplicitPort':ImplicitPort,
        'InternalInPort':InternalInPort,
        'InternalOutPort':InternalOutPort,
        'Block':Block,
        'Component':Component
    }.get(o['class'])()
    instance.__dict__ = o['data']
    return instance


if __name__ == '__main__':
    Node._verbose_desc = True
    p = Port('foo', 'out')
    l = Link(p, Port('bar', 'in'))
    a = Assignment('foo', 'std.Source', [NamedArg(Id('n'), Value(10)), NamedArg(Id('str'), Value('hello'))])
    print l, l.outport, l.inport
    lc = l.clone()
    print lc, lc.outport, lc.inport

    print a, a.ident, a.actor_type, id(a.children), a.children[0], a.children[1]
    ac = a.clone()
    print ac, ac.ident, ac.actor_type, id(ac.children), ac.children[0], ac.children[1]
    ac.children[0].children[1] = 42
    print a.children[0].children[1], ac.children[0].children[1]

    n = p
    while n:
        print n
        n = n.parent







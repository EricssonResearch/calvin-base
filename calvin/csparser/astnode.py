


class Node(object):
    """Base class for all nodes in CS AST"""
    def __init__(self):
        super(Node, self).__init__()
        self.children = []

class Constant(Node):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(Constant, self).__init__()
        self.children = [ident, arg]

class Id(Node):
    """docstring for IdNode"""
    def __init__(self, ident):
        super(Id, self).__init__()
        self.ident = ident

class Value(Node):
    """docstring for ValueNode"""
    def __init__(self, value):
        super(Value, self).__init__()
        self.value = value

class Assignment(Node):
    """docstring for AssignmentNode"""
    def __init__(self, ident, actor_type, args):
        super(Assignment, self).__init__()
        self.ident = ident
        self.actor_type = actor_type
        self.children = args

class NamedArg(Node):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(NamedArg, self).__init__()
        self.children = [ident, arg]

class Link(Node):
    """docstring for LinkNode"""
    def __init__(self, outport, inport):
        super(Link, self).__init__()
        self.children = [outport, inport]
        self.outport = self.children[0]
        self.inport = self.children[1]

class Port(Node):
    """docstring for LinkNode"""
    def __init__(self, actor, port):
        super(Port, self).__init__()
        self.actor = actor
        self.port = port

class ImplicitPort(Node):
    """docstring for ImplicitPortNode"""
    def __init__(self, arg):
        super(ImplicitPort, self).__init__()
        self.children = [arg]

class InternalPort(Node):
    """docstring for InternalPortNode"""
    def __init__(self, port):
        super(InternalPort, self).__init__()
        self.port = port

class Block(Node):
    """docstring for ComponentNode"""
    def __init__(self, program):
        super(Block, self).__init__()
        self.children = program


class Component(Node):
    """docstring for ComponentNode"""
    def __init__(self, name, arg_names, inports, outports, docstring, program):
        super(Component, self).__init__()
        self.name = name
        self.arg_names = arg_names
        self.inports = inports
        self.outports = outports
        self.docstring = docstring
        self.children = [Block(program)]



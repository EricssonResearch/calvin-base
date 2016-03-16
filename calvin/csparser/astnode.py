from copy import copy, deepcopy


class Node(object):

    _verbose_desc = False

    """Base class for all nodes in CS AST"""
    def __init__(self):
        super(Node, self).__init__()
        self.parent = None
        self.children = []

    def is_leaf(self):
        return self.children is None

    def add_child(self, child):
        if self.is_leaf():
            raise Exception("Can't add children to leaf node {}".format(self))
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


    def __str__(self):
        if self._verbose_desc:
            return "{} {}".format(self.__class__.__name__, hex(id(self)))
        else:
            return "{}".format(self.__class__.__name__)

class Constant(Node):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(Constant, self).__init__()
        self.add_children([ident, arg])

class Id(Node):
    """docstring for IdNode"""
    def __init__(self, ident):
        super(Id, self).__init__()
        self.children = None
        self.ident = ident

class Value(Node):
    """docstring for ValueNode"""
    def __init__(self, value):
        super(Value, self).__init__()
        self.children = None
        self.value = value

class Assignment(Node):
    """docstring for AssignmentNode"""
    def __init__(self, ident, actor_type, args):
        super(Assignment, self).__init__()
        self.ident = ident
        self.actor_type = actor_type
        self.add_children(args)

    def __copy__(self):
        return Assignment(copy(self.ident), copy(self.actor_type), deepcopy(self.children))

class NamedArg(Node):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(NamedArg, self).__init__()
        self.add_children([ident, arg])

    def __copy__(self, memo):
        print "NamedArg.copy"
        return  NamedArg(copy(self.children[0]), copy(self.children[1]))

class Link(Node):
    """docstring for LinkNode"""
    def __init__(self, outport, inport):
        super(Link, self).__init__()
        self.add_children([outport, inport])

    def __copy__(self):
        print "Link", self.outport, copy(self.outport)
        return Link(copy(self.outport), copy(self.inport))

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


class Port(Node):
    """docstring for LinkNode"""
    def __init__(self, actor, port):
        super(Port, self).__init__()
        self.children = None
        self.actor = actor
        self.port = port

class ImplicitPort(Node):
    """docstring for ImplicitPortNode"""
    def __init__(self, arg):
        super(ImplicitPort, self).__init__()
        self.add_child(arg)

class InternalPort(Node):
    """docstring for InternalPortNode"""
    def __init__(self, port):
        super(InternalPort, self).__init__()
        self.children = None
        self.port = port

class Block(Node):
    """docstring for ComponentNode"""
    def __init__(self, program = None):
        super(Block, self).__init__()
        self.add_children(program or [])

    def __copy__(self):
        return Block(deepcopy(self.children))


class Component(Node):
    """docstring for ComponentNode"""
    def __init__(self, name, arg_names, inports, outports, docstring, program):
        super(Component, self).__init__()
        self.name = name
        self.arg_names = arg_names
        self.inports = inports
        self.outports = outports
        self.docstring = docstring
        self.add_child(Block(program))

if __name__ == '__main__':
    # Node._verbose_desc = True
    p = Port('foo', 'out')
    l = Link(p, Port('bar', 'in'))
    a = Assignment('foo', 'std.Source', [NamedArg(Id('n'), Value(10)), NamedArg(Id('str'), Value('hello'))])
    print l, l.outport, l.inport
    lc = copy(l)
    print lc, lc.outport, lc.inport

    print a, a.ident, a.actor_type, id(a.children), a.children[0], a.children[1]
    ac = copy(a)
    print ac, ac.ident, ac.actor_type, id(ac.children), ac.children[0], ac.children[1]
    ac.children[0].children[1] = 42
    print a.children[0].children[1], ac.children[0].children[1]

    n = p
    while n:
        print n
        n = n.parent




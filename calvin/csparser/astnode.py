from copy import copy, deepcopy


class Node(object):

    _verbose_desc = False

    """Base class for all nodes in CS AST"""
    def __init__(self):
        super(Node, self).__init__()
        self.children = []

    def __str__(self):
        if self._verbose_desc:
            return "{} {}".format(self.__class__.__name__, hex(id(self)))
        else:
            return "{}".format(self.__class__.__name__)

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

    def __copy__(self):
        return Assignment(copy(self.ident), copy(self.actor_type), deepcopy(self.children))

class NamedArg(Node):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(NamedArg, self).__init__()
        self.children = [ident, arg]

    def __copy__(self, memo):
        print "NamedArg.copy"
        return  NamedArg(copy(self.children[0]), copy(self.children[1]))

class Link(Node):
    """docstring for LinkNode"""
    def __init__(self, outport, inport):
        super(Link, self).__init__()
        self.children = [outport, inport]

    def __copy__(self):
        print "Link", self.outport, copy(self.outport)
        return Link(copy(self.outport), copy(self.inport))

    @property
    def outport(self):
        return self.children[0]

    @outport.setter
    def outport(self, value):
        self.children[0] = value

    @property
    def inport(self):
        return self.children[1]

    @inport.setter
    def inport(self, value):
        self.children[1] = value


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
    def __init__(self, program = None):
        super(Block, self).__init__()
        self.children = program or []

    def append(self, node):
        index = 0 if type(node) is Assignment else len(self.children)
        self.children.insert(index, node)

    def remove(self, node):
        self.children.remove(node)

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
        self.children = [Block(program)]

if __name__ == '__main__':
    # Node._verbose_desc = True
    l = Link(Port('foo', 'out'), Port('bar', 'in'))
    a = Assignment('foo', 'std.Source', [NamedArg('n', 10), NamedArg('str', 'hello')])
    print l, l.outport, l.inport
    lc = copy(l)
    print lc, lc.outport, lc.inport

    print a, a.ident, a.actor_type, id(a.children), a.children[0], a.children[1]
    ac = copy(a)
    print ac, ac.ident, ac.actor_type, id(ac.children), ac.children[0], ac.children[1]
    ac.children[0].children[1] = 42
    print a.children[0].children[1], ac.children[0].children[1]



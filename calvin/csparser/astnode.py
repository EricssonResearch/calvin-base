


class ASTNode(object):
    """Base class for all nodes in CS AST"""
    def __init__(self):
        super(ASTNode, self).__init__()
        self.children = []

class ConstNode(ASTNode):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(ConstNode, self).__init__()
        self.children = [ident, arg]

class IdNode(ASTNode):
    """docstring for IdNode"""
    def __init__(self, ident):
        super(IdNode, self).__init__()
        self.ident = ident

class ValueNode(ASTNode):
    """docstring for ValueNode"""
    def __init__(self, value):
        super(ValueNode, self).__init__()
        self.value = value

class AssignmentNode(ASTNode):
    """docstring for AssignmentNode"""
    def __init__(self, ident, actor_type, args):
        super(AssignmentNode, self).__init__()
        self.ident = ident
        self.actor_type = actor_type
        self.children = args

class NamedArgNode(ASTNode):
    """docstring for ConstNode"""
    def __init__(self, ident, arg):
        super(NamedArgNode, self).__init__()
        self.children = [ident, arg]

class LinkNode(ASTNode):
    """docstring for LinkNode"""
    def __init__(self, outport, inport):
        super(LinkNode, self).__init__()
        self.children = [outport, inport]

class PortNode(ASTNode):
    """docstring for LinkNode"""
    def __init__(self, actor, port):
        super(PortNode, self).__init__()
        self.actor = actor
        self.port = port

class ImplicitPortNode(ASTNode):
    """docstring for ImplicitPortNode"""
    def __init__(self, arg):
        super(ImplicitPortNode, self).__init__()
        self.children = [arg]


class InternalPortNode(ASTNode):
    """docstring for InternalPortNode"""
    def __init__(self, port):
        super(InternalPortNode, self).__init__()
        self.port = port

class BlockNode(ASTNode):
    """docstring for ComponentNode"""
    def __init__(self, program):
        super(BlockNode, self).__init__()
        self.children = program


class ComponentNode(ASTNode):
    """docstring for ComponentNode"""
    def __init__(self, name, arg_names, inports, outports, docstring, program):
        super(ComponentNode, self).__init__()
        self.name = name
        self.arg_names = arg_names
        self.inports = inports
        self.outports = outports
        self.docstring = docstring
        self.children = [BlockNode(program)]

        # name = p[2]

        # arg_ids = p[4]
        # inputs = p[6]
        # outputs = p[8]
        # docstring = p[10]
        # structure = p[11]
        # comp = {
        #     'name': name,
        #     'inports': inputs,
        #     'outports': outputs,
        #     'arg_identifiers': arg_ids,
        #     'structure': structure,
        #     'docstring': docstring,
        #     'dbg_line':p.lineno(2)
        # }
        # p[0] = {name:comp}



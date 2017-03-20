import inspect
from copy import deepcopy
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

    def next_sibling(self):
        if not self.parent:
            return None
        i = self.parent.children.index(self)
        try:
            return self.parent.children[i + 1]
        except:
            return None

    def prev_sibling(self):
        if not self.parent:
            return None
        i = self.parent.children.index(self)
        try:
            return self.parent.children[i - 1]
        except:
            return None

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

    def is_same_port(self, other):
        return (self.actor == other.actor and self.port == other.port and
            not (self.direction is not None and other.direction is not None and self.direction != other.direction))

    def consolidate(self, other):
        """
        This method consolidates two port properties into one.
        Handling duplicates and conflicts for the same port.
        Assumes check that ports are identical is done!
        """
        my_properties = {p.ident.ident: p for p in self.children}
        other_properties = {p.ident.ident: p for p in other.children}
        consolidate = set(my_properties.keys()) & set(other_properties.keys())
        #keep = set(my_properties.keys()) - set(other_properties.keys())
        add = set(other_properties.keys()) - set(my_properties.keys())

        for prop_name in consolidate:
            # Properties can be tuples/list with alternatives in priority order
            # Consolidate to a common subset in the order of our alternatives
            if my_properties[prop_name].arg.value != other_properties[prop_name].arg.value:
                if isinstance(my_properties[prop_name].arg.value, (tuple, list)):
                    my_prop_list = my_properties[prop_name].arg.value
                else:
                    my_prop_list = [my_properties[prop_name].arg.value]
                if isinstance(other_properties[prop_name].arg.value, (tuple, list)):
                    other_prop_list = other_properties[prop_name].arg.value
                else:
                    other_prop_list = [other_properties[prop_name].arg.value]
                common = set(my_prop_list) & set(other_prop_list)
                if len(common) == 0:
                    raise  calvinresponse.CalvinResponseException(
                                calvinresponse.CalvinResponse(
                                    status=calvinresponse.BAD_REQUEST,
                                    data="Can't handle conflicting properties without common alternatives"))
                # Ordered common
                ordered_common = []
                for p in my_prop_list:
                    if p in common:
                        ordered_common.append(p)
                my_properties[prop_name].arg.value = ordered_common

        for prop_name in add:
            prop = other_properties[prop_name]
            other.remove_child(prop)
            self.add_child(prop)

    def add_property(self, ident, arg):
        my_properties = [p for p in self.children if p.ident.ident == ident]
        if my_properties:
            my_properties[0].arg.value = arg
        else:
            self.add_child(NamedArg(ident=Id(ident=ident), arg=Value(value=arg)))

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


# FIXME: Abstract
class Port(Node):
    """docstring for LinkNode"""
    def __init__(self, **kwargs):
        super(Port, self).__init__(**kwargs)
        self.children = None
        self.actor = kwargs.get('actor')
        self.port = kwargs.get('port')

    @property
    def name(self):
        return "{}.{}".format(self.actor, self.port)

    def __str__(self):
        if self._verbose_desc:
            return "{} {}.{} {} {}".format(self.__class__.__name__, str(self.actor), self.port,
                                                hex(id(self)), self.debug_info)
        else:
            return "{} {}.{}".format(self.__class__.__name__, str(self.actor), self.port)

class PortRef(Port):
    def __init__(self, **kwargs):
        super(PortRef, self).__init__(**kwargs)
        self.direction = kwargs.get('direction')

class InternalPortRef(PortRef):
    def __init__(self, **kwargs):
        super(InternalPortRef, self).__init__(actor='', **kwargs)
        self.direction = kwargs.get('direction')

class PortList(Node):
    """docstring for LinkNode"""
    def __init__(self, **kwargs):
        super(PortList, self).__init__(**kwargs)

class InPort(Port):
    """docstring for LinkNode"""
    def __init__(self, **kwargs):
        super(InPort, self).__init__(**kwargs)

class OutPort(Port):
    """docstring for LinkNode"""
    def __init__(self, **kwargs):
        super(OutPort, self).__init__(**kwargs)

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

class InternalPort(Port):
    """docstring for InternalPortNode"""
    def __init__(self, **kwargs):
        super(InternalPort, self).__init__(actor='', **kwargs)

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

class Rule(Node):
    def __init__(self, **kwargs):
        super(Rule, self).__init__(**kwargs)
        self.rule = kwargs.get('rule')
        # FIXME We only have one expression why is this a child?
        self.add_children([kwargs.get('expression')])

class RuleExpression(Node):
    def __init__(self, **kwargs):
        super(RuleExpression, self).__init__(**kwargs)
        if kwargs and 'first_predicate' in kwargs:
            self.add_child(kwargs.get('first_predicate'))

class RulePredicate(Node):
    def __init__(self, **kwargs):
        super(RulePredicate, self).__init__(**kwargs)
        self.predicate = kwargs.get('predicate')
        self.op = kwargs.get('op', RuleSetOp(op=""))
        self.type = kwargs.get('type')
        self.add_children(kwargs.get('args', []))

    def __str__(self):
        if self._verbose_desc:
            return "{} {} {} {} {}".format(
                self.__class__.__name__, "" if self.op is None else self.op.op,
                self.predicate.ident, hex(id(self)), self.debug_info)
        else:
            return "{} {} {}".format(
                self.__class__.__name__, "" if self.op is None else self.op.op, self.predicate.ident)

class RuleSetOp(Node):
    def __init__(self, **kwargs):
        super(RuleSetOp, self).__init__(**kwargs)
        # op is & intersection, | union and/or with the unary ~ not operator
        self.op = kwargs.get('op')
        self.children = None

class Group(Node):
    def __init__(self, **kwargs):
        super(Group, self).__init__(**kwargs)
        self.group = kwargs.get('group')
        self.add_children(kwargs.get('members'))

class RuleApply(Node):
    def __init__(self, **kwargs):
        super(RuleApply, self).__init__(**kwargs)
        self.optional = kwargs.get('optional')
        self.rule = kwargs.get('rule')
        self.add_children(kwargs.get('targets'))


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
        'InternalPort':InternalPort,
        'InternalInPort':InternalInPort,
        'InternalOutPort':InternalOutPort,
        'InternalPortRef':InternalPortRef,
        'PortRef':PortRef,
        'Block':Block,
        'Component':Component,
        'RuleApply':RuleApply,
        'Group':Group,
        'RuleSetOp':RuleSetOp,
        'RulePredicate':RulePredicate,
        'RuleExpression':RuleExpression,
        'Rule':Rule
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
    bp.visit(root)

    s = json.dumps(root, default=ast.node_encoder, indent=2)

    print
    print s
    print

    tree = json.loads(s, object_hook=ast.node_decoder)
    bp.visit(tree)







import astnode as ast
import visitor
import astprint
from calvin.actorstore.store import ActorStore, GlobalStore


def _create_signature(actor_class, actor_type):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    signature_desc = {'is_primitive': True,
                      'actor_type': actor_type,
                      'inports': actor_class.inport_names,
                      'outports': actor_class.outport_names}
    return GlobalStore.actor_signature(signature_desc)



class Finder(object):
    """
    Perform queries on the tree
    FIXME: Make subclass of Visitor
    """
    def __init__(self):
        pass

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not self.kind or type(node) is self.kind:
            self.matches.append(node)
        if not node.is_leaf() and self.depth < self.maxdepth:
            self.depth += 1
            map(self.visit, node.children)
            self.depth -= 1

    def find_all(self, kind, node, maxdepth):
        """
        Return a list of all nodes matching <kind>, at most <maxdepth> levels
        down from the starting node <node>
        """
        self.depth = 0
        self.kind = kind
        self.maxdepth = maxdepth
        self.matches = []
        self.visit(node)

class Visitor(object):
    def __init__(self, maxdepth=1024):
        self.maxdepth = maxdepth
        self.depth = 0

    def _visit(self, node, preorder=None, inorder=None, postorder=None):
        if node.is_leaf() or self.depth > self.maxdepth:
            # print "maxdepth ({}) exceeded".format(self.depth)
            return
        if preorder: preorder(node)
        left, last = node.children[0:-1], node.children[-1:]
        if not left:
            if last: self.visit(last[0])
            if inorder: inorder(node)
        else:
            self.depth +=1
            for child in left:
                self.visit(child)
                if inorder: inorder(node)
            self.visit(last[0])
            self.depth -=1
        if postorder: postorder(node)

    def _indentation(self):
        return "    "*self.depth

    @visitor.on('node')
    def visit(self, node):
        pass


class ImplicitPortRewrite(Visitor):
    """
    ImplicitPortRewrite takes care of the construct
        <value> > foo.in
    by replacing <value> with a std.Constant(data=<value>) actor.
    """
    def __init__(self, maxdepth=1024):
        super(ImplicitPortRewrite, self).__init__(maxdepth)
        self.kind = ast.ImplicitPort
        self.implicit_port = None
        self.real_port = None
        self.real_constants = []
        self.counter = 0

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        self._visit(node)

    @visitor.when(ast.Block)
    def visit(self, node):
        def g(node):
            if self.real_constants:
                node.children.extend(self.real_constants)
            self.real_constants = []

        self._visit(node, postorder=g)


    @visitor.when(ast.Link)
    def visit(self, node):
        def g(node):
            if self.implicit_port:
                removed = node.outport
                if removed != self.implicit_port:
                    print "ERROR"
                node.outport = self.real_port
                self.real_port = None
                self.implicit_port = None
        self._visit(node, postorder=g)


    @visitor.when(ast.ImplicitPort)
    def visit(self, node):
        self.implicit_port = node
        args = [ ast.NamedArg(ast.Id('data'), node.children[0]),  ast.NamedArg(ast.Id('n'), ast.Value(-1))]
        self.counter += 1
        const_name = '_literal_const_'+str(self.counter)
        self.real_constants.append(ast.Assignment(const_name, 'std.Constant', args))
        self.real_port = ast.Port(const_name, 'token')


class WrapInNamespace(Visitor):
    """docstring for WrapInNamespace"""
    def __init__(self):
        super(WrapInNamespace, self).__init__()

    def wrap(self, node, namespace):
        self.namespace = namespace
        self._visit(node)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        self._visit(node)

    @visitor.when(ast.Port)
    def visit(self, node):
        node.actor = self.namespace + "." + node.actor

    @visitor.when(ast.InternalPort)
    def visit(self, node):
        node.port = self.namespace + "." + node.port

    @visitor.when(ast.Assignment)
    def visit(self, node):
        node.ident = self.namespace + "." + node.ident


class Expander(object):
    """
    Expands a tree with components provided as a dictionary
    """
    def __init__(self, components):
        self.components = components

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.children is None:
            return
        map(self.visit, node.children)

    @visitor.when(ast.Assignment)
    def visit(self, node):
        if node.actor_type not in self.components:
            map(self.visit, node.children)
            return
        # Clone assignment to clone the arguments
        # FIXME: Should args be a node rather than a list?
        ca = node.clone()
        args = ca.children
        # Clone block from component definition
        # FIXME: should block be a propery?
        block = self.components[node.actor_type].children[0]
        new = block.clone()
        new.namespace = node.ident
        # Add arguments from assignment to block
        new.add_children(args)
        node.parent.replace_child(node, new)
        # Recurse
        map(self.visit, new.children)


class CodeGen(object):
    """
    Generate code from a source file
    FIXME: Use a writer class to generate output in various formats
    """
    def __init__(self, ast_root, script_name):
        super(CodeGen, self).__init__()
        self.actorstore = ActorStore()
        self.ast = ast_root
        self.script_name = script_name
        self.constants = {}
        self.local_components = {}
        self.app_info = {'name':script_name}
        self.printer = astprint.BracePrinter()

        self.run()

    def lookup(self, actor_type):
        """
        Search for the definition of 'actor_type'.
        Returns a tuple (found, is_primitive, info) where info is either a
        class (primitive) or a dictionary with component definition
        Search order:
          1 - components defined in the current script: self.local_components
          2 - primitive actors in the order defined by actor store
          3 - components in the order defined by actor store
        Steps 2 and 3 are handled by generic lookup in actor store
        """
        if actor_type in self.local_components:
            compdef = self.local_components[actor_type]
            return compdef, False

        found, is_actor, info = self.actorstore.lookup(actor_type)
        # if self.verify and not found:
        #     msg = 'Actor "{}" not found.'.format(actor_type)
        #     raise Exception(msg)
        return info, is_actor and found


    def run(self, verbose=True):
        ast.Node._verbose_desc = verbose

        # Add sections
        ai = self.app_info
        ai['actors'] = {}
        ai['connections'] = {}
        ai['valid'] = True

        ##
        # Check for errors
        #

        ##
        # Tree re-write
        #
        print
        self.printer.process(self.ast)
        ##
        # 1. Expand components
        #

        components = self.query(ast.Component, self.ast, maxdepth=1)
        for c in components:
            self.local_components[c.name] = c

        expander = Expander(self.local_components)
        expander.visit(self.ast)
        # All component definitions can now be removed
        comps = self.query(ast.Component, self.ast)
        if comps:
            print "WARNING: unused components. ", comps
        for comp in comps:
            comp.delete()
        self.printer.process(self.ast)

        ##
        # 2. Implicit port rewrite
        rw = ImplicitPortRewrite()
        rw.visit(self.ast)

        #
        # "code" generation
        #
        self.process_main(self.ast)


    def get_named_args(self, node):
        """
        Return a dictionary with named args rooted in <node> as key/value-pairs
        """
        args = {}
        argnodes = self.query(ast.NamedArg, node)
        for n in argnodes:
            k, v = n.children
            args[k.ident] = v.value
        return args

    def wrap_in_namespace(self, block, namespace):
        wr = WrapInNamespace()
        wr.wrap(block, namespace)

    def add_actor(self, actor, namespace):
        key = "{}:{}".format(namespace, actor.ident)
        value = {}
        actor_class, is_actor = self.lookup(actor.actor_type)
        value['actor_type'] = actor.actor_type
        value['args'] = self.get_named_args(actor)
        value['signature'] = _create_signature(actor_class, actor.actor_type)
        self.app_info['actors'][key] = value

    def add_link(self, link, namespace):
        key = "{}:{}.{}".format(namespace, link.outport.actor, link.outport.port)
        value = "{}:{}.{}".format(namespace, link.inport.actor, link.inport.port)
        self.app_info['connections'].setdefault(key, []).append(value)

    def process_constants(self, unresolved):
        # FIXME: Handle define FOO = BAR etc. including infinite recursion
        resolved = {}
        for c in unresolved:
            _id, _val = c.children
            if type(_val) is ast.Value:
                self.constants[_id.ident] = _val.value

    def rewrite_implicit_ports(self):
        pass

    def process_main(self, main):
        actors = self.query(ast.Assignment, main)
        links = self.query(ast.Link, main)
        for actor in actors:
            self.add_actor(actor, self.script_name)
        for link in links:
            self.add_link(link, self.script_name)

    def query(self, kind, root, maxdepth=1024):
        finder = Finder()
        finder.find_all(kind, root, maxdepth=maxdepth)
        return finder.matches


if __name__ == '__main__':
    from parser_regression_tests import run_check
    run_check()


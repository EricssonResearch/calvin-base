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
        if node.matches(self.kind, self.attributes):
            self.matches.append(node)
        if not node.is_leaf() and self.depth < self.maxdepth:
            self.depth += 1
            map(self.visit, node.children)
            self.depth -= 1

    def find_all(self, root, kind=None, attributes=None, maxdepth=1024):
        """
        Return a list of all nodes matching <kind>, at most <maxdepth> levels
        down from the starting node <node>
        """
        self.depth = 0
        self.kind = kind
        self.maxdepth = maxdepth
        self.matches = []
        self.attributes = attributes
        self.visit(root)
        return self.matches

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
        ca = node.clone()
        args = ca.children
        # Clone block from component definition
        # FIXME: should block be a propery?
        block = self.components[node.actor_type].children[0]
        new = block.clone()
        new.namespace = node.ident
        # Add arguments from assignment to block
        new.args = {x.children[0].ident: x.children[1] for x in args}
        node.parent.replace_child(node, new)
        # Recurse
        map(self.visit, new.children)


class Flatten(object):
    """
    Flattens a block by wrapping everything in the block's namespace
    and propagating arguments before removing the block
    """
    def __init__(self):
        self.stack = []

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children[:])

    @visitor.when(ast.Assignment)
    def visit(self, node):
        self.stack.append(node.ident)
        node.ident = ':'.join(self.stack)
        self.stack.pop()
        map(self.visit, node.children[:])


    @visitor.when(ast.NamedArg)
    def visit(self, node):
        value_node = node.children[1]
        if type(value_node) is ast.Id:
            # Get value from grandparent (block)
            block = node.parent.parent
            key = value_node.ident
            if key not in block.args:
                print "WARNING: Missing symbol '{}'".format(key)
            else:
                value = block.args[key]
                node.replace_child(value_node, value)

    @visitor.when(ast.InternalPort)
    def visit(self, node):
        node.actor = ':'.join(self.stack)

    @visitor.when(ast.Port)
    def visit(self, node):
        node.actor = ':'.join(self.stack + [node.actor])

    @visitor.when(ast.Block)
    def visit(self, node):
        for key, value_node in node.args.iteritems():
            if type(value_node) is ast.Id:
                # Get value from parent (block)
                block = node.parent
                parent_key = value_node.ident
                if parent_key not in block.args:
                    print "WARNING: Missing symbol '{}'".format(parent_key)
                else:
                    value = block.args[parent_key]
                    node.args[key] = value

        if node.namespace:
            self.stack.append(node.namespace)
        # Iterate over a copy of children since we manipulate the list

        map(self.visit, node.children[:])
        if node.namespace:
            self.stack.pop()

        node.parent.add_children(node.children)
        node.delete()

class AppInfo(object):
    """docstring for AppInfo"""
    def __init__(self, script_name):
        super(AppInfo, self).__init__()
        self.actorstore = ActorStore()
        self.app_info = {
            'name':script_name,
            'actors': {},
            'connections': {},
            'valid': True
        }

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.Assignment)
    def visit(self, node):
        namespace = self.app_info['name']
        key = "{}:{}".format(namespace, node.ident)
        value = {}
        found, is_actor, actor_class = self.actorstore.lookup(node.actor_type)
        value['actor_type'] = node.actor_type
        args = {}
        for arg_node in node.children:
            if type(arg_node) is ast.NamedArg:
                arg_id, arg_val = arg_node.children
                args[arg_id.ident] = arg_val.value
        value['args'] = args
        value['signature'] = _create_signature(actor_class, node.actor_type)
        self.app_info['actors'][key] = value

    @visitor.when(ast.Link)
    def visit(self, node):
        namespace = self.app_info['name']
        key = "{}:{}.{}".format(namespace, node.outport.actor, node.outport.port)
        value = "{}:{}.{}".format(namespace, node.inport.actor, node.inport.port)
        self.app_info['connections'].setdefault(key, []).append(value)


class CodeGen(object):
    """
    Generate code from a source file
    FIXME: Use a writer class to generate output in various formats
    """
    def __init__(self, ast_root, script_name):
        super(CodeGen, self).__init__()
        self.actorstore = ActorStore()
        self.root = ast_root
        self.script_name = script_name
        self.constants = {}
        self.local_components = {}
        # self.app_info = {'name':script_name}
        self.printer = astprint.BracePrinter()

        self.run()


    def run(self, verbose=True):
        ast.Node._verbose_desc = verbose

        ##
        # Check for errors
        #

        ##
        # Tree re-write
        #
        print
        # self.printer.process(self.root)
        ##
        # Expand components
        #

        components = self.query(self.root, kind=ast.Component, maxdepth=1)
        for c in components:
            self.local_components[c.name] = c

        expander = Expander(self.local_components)
        expander.visit(self.root)
        # All component definitions can now be removed
        comps = self.query(self.root, kind=ast.Component)
        for comp in comps:
            comp.delete()

        ##
        # Implicit port rewrite
        rw = ImplicitPortRewrite()
        rw.visit(self.root)

        self.printer.process(self.root)

        ##
        # Flatten blocks
        flattener = Flatten()
        flattener.visit(self.root)

        ##
        # Resolve portmaps
        portmaps = self.query(self.root, kind=ast.Portmap)
        outportmaps = [(p.inport.actor, p.inport.port, p.outport) for p in portmaps if type(p.inport) is ast.InternalPort]
        inportmaps = [(p.outport.actor, p.outport.port, p.inport) for p in portmaps if type(p.outport) is ast.InternalPort]
        for portmap in portmaps:
            portmap.delete()

        for actor, port, replacement in outportmaps:
            ports = self.query(self.root, kind=ast.Port, attributes={'actor':actor, 'port':port})
            for replace in ports:
                link = replace.parent
                link.outport = replacement
        for actor, port, replacement in inportmaps:
            ports = self.query(self.root, kind=ast.Port, attributes={'actor':actor, 'port':port})
            for replace in ports:
                link = replace.parent
                link.inport = replacement

        self.printer.process(self.root)

        ##
        # "code" generation
        gen_app_info = AppInfo(self.script_name)
        gen_app_info.visit(self.root)
        self.app_info = gen_app_info.app_info

    def query(self, root, kind=None, attributes=None, maxdepth=1024):
        finder = Finder()
        finder.find_all(root, kind, attributes=attributes, maxdepth=maxdepth)
        return finder.matches


if __name__ == '__main__':
    from parser_regression_tests import run_check
    run_check(tests=['nested_components_with_args'], print_diff=True, print_script=True)


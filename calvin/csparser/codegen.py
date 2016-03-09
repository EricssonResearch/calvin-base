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
    def __init__(self, kind, maxdepth):
        self.depth = 0
        self.kind = kind
        self.maxdepth = maxdepth
        self.matches = []

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not self.kind or type(node) is self.kind:
            self.matches.append(node)
        if self.depth < self.maxdepth:
            self.depth += 1
            map(self.visit, node.children)
            self.depth -= 1

class Visitor(object):
    def __init__(self, maxdepth=1024):
        self.maxdepth = maxdepth
        self.depth = 0

    def _visit(self, node, preorder=None, inorder=None, postorder=None):
        if self.depth > self.maxdepth:
            print "maxdepth ({}) exceeded".format(self.depth)
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
    def __init__(self, maxdepth):
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
        args = [ ast.NamedArg('data', node.children[0]) ]
        self.counter += 1
        const_name = '_literal_const_'+str(self.counter)
        self.real_constants.append(ast.Assignment(const_name, 'std.Constant', args))
        self.real_port = ast.Port(const_name, 'token')


class CodeGen(object):
    """docstring for CodeGen"""
    def __init__(self, ast_root, script_name):
        super(CodeGen, self).__init__()
        self.actorstore = ActorStore()
        self.ast = ast_root
        self.script_name = script_name
        self.constants = {}
        self.app_info = {'name':script_name}

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
        # if actor_type in self.local_components:
        #     compdef = self.local_components[actor_type]
        #     return compdef, False

        found, is_actor, info = self.actorstore.lookup(actor_type)
        # if self.verify and not found:
        #     msg = 'Actor "{}" not found.'.format(actor_type)
        #     raise Exception(msg)
        return info, is_actor and found


    def run(self):
        # Add sections
        ai = self.app_info
        ai['actors'] = {}
        ai['connections'] = {}
        ai['valid'] = True

        c = self.query(ast.Constant, self.ast, maxdepth=1)
        self.process_constants(c)

        blocks = self.query(ast.Block, self.ast)
        for b in blocks:
            iprw = ImplicitPortRewrite(maxdepth=1024)
            iprw.visit(b)


        m = self.query(ast.Block, self.ast, maxdepth=1)
        if len(m) == 1:
            self.process_main(m[0])

    def add_actor(self, actor, namespace):
        key = "{}:{}".format(namespace, actor.ident)
        value = {}
        actor_class, is_actor = self.lookup(actor.actor_type)
        value['actor_type'] = actor.actor_type
        value['args'] = {} # FIXME: process args
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
        finder = Finder(kind, maxdepth=maxdepth)
        finder.visit(root)
        return finder.matches


if __name__ == '__main__':
    from parser_regression_tests import run_check
    run_check()


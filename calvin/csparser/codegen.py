import astnode as ast
import visitor
import astprint

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


class CodeGen(object):
    """docstring for CodeGen"""
    def __init__(self, ast_root, script_name):
        super(CodeGen, self).__init__()
        self.ast = ast_root
        self.script_name = script_name
        self.constants = {}
        self.app_info = {'name':script_name}

        self.run()

    def run(self):
        # Add sections
        ai = self.app_info
        ai['actors'] = {}
        ai['connections'] = {}
        ai['valid'] = True

        c = self.query(ast.Constant, self.ast, maxdepth=1)
        self.process_constants(c)

        m = self.query(ast.Block, self.ast, maxdepth=1)
        if len(m) == 1:
            self.process_main(m[0])

    def add_actor(self, actor, namespace):
        key = "{}:{}".format(namespace, actor.ident)
        value = {}
        value['actor_type'] = actor.actor_type
        value['args'] = {} # FIXME: process args
        self.app_info['actors'][key] = value

    def add_link(self, link, namespace):
        print link.outport.actor, link.inport.port
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


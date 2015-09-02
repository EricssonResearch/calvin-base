import visitor
import astnode as ast

class BracePrinter(object):

    def _visit(self, node, preorder=None, inorder=None, postorder=None):
        if preorder: preorder(node)
        left, last = node.children[0:-1], node.children[-1:]
        if not left:
            if last: self.visit(last[0])
            if inorder: inorder(node)
        else:
            for child in left:
                self.visit(child)
                if inorder: inorder(node)
            self.visit(last[0])
        if postorder: postorder(node)

    @staticmethod
    def _printval(n):
        print "n.type",

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.ASTNode)
    def visit(self, node):
        def f(n): print "( AST",
        def g(n): print ")",
        self._visit(node, preorder=f, postorder=g)

    @visitor.when(ast.ConstNode)
    def visit(self, node):
        def f(n): print "( CONST",
        def g(n): print ")",
        self._visit(node, preorder=f, postorder=g)

    @visitor.when(ast.IdNode)
    def visit(self, node):
        print node.ident,

    @visitor.when(ast.ValueNode)
    def visit(self, node):
        print node.value,

    @visitor.when(ast.AssignmentNode)
    def visit(self, node):
        def f(n): print "( ASSIGNMENT", node.ident, node.actor_type,
        def g(n): print ")",
        self._visit(node, preorder=f, postorder=g)

    @visitor.when(ast.NamedArgNode)
    def visit(self, node):
        def f(n): print "( NAMED_ARG",
        def g(n): print ")",
        self._visit(node, preorder=f, postorder=g)

    @visitor.when(ast.LinkNode)
    def visit(self, node):
        def f(n): print "( LINK",
        def g(n): print ")",
        self._visit(node, preorder=f, postorder=g)

    @visitor.when(ast.PortNode)
    def visit(self, node):
        print "( PORT {}.{} )".format(node.actor, node.port),

    @visitor.when(ast.InternalPortNode)
    def visit(self, node):
        print "( INTERNAL_PORT .{} )".format(node.port),

    @visitor.when(ast.ImplicitPortNode)
    def visit(self, node):
        def f(n): print "( IMPLICIT_PORT",
        def g(n): print ")",
        self._visit(node, preorder=f, postorder=g)

    @visitor.when(ast.ComponentNode)
    def visit(self, node):
        print "( COMPONENT {} )".format(node.name),

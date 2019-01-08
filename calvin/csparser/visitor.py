# For debugging
from astnode import Node

class Visitor(object):

    def visit(self, node):
        if not issubclass(type(node), Node):
            print "Skipping {}, {}".format(type(node), node)
            return  
        methname = 'visit_' + type(node).__name__ 
        meth = getattr(self, methname, self.generic_visit)
        return meth(node)

    def _visit_children(self, children):
        children = children or []
        for child in children:
            self.visit(child)    
    
    def generic_visit(self, node):
        self._visit_children(node.children)

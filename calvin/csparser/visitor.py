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
        for child in children:
            self.visit(child)    
    
    def generic_visit(self, node):
        # Sometimes a shallow copy of the children list is necessary, 
        # and it is always OK and simplifies usage
        self._visit_children(node.children[:])


class Finder(Visitor):
    """
    Perform queries on AST
    """

    def generic_visit(self, node):
        if self.query(node):
            self.matches.append(node)
        descend = node.children and self.depth < self.maxdepth
        if descend:
            self.depth += 1
            self._visit_children(node.children)
            self.depth -= 1

    def search(self, root, query, maxdepth):
        """
        Return a list of all nodes matching <kind>, at most <maxdepth> levels
        down from the starting node <node>
        If root evaluates to False or is not a subclass of ast.Node, return None

        """
        self.depth = 0
        self.maxdepth = maxdepth
        self.query = query
        self.matches = []
        self.visit(root)
        return self.matches
        

def search_tree(root, query, maxdepth):
    f = Finder()
    return f.search(root, query, maxdepth)        

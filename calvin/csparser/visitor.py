# FIXME: For debugging NoneType object in tree, remove when fixed
from astnode import Node

class Visitor(object):

    def visit(self, node):
        """
        Visit each node in tree depth first, starting in <node>
        
        Assumes <node> to have property children, a list of nodes.  
        """
        # FIXME: For debugging NoneType object in tree, remove when fixed
        if not issubclass(type(node), Node):
            print "Skipping {}, {}".format(type(node), node)
            return  
        methname = 'visit_' + type(node).__name__ 
        meth = getattr(self, methname, self.generic_visit)
        return meth(node)

    def _visit_children(self, children):
        """For use when overriding generic_visit in subclass"""
        for child in children:
            self.visit(child)    
    
    def generic_visit(self, node):
        """Default behaviour is to descend into children of <node>. Override in subclass to alter behaviour"""
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
        depth_limit = self.maxdepth >= 0 and self.depth >= self.maxdepth
        descend = node.children and not depth_limit
        if descend:
            self.depth += 1
            self._visit_children(node.children)
            self.depth -= 1

    def search(self, root, query, maxdepth):
        """
        Return a list of all nodes matching <query>, at most <maxdepth> levels
        down from the starting node <root>
        
        <query> is a predicate method that will get passed the current node as argument
        """
        self.depth = 0
        self.maxdepth = maxdepth
        self.query = query
        self.matches = []
        self.visit(root)
        return self.matches
        

def search_tree(root, query, maxdepth=-1):
    """
    Return a list of all nodes matching <query>, at most <maxdepth> levels
    down from the starting node <root>
    If <maxdepth> is < 0 (default) search depth is not limited
    <query> is a predicate method that will get passed the current node as argument
    """
    f = Finder()
    return f.search(root, query, maxdepth)
    
    
if __name__ == '__main__':
    a = Node()
    a.foo = "a"
    b = Node()
    b.foo = "b"
    c = Node()
    c.foo = "c"
    
    a.add_child(b)
    b.add_child(c)
    
    print len(search_tree(a, lambda node: node.foo == "c", 2))
    print len(search_tree(a, lambda node: node.foo == "c", 1))
    print len(search_tree(a, lambda node: node.foo == "c", 0))
    print
    print len(search_tree(a, lambda node: node.foo == "b", 2))
    print len(search_tree(a, lambda node: node.foo == "b", 1))
    print len(search_tree(a, lambda node: node.foo == "b", 0))
    print 
    print len(search_tree(a, lambda node: node.foo == "a", 2))
    print len(search_tree(a, lambda node: node.foo == "a", 1))
    print len(search_tree(a, lambda node: node.foo == "a", 0))
    print 
    print len(search_tree(a, lambda node: True, 2))
    print len(search_tree(a, lambda node: True, 1))
    print len(search_tree(a, lambda node: True, 0))
    print 
    print len(search_tree(a, lambda node: node.foo == "b" or node.foo == "c", 2))
    print len(search_tree(a, lambda node: node.foo == "b" or node.foo == "c", 1))
    print len(search_tree(a, lambda node: node.foo == "b" or node.foo == "c", 0))
    print
    print len(search_tree(a, lambda node: node.foo == "b" or node.foo == "c", -1))
    
    
    
    

    
    
    
    
    
                

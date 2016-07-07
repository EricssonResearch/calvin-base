import visitor
import astnode as ast
from codegen import calvin_astgen, query
from parser import calvin_parse
from calvin.actorstore.store import DocumentationStore

_docstore = DocumentationStore()

def _refname(name):
   return name.replace(':', '_')

def _lookup_definition(actor_type, root):
    if '.' in actor_type:
        doc = _docstore.help_raw(actor_type)
        if not doc['name']:
            return ([], [], '')
        t = doc['type']

        inports = [p for p,_ in doc['inputs']]
        outports = [p for p,_ in doc['outputs']]
    else:
        t = 'component'
        comps = query(root, kind=ast.Component, attributes={'name':actor_type}, maxdepth=2)
        if not comps:
            return ([], [], '')

        inports, outports = comps[0].inports, comps[0].outports

    return (inports, outports, t)

#
# Implement _vis_xxx for each node type with the following, and ...
#
def _viz_op(self):
    return "{}:{}_out:e".format(_refname(self.actor), self.port)

def _viz_ip(self):
    return "{}:{}_in:w".format(_refname(self.actor), self.port)

def _viz_iop(self):
    return "{}_out:e".format(self.port)

def _viz_iip(self):
    return "{}_in:w".format(self.port)

def _viz_implp(self):
    return "{}".format(self.arg)

def _viz_value(self):
    return "{}".format(self.value)

def _viz_id(self):
    return "{}".format(self.ident)

def _viz_actor(self):
    # ident, actor_type, args
    root = self
    while root.parent:
        root = root.parent
    _inports, _outports, _type = _lookup_definition(self.actor_type, root)
    inlen = len(_inports)
    outlen = len(_outports)
    portrows = max(inlen, outlen)
    inports = _inports + ['']*(portrows - inlen)
    outports = _outports + ['']*(portrows - outlen)
    hdrcolor = {
        'actor': 'lightblue',
        'component': 'lightyellow'
    }.get(_type, 'tomato')

    lines = []
    lines.append('{} [label=<'.format(_refname(self.ident)))
    lines.append('<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">')
    # Name
    lines.append('<TR><TD bgcolor="{1}" COLSPAN="3">{0}</TD></TR>'.format(self.ident, hdrcolor))
    # Class
    lines.append('<TR><TD COLSPAN="3">{}</TD></TR>'.format(self.actor_type))
    is_first=True
    for inport, outport in zip(inports, outports):
        inref = ' bgcolor="lightgrey" PORT="{}_in"'.format(inport) if inport else ''
        outref = ' bgcolor="lightgrey" PORT="{}_out"'.format(outport) if outport else ''
        if is_first:
            is_first = False
            middle = '<TD ROWSPAN="{}">    </TD>'.format(portrows)
        else:
            middle = ''
        lines.append('<TR><TD{0} align="left">{1}</TD>{4}<TD{2} align="right">{3}</TD></TR>'.format(inref, inport, outref, outport, middle))
    lines.append('</TABLE>>];')

    return '\n'.join(lines)

#
# ... monkey patch __str__ of the various node types
#
ast.OutPort.__str__ = _viz_op
ast.InPort.__str__ = _viz_ip
ast.InternalOutPort.__str__ = _viz_iop
ast.InternalInPort.__str__ = _viz_iip
ast.ImplicitPort.__str__ = _viz_implp
ast.Value.__str__ = _viz_value
ast.Id.__str__ = _viz_id
ast.Assignment.__str__ = _viz_actor



class Visualize(object):
   """docstring for VizPrinter"""
   def __init__(self):
       super(Visualize, self).__init__()
       self.expand_components = False

   def add(self, stmt):
       self.statements.append(stmt)

   def init(self, root):
       self.root = root
       self.statements = []

   def process(self, node):
       try:
           self.init(node)
           self.add('digraph structs { node [shape=plaintext]; rankdir=LR;')
           # self.add('digraph structs { node [shape=plaintext];')
           self.visit(node)
           self.add('}')
           return "\n".join(self.statements)
       except:
           print self.statements

   @visitor.on('node')
   def visit(self, node):
       pass

   @visitor.when(ast.Node)
   def visit(self, node):
       if node.children:
           map(self.visit, node.children)

   # FIXME: Make subgraph
   @visitor.when(ast.Component)
   def visit(self, node):
       if self.expand_components:
           self.add('subgraph { label=%s;' % node.name)
           for p in node.inports:
               self.add('{0}_out [shape="cds" style="filled" fillcolor="lightgrey" label="{0}"]'.format(p))
           for p in node.outports:
               self.add('{0}_in [shape="cds" style="filled" fillcolor="lightgrey" label="{0}"]'.format(p))
           if node.children:
               # print node.children
               map(self.visit, node.children)
           self.add('}')

   @visitor.when(ast.Assignment)
   def visit(self, node):
       self.add(str(node))


   @visitor.when(ast.Link)
   def visit(self, node):
       res = "{} -> {};".format(node.outport, node.inport)
       self.add(res)


def visualize_script(source_text):
    """Process script and return graphviz (dot) source representing application."""
    # Here we need the unprocessed tree
    ir, issuetracker = calvin_parse(source_text)
    v = Visualize()
    dot_source = v.process(ir)
    return dot_source, issuetracker


def visualize_deployment(source_text):
    ast_root, issuetracker = calvin_astgen(source_text, 'visualizer')
    # Here we need the processed tree
    v = Visualize()
    dot_source = v.process(ast_root)
    return dot_source, issuetracker

def visualize_component(source_text, name):
    # STUB
    from calvin.utilities.issuetracker import IssueTracker
    it = IssueTracker()
    it.add_error('Visualizing components not yet implemented.')
    return "digraph structs {ERROR}", it


if __name__ == '__main__':
    source_text = """
    /* Actors */
    src : std.CountTimer()
    snk : io.Print()
    /* Connections */
    src.integer > snk.token
    """

    print visualize_script(source_text)

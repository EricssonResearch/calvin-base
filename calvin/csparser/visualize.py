import string
import random
import inspect
import visitor
import astnode as ast
from codegen import calvin_astgen, calvin_components, query, PortlistRewrite
from parser import calvin_parse
from calvin.actorstore.store import DocumentationStore

_docstore = DocumentationStore()

def _refname(name):
   return name.replace(':', '_')

def _lookup_definition(actor_type, root):
    if '.' in actor_type:
        doc = _docstore.metadata(actor_type)
        if not doc['is_known']:
            return ([], [], '')
        return (doc['inputs'], doc['outputs'], doc['type'])
    comps = query(root, kind=ast.Component, attributes={'name':actor_type}, maxdepth=2)
    if not comps:
        return ([], [], '')
    return (comps[0].inports, comps[0].outports, 'component')

class BaseRenderer(object):
    """docstring for BaseRenderer"""
    def __init__(self, debug=False):
        super(BaseRenderer, self).__init__()
        self.debug = debug

    def _default(self, node, order):
        if self.debug:
            print "Not handling: {} ({})".format(node.__class__.__name__, order)
        return ''

    def _add(self, stmt):
        if stmt:
            self.statements.append(stmt)

    def render(self, node, order='preorder'):
        handler = getattr(self, node.__class__.__name__, self._default)
        args, _, _, _ = inspect.getargspec(handler)
        if len(args) == 3:
            self._add(handler(node, order))
        elif order == 'preorder':
            self._add(handler(node))

    def begin(self):
        self.statements = []
        self._add(self.preamble())

    def end(self):
        self._add(self.postamble())

    def result(self):
        return ''.join(self.statements)

    def preamble(self):
        return ''

    def postamble(self):
        return ''

# FIXME: PortList with TransformedPort breaks graphviz
class DotRenderer(BaseRenderer):

    def __init__(self, show_args=False, debug=False):
        super(DotRenderer, self).__init__()
        self.debug = debug
        self.show_args = show_args

    def _random_id(self):
        return ''.join(random.choice(string.ascii_uppercase) for x in range(8))

    def _truncate_label(self, label, maxlen=16):
        if len(label) > maxlen:
            label = label[:maxlen/2-2] + " ... " + label[-maxlen/2-2:]
        return label

    def preamble(self):
        return 'digraph structs { node [shape=plaintext]; rankdir=LR splines=spline;\n'

    def postamble(self):
        return '}\n'

    def Constant(self, node, order):
        if order == 'preorder':
            return '/* define '
        if order == 'inorder':
            return ' = '
        if order == 'postorder':
            return ' */\n'

    def Assignment(self, node, order):
        # ident, actor_type, args
        root = node
        while root.parent:
            root = root.parent
        _inports, _outports, _type = _lookup_definition(node.actor_type, root)
        inlen = len(_inports)
        outlen = len(_outports)
        portrows = max(inlen, outlen)
        inports = _inports + ['']*(portrows - inlen)
        outports = _outports + ['']*(portrows - outlen)
        hdrcolor = {
            'actor': 'lightblue',
            'component': 'lightyellow'
        }.get(_type, 'tomato')
        show_args = self.show_args and node.children

        if order == 'preorder':
            lines = []
            lines.append('{} [label=<'.format(_refname(node.ident)))
            lines.append('<TABLE bgcolor="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">')
            # Name
            lines.append('<TR><TD bgcolor="{1}" COLSPAN="3">{0}</TD></TR>'.format(node.ident, hdrcolor))
            # Class
            lines.append('<TR><TD COLSPAN="3">{}</TD></TR>'.format(node.actor_type))
            # Skipping arguments arriving inorder by commenting them out for now
            lines.append('<TR><TD COLSPAN="3" bgcolor="palegreen" ALIGN="left">' if show_args else '/* ')
            return '\n'.join(lines)

        if order == 'inorder':
            return '</TD></TR>\n<TR><TD COLSPAN="3" bgcolor="palegreen" ALIGN="left">' if show_args else ', '

        if order == 'postorder':
            # Close comment
            lines = ['</TD></TR>'if show_args else ' */']
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
            lines.append('</TABLE>>];\n')

            return '\n'.join(lines)

    def OutPort(self, node):
        return "{}:{}_out:e".format(_refname(node.actor), node.port)

    def InPort(self, node):
        return "{}:{}_in:w".format(_refname(node.actor), node.port)

    def InternalOutPort(self, node):
        return "{}_out:e".format(node.port)

    def InternalInPort(self, node):
        return "{}_in:w".format(node.port)

    def ImplicitPort(self, node, order):
        if order == 'preorder':
            return '{{{} [shape="box" style="filled" fillcolor="white" label="'.format(self._random_id())
        if order == 'postorder':
            return '" ]}'

    def TransformedPort(self, node):
        # N.B. port and value are properties of node, not children
        self.render(node.port)
        return ' [label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0"><TR><TD>/{}/</TD></TR></TABLE>>]'.format(self.Value(node.value))

    def Void(self, node):
        return '{{{} [shape="point" width=0.15]}}'.format(self._random_id())

    def Value(self, node):
        fmt = "'{}'" if type(node.value) is str else '{}'
        return self._truncate_label(fmt.format(node.value))

    def NamedArg(self, node, order):
        if order == 'inorder':
            return " = "

    def Id(self, node):
        return "{}".format(node.ident)

    def Link(self, node, order):
        if order == 'inorder' : return ' -> '
        if order == 'postorder' : return ';\n'

    def Component(self, node, order):
        if order == 'preorder':
            lines = ['subgraph cluster_{0}{{ style="filled"; color="lightyellow"; label="Component: {0}";'.format(node.name)]
            for p in node.inports:
                lines.append('{{/* rank="source" */ {0}_out [shape="cds" style="filled" fillcolor="lightgrey" label="{0}"]}};'.format(p))
            for p in node.outports:
                lines.append('{{/* rank="sink" */ {0}_in [shape="cds" style="filled" fillcolor="lightgrey" label="{0}"]}};'.format(p))
            return '\n'.join(lines)

        if order == 'postorder':
            return '}\n'


class Visualize(object):
   """docstring for VizPrinter"""
   def __init__(self, renderer=None):
       super(Visualize, self).__init__()
       self.renderer = renderer or DotRenderer()

   def process(self, root):
       self.renderer.begin()
       self.visit(root)
       self.renderer.end()
       return self.renderer.result()

   @visitor.on('node')
   def visit(self, node):
       pass

   @visitor.when(ast.Node)
   def visit(self, node):
       self.renderer.render(node, order='preorder')
       if not node.children:
           self.renderer.render(node, order='postorder')
       for n in node.children or []:
           self.visit(n)
           self.renderer.render(node, order='postorder' if n is node.children[-1] else 'inorder')


def visualize_script(source_text, show_args=False):
    """Process script and return graphviz (dot) source representing application."""
    # Here we need the unprocessed tree ...
    ir, issuetracker = calvin_parse(source_text)
    # ... but expand portlists to simplify rendering
    rw = PortlistRewrite(issuetracker)
    rw.visit(ir)
    r = DotRenderer(show_args, debug=False)
    v = Visualize(renderer = r)
    dot_source = v.process(ir)
    return dot_source, issuetracker

def visualize_deployment(source_text, show_args=False):
    ast_root, issuetracker = calvin_astgen(source_text, 'visualizer')
    # Here we need the processed tree
    r = DotRenderer(show_args, debug=False)
    v = Visualize(renderer = r)
    dot_source = v.process(ast_root)
    return dot_source, issuetracker

def visualize_component(source_text, name, show_args=False):
    # STUB
    ir_list, issuetracker = calvin_components(source_text, names=[name])
    r = DotRenderer(show_args, debug=False)
    v = Visualize(renderer = r)
    dot_source = v.process(ir_list[0])
    return dot_source, issuetracker


if __name__ == '__main__':
    source_text = """
    component FilterUnchanged() string -> string {
      iip : std.Init(data="nothing")
      cmp : std.Compare(op="=")
      sel : std.Select()

      .string > cmp.a
      iip.out > cmp.b
      cmp.result > sel.select
      .string > sel.data
      sel.case_true > voidport
      sel.case_false > iip.in
      sel.case_false > .string
    }

    /* Actors */
    src : std.CountTimer()
    snk : io.Print()
    /* Connections */
    src.integer > snk.token
    """

    dot_src, it =  visualize_script(source_text)
    print dot_src


    dot_src, it =  visualize_deployment(source_text)
    print dot_src

    dot_src, it =  visualize_component(source_text, "FilterUnchanged")
    print dot_src


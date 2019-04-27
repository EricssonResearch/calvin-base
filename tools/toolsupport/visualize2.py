import random
import string

import pystache

from calvinservices.csparser import astnode as ast
from calvinservices.csparser import visitor

    
class Renderer(visitor.Visitor):
    """docstring for Renderer"""
    def __init__(self, store):
        super(Renderer, self).__init__()
        self.store = store
    
    def render(self, root):
        raise Exception("Implement in subclass")
    
    def emit(self, text):
        self.segments.append(text)
        
    def _reset(self):
        self.segments = []
        self._namespace_stack = []
        
    def push_namespace(self, ns):
        self._namespace_stack.append(ns)

    def pop_namespace(self):
        if self._namespace_stack:
            self._namespace_stack.pop()

    @property
    def namespace(self):
        return self._namespace_stack[-1] if self._namespace_stack else ''
        
    def _random_id(self):
        return ''.join(random.choice(string.ascii_uppercase) for x in list(range(8)))

    def _truncate_label(self, label, maxlen=16):
        if len(label) > maxlen:
            label = label[:maxlen/2-2] + " ... " + label[-maxlen/2-2:]
        return label        


class DotRenderer(Renderer):
    """docstring for DotRenderer"""
    
    PREAMBLE = """digraph structs { node [shape=plaintext]; rankdir=LR splines=spline;"""
    POSTAMBLE = """}"""

    COMP_PREAMBLE = """
    subgraph cluster_{{name}} { 
        style="filled"; color="lightyellow"; label="Component: {{name}}";
        {{#inports}}
        { {{name}}_{{.}}_out [shape="cds" style="filled" fillcolor="lightgrey" label="{{.}}"] }
        {{/inports}}    
        {{#outports}}
        { {{name}}_{{.}}_in [shape="cds" style="filled" fillcolor="lightgrey" label="{{.}}"] }
        {{/outports}}    
    """
    COMP_POSTAMBLE = """}"""

    ASSIGNMENT = """
    {{#ns}}{{ns}}_{{/ns}}{{name}} [label=<
        <TABLE bgcolor="white" BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">
        <TR><TD bgcolor="{{header_color}}" COLSPAN="3">{{name}}</TD></TR>
        <TR><TD COLSPAN="3">{{actor_type}}</TD></TR>
        {{#ports}}
        <TR>
            <TD{{#inport}} bgcolor="lightgrey" PORT="{{inport}}_in"{{/inport}} align="left">{{inport}}</TD>
            {{#padding}}<TD ROWSPAN="{{padding}}">    </TD>{{/padding}}
            <TD{{#outport}} bgcolor="lightgrey" PORT="{{outport}}_out"{{/outport}} align="right">{{outport}}</TD>
        </TR>
        {{/ports}}
        </TABLE>
    >];
    """

    OUTPORT = """{{#ns}}{{ns}}_{{/ns}}{{actor}}:{{port}}_out:e"""
    INPORT = """{{#ns}}{{ns}}_{{/ns}}{{actor}}:{{port}}_in:w"""
    
    INT_INPORT = "{{ns}}_{{port}}_in:w"
    INT_OUTPORT = "{{ns}}_{{port}}_out:e"
    
    LINK = " -> "
    
    VOID = """
    { 
        {{random_id}} [shape="point" width=0.15]
    }
    """
            
    def render(self, root):
        self._reset()
        self.root = root
        self.emit(self.PREAMBLE)
        self.visit(self.root)
        self.emit(self.POSTAMBLE)
        return "\n".join(self.segments)
        

    def visit_Assignment(self, node):
        # Stop descent here, and gather required information
        metadata = self.store.get_metadata(node.actor_type)
        inports = [p['name'] for p in metadata['ports'] if p['direction'] == 'in']
        outports = [p['name'] for p in metadata['ports'] if p['direction'] == 'out']
        rows = max(len(inports), len(outports))
        padding = [rows] + ['']*(rows - 1) 
        inports += ['']*(rows - len(inports))
        outports += ['']*(rows - len(outports))
        keys = ['inport', 'padding', 'outport']
        port_list = [dict(zip(keys, x)) for x in zip(inports, padding, outports)]
        hdrcolor = {
            'actor': 'lightblue',
            'component': 'lightyellow'
        }.get(metadata['type'], 'tomato')
        data = {
            "ns": self.namespace,
            "name": node.ident,
            "actor_type": node.actor_type,
            "ports": port_list,
            "header_color": hdrcolor
        }
        self.emit(pystache.render(self.ASSIGNMENT, data))
        
    def visit_Link(self, node):
        # src:integer_out:e -> snk:token_in:w;
        self.visit(node.outport)
        self.emit(self.LINK)
        self.visit(node.inport)
        
    def _port_data(self, node):
        data = {
            'actor': node.actor,
            'port': node.port,
            'ns': self.namespace,
        }
        return data
        
    def visit_InPort(self, node):
        data = self._port_data(node)
        self.emit(pystache.render(self.INPORT, data))

    def visit_OutPort(self, node):
        data = self._port_data(node)
        self.emit(pystache.render(self.OUTPORT, data))

    def visit_InternalInPort(self, node):
        self.emit(pystache.render(self.INT_INPORT, ns=self.namespace, port=node.port))

    def visit_InternalOutPort(self, node):
        self.emit(pystache.render(self.INT_OUTPORT, ns=self.namespace, port=node.port))
        
    def visit_Component(self, node):
        self.push_namespace(node.name)
        # Data is neatly contained in node, so use it
        self.emit(pystache.render(self.COMP_PREAMBLE, node))
        super().generic_visit(node)
        self.emit(self.COMP_POSTAMBLE)
        self.pop_namespace()       

    def visit_Void(self, node):
        self.emit(pystache.render(self.VOID, random_id=self._random_id()))
        
    def generic_visit(self, node):
        self.emit("/* {} */".format(node.__class__.__name__))
        super().generic_visit(node)
        

import astnode as ast
import visitor
import astprint
import numbers
from parser import calvin_parse
from calvin.actorstore.store import DocumentationStore, GlobalStore
from calvin.requests import calvinresponse
from calvin.csparser.port_property_syntax import port_property_data

def _create_signature(actor_type, metadata):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    signature_desc = {'is_primitive': True,
                      'actor_type': actor_type,
                      'inports': metadata['inputs'],
                      'outports': metadata['outputs']}
    return GlobalStore.actor_signature(signature_desc)

def _is_local_component(actor_type):
    return '.' not in actor_type

def _root(node):
    root = node
    while root.parent:
        root = root.parent
    return root

def _construct_metadata(node):
    # FIXME: Actually construct metadata
    return {
        'is_known': False,
        'inputs': [],
        'outputs': [],
        'args':{
            'mandatory':[],
            'optional':{}
        }
    }

def _lookup(node, issue_tracker):
    if _is_local_component(node.actor_type):
        comps = query(_root(node), kind=ast.Component, attributes={'name':node.actor_type})
        if not comps:
            reason = "Missing local component definition: '{}'".format(node.actor_type)
            issue_tracker.add_error(reason, node)
            return {'is_known': False}
        comp = comps[0]
        metadata = {
            'is_known': True,
            'name': comp.name,
            'type': 'component',
            'inputs': comp.inports,
            'outputs': comp.outports,
            'args':{
                'mandatory':comp.arg_names,
                'optional':{}
            },
            'definition': comp.children[0]
        }
    else:
        metadata = DocumentationStore().metadata(node.actor_type)
        if not metadata['is_known']:
            reason = "Not validating actor type: '{}'".format(node.actor_type)
            issue_tracker.add_warning(reason, node)

    return metadata


def _check_arguments(assignment, issue_tracker):
    """
    Verify that all arguments are present and valid when instantiating actors.
    """
    metadata = assignment.metadata
    mandatory = set(metadata['args']['mandatory'])
    optional = set(metadata['args']['optional'].keys())

    given_args = assignment.children
    given_idents = {a.ident.ident: a.ident for a in given_args}
    given_keys = given_idents.keys()
    given = set(given_keys)

    # Case 0: Duplicated arguments
    duplicates = set([x for x in given_keys if given_keys.count(x) > 1])
    for m in duplicates:
        reason = "Duplicated argument: '{}'".format(m)
        issue_tracker.add_error(reason, given_idents[m])

    # Case 1: Missing arguments
    missing = mandatory - given
    for m in missing:
        reason = "Missing argument: '{}'".format(m)
        issue_tracker.add_error(reason, assignment)

    # Case 2: Extra (unused) arguments
    # FIXME: Rename error to Excess argument
    unused = given - (mandatory | optional)
    for m in unused:
        reason = "Excess argument: '{}'".format(m)
        issue_tracker.add_error(reason, given_idents[m])

    # Case 3: Deprecation warning if optional args not explicitly given
    deprecated = optional - given
    for m in deprecated:
        reason = "Using default value for implicit parameter '{}'".format(m)
        issue_tracker.add_warning(reason, assignment)


def _arguments(assignment, issue_tracker):
    # Assign and return args dictionary
    given_args = assignment.children
    args = {}
    for arg_node in given_args:
        if type(arg_node.arg) is ast.Value:
            args[arg_node.ident.ident] = arg_node.arg.value
        else:
            reason = "Undefined identifier: '{}'".format(arg_node.arg.ident)
            issue_tracker.add_error(reason, arg_node.arg)
    return args


class Finder(object):
    """
    Perform queries on the tree
    """
    def __init__(self):
        super(Finder, self).__init__()

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

class PortlistRewrite(object):
    """docstring for PortlistRewrite"""
    def __init__(self, issue_tracker):
        super(PortlistRewrite, self).__init__()
        self.issue_tracker = issue_tracker

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])

    @visitor.when(ast.PortList)
    def visit(self, node):
        link = node.parent
        block = link.parent
        for inport in node.children:
            new_link = ast.Link(outport=link.outport.clone(), inport=inport)
            block.add_child(new_link)
        link.delete()


class PortRewrite(object):
    """Baseclass for port rewrite operations"""
    def __init__(self, issue_tracker):
        super(PortRewrite, self).__init__()
        self.issue_tracker = issue_tracker
        self.counter = 0

    def _make_unique(self, name):
        self.counter += 1
        return "_{}_{}".format(name, str(self.counter))


    def _add_src_or_snk_and_relink(self, node, actor, port):
        link = node.parent
        link.replace_child(node, port)
        block = link.parent
        block.add_child(actor)

    def _add_src_and_relink(self, node, actor, port):
        self._add_src_or_snk_and_relink(node, actor, port)

    def _add_snk_and_relink(self, node, actor, port):
        self._add_src_or_snk_and_relink(node, actor, port)

    def _add_filter_and_relink(self, node, actor, inport, outport):
        link = node.parent
        block = link.parent
        block.add_child(actor)
        new_link = ast.Link(outport=outport, inport=node.port)
        block.add_child(new_link)
        link.inport = inport



class ImplicitOutPortRewrite(PortRewrite):
    """
    ImplicitPortRewrite takes care of the construct
        <value> > foo.in
    by replacing <value> with a std.Constant(data=<value>) actor.

    Running this cannot not fail and thus cannot cause an issue.
    """
    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])

    @visitor.when(ast.ImplicitPort)
    def visit(self, node):
        args = [ ast.NamedArg(ident=ast.Id(ident='data'), arg=node.arg) ]
        if node.label:
            const_name = node.label.ident
        else:
            # Create a unique name if not given by label
            const_name = self._make_unique('literal_const')

        const_actor = ast.Assignment(ident=const_name, actor_type='std.Constant', args=args)
        const_actor.debug_info = node.arg.debug_info
        const_actor_port = ast.OutPort(actor=const_name, port='token')
        self._add_src_and_relink(node, const_actor, const_actor_port)


class ImplicitInPortRewrite(PortRewrite):
    """
    """

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])

    @visitor.when(ast.TransformedPort)
    def visit(self, node):
        # std.Constantify(constant) ports: in/out
        args = [ast.NamedArg(ident=ast.Id(ident='constant'), arg=node.value)]
        if node.label:
            transform_name = node.label.ident
        else:
            # Create a unique name if not given by label
            transform_name = self._make_unique('transform')
        transform_actor = ast.Assignment(ident=transform_name, actor_type='std.Constantify', args=args)
        transform_actor.debug_info = node.value.debug_info
        transform_actor_outport = ast.OutPort(actor=transform_name, port='out')
        transform_actor_inport = ast.InPort(actor=transform_name, port='in')

        self._add_filter_and_relink(node, transform_actor, transform_actor_inport, transform_actor_outport)


class VoidPortRewrite(PortRewrite):
    """
    """

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])

    @visitor.when(ast.Void)
    def visit(self, node):
        link = node.parent
        if link.outport is node:
            actor_type = 'flow.Void'
            port_class = ast.OutPort
            reason = "Using 'void' as input to '{}.{}'".format(link.inport.actor, link.inport.port)
            self.issue_tracker.add_warning(reason, node)
        else:
            actor_type='flow.Terminator'
            port_class = ast.InPort

        actor_name = self._make_unique('void')
        void_actor = ast.Assignment(ident=actor_name, actor_type=actor_type)
        void_actor.debug_info = node.debug_info
        void_actor_port = port_class(actor=actor_name, port='void')

        self._add_src_or_snk_and_relink(node, void_actor, void_actor_port)


class RestoreParents(object):
    """docstring for RestoreParents"""
    def __init__(self):
        super(RestoreParents, self).__init__()
        self.stack = [None]

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        node.parent = self.stack[-1]
        if node.is_leaf():
            return
        self.stack.append(node)
        map(self.visit, node.children[:])
        self.stack.pop()

class CollectPortProperties(object):
    """
    Collect actor-declared port properties and PortProperty statements and make the port properties
    children of their respective ports.
    The rationale for this is that we don't need to handle namespace propagation etc. for the port properties
    since they will piggy-back on the port that the properties relate to.
    N.B. A consequence of this is that until the port properties have been coalesced (extracted
    from the port) after the tree is flattened the (name, port, direction) combo is not updated.
    """
    def __init__(self, issue_tracker):
        super(CollectPortProperties, self).__init__()
        self.issue_tracker = issue_tracker

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])

    @visitor.when(ast.PortProperty)
    def visit(self, node):
        # Collect explicit PortProperty statements and make them children of their respective ports
        block = node.parent
        ports = []
        if node.actor is None:
            # This works because any ambiguity in port names have been detected in check_consistency in a previous step
            if not node.direction or node.direction == "in":
                ports += query(block, kind=ast.InternalInPort, maxdepth=2, attributes={'port':node.port})
            if not node.direction or node.direction == "out":
                ports += query(block, kind=ast.InternalOutPort, maxdepth=2, attributes={'port':node.port})
        else:
            # This works because any ambiguity in port names have been detected in check_consistency in a previous step
            if not node.direction or node.direction == "in":
                ports += query(block, kind=ast.InPort, maxdepth=2, attributes={'actor':node.actor, 'port':node.port})
            if not node.direction or node.direction == "out":
                ports += query(block, kind=ast.OutPort, maxdepth=2, attributes={'actor':node.actor, 'port':node.port})
        self._transfer_property(node, ports)

    def _transfer_property(self, node, portlist):
            # If len(portlist) == 0 then there is no port with such a name => error should have been reported earlier
            # Since there is no port to attach the property to, drop the node and continue
            if not portlist:
                node.delete() # remove from tree
                return
            # If len(portlist) > 1 then there are multiple ports connected which is OK as long there is not a mix of inports and outports
            # which should have been detected earlier => error should have been reported earlier.
            # Since it is enough to attach the the property to one port instance, grab the first port instance.
            port = portlist[0]
            node.delete() # remove from tree
            port.add_child(node)

    @visitor.when(ast.Assignment)
    def visit(self, node):
        if not node.metadata['is_known']:
            return
        # Collect actor-declared port properties and make them children of their respective ports
        name = node.ident
        for port, pp in  node.metadata['input_properties'].items():
            query_res = query(node.parent, kind=ast.InPort, maxdepth=2, attributes={'actor':name, 'port':port})
            self._transfer_actor_properties(node, name, port, query_res, pp)
        for port, pp in  node.metadata['output_properties'].items():
            query_res = query(node.parent, kind=ast.OutPort, maxdepth=2, attributes={'actor':name, 'port':port})
            self._transfer_actor_properties(node, name, port, query_res, pp)

    def _transfer_actor_properties(self, node, actor, port, portlist, properties):
        if not portlist:
            # The portlist is empty => there is a bug in the script
            # Silently let this pass to be handled during consistency check
            return
        destination_port = portlist[0]
        direction = 'in' if type(destination_port) is ast.InPort else 'out'
        # Create a new port property object and stuff the actor properties into it
        # FIXME: Actor argument shouldn't matter, since it will be taken from the port after flattening the tree,
        #        but it setting it a generic string causes errors. Need to find out why.
        port_property = ast.PortProperty(actor=actor, port=port, direction=direction, debug_info=node.debug_info)
        for ident, value in properties.items():
            prop = ast.NamedArg(ident=ast.Id(ident=ident), arg=ast.Value(value=value))
            port_property.add_child(prop)
        destination_port.add_child(port_property)


class Expander(object):
    """
    Expands a tree with components provided as a subtree
    """
    def __init__(self, issue_tracker):
        self.issue_tracker = issue_tracker

    def process(self, root, verify=True):
        self.verify = verify
        self.visit(root)
        # Remove local componentes from AST
        for comp in query(root, kind=ast.Component, maxdepth=1):
            comp.delete()

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])


    @visitor.when(ast.Assignment)
    def visit(self, node):
        if not node.metadata:
            node.metadata = _lookup(node, self.issue_tracker)
        if node.metadata['is_known'] and node.metadata['type'] == 'actor':
            # Nothing more to do
            return
        if not node.metadata['is_known']:
            # Unknown actor => construct metadata from graph + args unless verify is True
            if self.verify:
                reason = "Unknown actor type: '{}'".format(node.actor_type)
                self.issue_tracker.add_error(reason, node)
            else:
                # Warning issued previously
                node.metadata = _construct_metadata(node)
            return
        #
        # We end up here if node is in fact a component
        #
        compdef = node.metadata['definition']
        v = RestoreParents()
        v.visit(compdef)
        # Clone block from component definition
        new = compdef.clone()
        new.namespace = node.ident
        # Add arguments from assignment to block
        args = node.children
        new.args = {x.ident.ident: x.arg for x in args}
        node.parent.replace_child(node, new)
        # Recurse
        self.visit(new)


class Flatten(object):
    """
    Flattens a block by wrapping everything in the block's namespace
    and propagating arguments before removing the block
    N.B. This visits blocks depth-first and must start in a block node
         or a node whose only child is a block.
    """
    def __init__(self, issue_tracker):
        self.stack = []
        self.issue_tracker = issue_tracker

    def process(self, root):
        self.visit(root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children[:])

    @visitor.when(ast.Block)
    def visit(self, node):
        # Recurse into blocks first, putting block's namespace on stack
        self.stack.append(node.namespace)
        blocks = [x for x in node.children if type(x) is ast.Block]
        map(self.visit, blocks)

        # Keep track of nodes to to delete
        self.consumed = set()

        # Promote ports and assignments, and create links across component borders
        # N.B. By this point all sub-blocks have been removed, thus non_blocks == node.children
        non_blocks = node.children[:]
        map(self.visit, non_blocks)

        # Clean up nodes no longer needed
        for n in self.consumed:
            n.delete()

        # Move remaining children to containing block
        node.parent.add_children(node.children)

        # Delete this block and pop the namespace stack
        node.delete()
        self.stack.pop()

    @visitor.when(ast.Link)
    def visit(self, node):
        # Make sure real ports have been promoted, i.e. have had the block namspace
        # added to the actor name, before juggling with component internal ports.
        linktype = (type(node.outport), type(node.inport))
        if linktype == (ast.InternalOutPort, ast.InPort):
            map(self.visit, [node.inport, node.outport])
        else:
            map(self.visit, [node.outport, node.inport])

    @visitor.when(ast.InternalOutPort)
    def visit(self, node):
        # Block expansion of link and properties over component inports
        # =============================================================
        #
        # We have the following situation: an actor outport is connected to an inport on a component "hull",
        # that is subsequently connected to an actor inport inside the component. There are four ports involved,
        # connecting port on the component hull counting as two (outside and inside). Each of the ports may have
        # port properties set on them, and the properties set on the ports on the hull need to be transferred to
        # the other ports since the hull is about to go away.
        #
        # The way to identify the connection to be made is by finding ast.InternalOutPort objects with the same
        # identifier (actor name + port name) as an ast.Inport object (L1 and L2 below).
        #
        # In order to preserve port propterties P1 and P2 from L1 and L2, respectively, they should be transferred
        # according to the scheme below.
        #
        #                                                 +---------------------------------+
        #                    L0      L1                   |                                 |
        # (ast.OutPort [P0]) x.out > comp.in (ast.InPort [P1])                              v
        #               ^            comp.in (ast.InternalOutPort [P2]) > y.in (ast.InPort [P3])
        #               |            L2                            |      L3
        #               +------------------------------------------+
        #
        # =>
        #
        # (ast.OutPort [P0, P2]) x.out > y.in (ast.InPort [P1, P3])
        #
        # (L0 [P0], L1 [P1]) + (L2 [P2], L3 [P3]) => (L0 [P0, P2], L3 [P1, P3])
        l2 = node
        block = node.parent.parent
        l1_list = query(block.parent, kind=ast.InPort, maxdepth=2, attributes={'actor':block.namespace, 'port':l2.port})
        for l1 in l1_list:
            new_link = self._relink(l1, l2)
            block.add_child(new_link)

    @visitor.when(ast.InternalInPort)
    def visit(self, node):
        # Block expansion of link and properties over component outports
        # ==============================================================
        #
        # This follows the same pattern as above, but the situation now looks like follows
        #
        #                                                          +-----------------+
        #                    L0      L1                            |                 |
        # (ast.OutPort [P0]) x.out > comp.out (ast.InternalInPort [P1])              v
        #               ^            comp.out (ast.OutPort [P2]) > y.in (ast.InPort [P3])
        #               |            L2                     |      L3
        #               +-----------------------------------+
        #
        # =>
        #
        # (ast.OutPort [P0, P2]) x.out > y.in (ast.InPort [P1, P3])
        #
        # (L0 [P0], L1 [P1]) + (L2 [P2], L3 [P3]) => (L0 [P0, P2], L3 [P1, P3])
        l1 = node
        block = node.parent.parent
        l2_list = query(block.parent, kind=ast.OutPort, maxdepth=2, attributes={'actor':block.namespace, 'port':l1.port})
        for l2 in l2_list:
            new_link = self._relink(l1, l2)
            block.add_child(new_link)

    def _relink(self, l1, l2):
        # Follow the relinking pattern described above
        l0_l1_link = l1.parent
        l0 = l0_l1_link.outport
        l2_l3_link = l2.parent
        l3 = l2_l3_link.inport
        # 5. Create the new link
        l0_copy = l0.clone()
        l3_copy = l3.clone()
        l0_l3_link = ast.Link(outport=l0_copy, inport=l3_copy)
        # 8. Transfer port properties
        l0_l3_link.outport.add_children(l2.children)
        l0_l3_link.inport.add_children(l1.children)
        # l0_l1_link and l2_l3_link may be referred to multiple times,
        # but can only be removed once, hence the use of a set here.
        self.consumed.add(l0_l1_link)
        self.consumed.add(l2_l3_link)
        return l0_l3_link

    @visitor.when(ast.Assignment)
    def visit(self, node):
        node.ident = self.stack[-1] + ':' + node.ident
        map(self.visit, node.children[:])

    @visitor.when(ast.NamedArg)
    def visit(self, node):
        if type(node.arg) is ast.Id:
            # Get value from grandparent (block)
            block = node.parent.parent
            key = node.arg.ident
            if key in block.args:
                value = block.args[key]
                node.replace_child(node.arg, value)

    @visitor.when(ast.InPort)
    def visit(self, node):
        self._promote_port(node)

    @visitor.when(ast.OutPort)
    def visit(self, node):
        self._promote_port(node)

    def _promote_port(self, node):
        if node.actor:
            node.actor = self.stack[-1] + ':' + node.actor
        else:
            node.actor = self.stack[-1]



class CoalesceProperties(object):
    """
    Add the nbr_peers property for all ports, generating a number of
    """
    def __init__(self, issue_tracker):
        super(CoalesceProperties, self).__init__()
        self.issue_tracker = issue_tracker

    def process(self, root):
        self.counter = {}
        self.port_properties = {}
        self.visit(root)
        props = []
        for key, pp in self.port_properties.iteritems():
            pp.add_child(ast.NamedArg(ident=ast.Id(ident="nbr_peers"), arg=ast.Value(value=self.counter[key])))
            props.append(pp)
        root.add_children(props)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children[:])

    @visitor.when(ast.Link)
    def visit(self, link):
        # Create port properties and compute number of connections for each port
        name = (link.inport.actor, link.inport.port, "in")
        self.port_properties.setdefault(name, ast.PortProperty(actor=link.inport.actor, port=link.inport.port, direction="in"))
        self.counter[name] = self.counter.get(name, 0) + 1

        name = (link.outport.actor, link.outport.port, "out")
        self.port_properties.setdefault(name, ast.PortProperty(actor=link.outport.actor, port=link.outport.port, direction="out"))
        self.counter[name] = self.counter.get(name, 0) + 1

        map(self.visit, link.children[:])

    @visitor.when(ast.InPort)
    def visit(self, node):
        self._coalsesce_properties_for_port(node, "in")

    @visitor.when(ast.OutPort)
    def visit(self, node):
        self._coalsesce_properties_for_port(node, "out")

    def _coalsesce_properties_for_port(self, node, direction):
        if not node.children:
            return
        name = (node.actor, node.port, direction)
        pp = self.port_properties[name]
        for npp in node.children[:]:
            pp.add_children(npp.children)
            node.remove_child(npp)


class MergePortProperties(object):
    """
    Merge port properties that have been set in various places

    FIXME: Order is important, IMHO an _intrinsic_ property, i.e. defined by actor
           should have preceedence over externally set properties, and likewise
           a property defined inside a component should have preceedence over
           externally set properties.
    FIXME: Assuming for now that order of PortProperty's children complies with the above
    """
    def __init__(self, issue_tracker):
        super(MergePortProperties, self).__init__()
        self.issue_tracker = issue_tracker

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children[:])

    @visitor.when(ast.PortProperty)
    def visit(self, node):
        props = {}
        for p in node.children[:]:
            props.setdefault(p.ident.ident, []).append(p)
        for p, mergelist in props.iteritems():
            if len(mergelist) < 2:
                # Uncontested
                continue
            # Detach properties from node
            node.remove_children(mergelist)
            # Merge list of properties targeting the same port
            merged = self.merge_properties(mergelist)
            # Add the resulting, single, merged property to node
            node.add_child(merged)

    def merge_properties(self, mergelist):

        def _merge_two(left, right):
            lval = left.arg.value
            rval = right.arg.value
            if lval == rval:
                # Identical properties
                return left
            lval_is_scalar = not isinstance(lval, (tuple, list))
            rval_is_scalar = not isinstance(rval, (tuple, list))
            if lval_is_scalar and rval_is_scalar:
                # Both are non-iterables => left is prioritized (see class docs)
                return left
            # Make sure lval and rval are both lists
            if lval_is_scalar:
                lval = [lval]
            if rval_is_scalar:
                rval = [rval]
            # Make ordered subset, possibly empty
            merged_val = [item for item in lval if item in rval]
            if not merged_val:
                # Generate errors for each port property targeting this port
                reason = "Can't handle conflicting properties without common alternatives"
                for node in mergelist:
                    self.issue_tracker.add_error(reason, node)
            left.arg.value = merged_val
            return left

        prioritized = mergelist[0]
        for merger in mergelist[1:]:
            prioritized = _merge_two(prioritized, merger)
        return prioritized

class CheckPortProperties(object):
    """
    Merge port properties that have been set in various places

    FIXME: Order is important, IMHO an _intrinsic_ property, i.e. defined by actor
           should have preceedence over externally set properties, and likewise
           a property defined inside a component should have preceedence over
           externally set properties.
    FIXME: Assuming for now that order of PortProperty's children complies with the above
    """
    def __init__(self, issue_tracker):
        super(CheckPortProperties, self).__init__()
        self.issue_tracker = issue_tracker

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children[:])

    @visitor.when(ast.PortProperty)
    def visit(self, node):
        for p in node.children[:]:
            self.check_property(p)

    def check_property(self, prop):
        p_name = prop.ident.ident
        p_value = prop.arg.value if isinstance(prop.arg.value, (list, tuple)) else [prop.arg.value]
        # print p_name, p_value
        # Check that the property type is allowed
        if p_name not in port_property_data:
            reason = "Port property {} is unknown".format(p_name)
            self.issue_tracker.add_error(reason, prop)
            return
        ppdata = port_property_data[p_name]
        for value in p_value:
            if ppdata['type'] == "category":
                if value not in ppdata['values']:
                    reason = "Port property {} can only have values {}".format(p_name, ", ".join(ppdata['values'].keys()))
                    self.issue_tracker.add_error(reason, prop)
                    continue
                if prop.parent.direction not in ppdata['values'][value]['direction']:
                    reason = "Port property {}={} is only for {} ports".format(p_name, value, ppdata['values'][value]['direction'])
                    self.issue_tracker.add_error(reason, prop)
                    continue
            if ppdata['type'] == 'scalar':
                if not isinstance(value, numbers.Number):
                    reason = "Port property {} can only have scalar values".format(p_name)
                    self.issue_tracker.add_error(reason, prop)
                    continue
            if ppdata['type'] == 'string':
                if not isinstance(value, basestring):
                    reason = "Port property {} can only have string values".format(p_name)
                    self.issue_tracker.add_error(reason, prop)
                    continue

            if p_name == 'nbr_peers' and value > 1 and prop.parent.direction == 'in':
                # Verify that inports with multiple connections have a routing property for multipeers
                res = query(prop.parent, kind=ast.Id, attributes={'ident': 'routing'})
                if not res:
                    reason = "Input port {}.{} with multiple connections must have a routing port property.".format(prop.parent.actor, prop.parent.port)
                    self.issue_tracker.add_error(reason, prop)
                    continue
                routings = res[0].parent.arg.value
                if not isinstance(routings, (list, tuple)):
                    routings = [routings]
                valid_routings = [routing for routing in routings if port_property_data['routing']['values'][routing].get('multipeer', False)]
                # FIXME: Issue warning if valid len(valid_routings) < len(routings)
                routings = valid_routings[0] if len(valid_routings) == 1 else valid_routings
                if not valid_routings:
                    reason = "Input port {}.{} with multiple connections must have a routing port property.".format(prop.parent.actor, prop.parent.port)
                    self.issue_tracker.add_error(reason, prop)
                    continue


class AppInfo(object):
    """docstring for AppInfo"""
    def __init__(self, app_info, root, issue_tracker):
        super(AppInfo, self).__init__()
        self.root = root
        self.app_info = app_info
        self.issue_tracker = issue_tracker

    def process(self):
        self.visit(self.root)


    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.Assignment)
    def visit(self, node):
        if not node.metadata['is_known']:
            # No metadata => we have already generated an error, just skip
            return

        value = {}
        value['actor_type'] = node.actor_type
        value['args'] = _arguments(node, self.issue_tracker)
        value['signature'] = _create_signature(node.actor_type, node.metadata)

        self.app_info['actors'][node.ident] = value

    @visitor.when(ast.Link)
    def visit(self, node):
        key = "{}.{}".format(node.outport.actor, node.outport.port)
        value = "{}.{}".format(node.inport.actor, node.inport.port)

        self.app_info['connections'].setdefault(key, []).append(value)


    @visitor.when(ast.PortProperty)
    def visit(self, node):
        value = {}
        value['port'] = node.port
        value['direction'] = node.direction
        value['properties'] = _arguments(node, self.issue_tracker)

        self.app_info['port_properties'].setdefault(node.actor, []).append(value)


class ReplaceConstants(object):
    """docstring for ReplaceConstants"""
    def __init__(self, issue_tracker):
        super(ReplaceConstants, self).__init__()
        self.issue_tracker = issue_tracker

    def process(self, root):
        constants = query(root, ast.Constant, maxdepth=2)
        defined = {c.ident.ident: c.arg for c in constants if type(c.arg) is ast.Value}
        unresolved = [c for c in constants if type(c.arg) is ast.Id]
        seen = [c.ident.ident for c in unresolved]
        while True:
            did_replace = False
            for c in unresolved[:]:
                key, const_key = c.ident, c.arg
                if const_key.ident in defined:
                    defined[key.ident] = defined[const_key.ident]
                    unresolved.remove(c)
                    seen.append(c.ident.ident)
                    did_replace = True
            if not did_replace:
                break
        for c in unresolved:
            key, const_key = c.ident, c.arg
            if const_key.ident in seen:
                reason = "Constant '{}' has a circular reference".format(key.ident)
            else:
                reason = "Constant '{}' is undefined".format(const_key.ident)
            self.issue_tracker.add_error(reason, const_key)
        self.definitions = defined
        self.visit(root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.NamedArg)
    def visit(self, node):
        if type(node.arg) is ast.Value:
            return
        if node.arg.ident in self.definitions:
            value = self.definitions[node.arg.ident]
            node.replace_child(node.arg, value)


class ConsistencyCheck(object):
    """docstring for RestoreParents

       Run before expansion.
    """
    def __init__(self, issue_tracker):
        super(ConsistencyCheck, self).__init__()
        self.issue_tracker = issue_tracker
        self.block = None
        self.component = None

    def process(self, root):
        self.visit(root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.Component)
    def visit(self, node):
        self.component = node

        for arg_name in node.arg_names:
            matches = query(node, kind=ast.NamedArg)
            referenced_values = [m.arg.ident for m in matches if type(m.arg) is ast.Id]
            if not arg_name in referenced_values:
                reason = "Unused argument: '{}'".format(arg_name)
                self.issue_tracker.add_error(reason, node)

        for port in node.outports:
            matches = query(node, kind=ast.InternalInPort, maxdepth=3, attributes={'port':port})
            if not matches:
                reason = "Component {} is missing connection to outport '{}'".format(node.name, port)
                self.issue_tracker.add_error(reason, node)
        for port in node.inports:
            matches = query(node, kind=ast.InternalOutPort, maxdepth=3, attributes={'port':port})
            if not matches:
                reason = "Component {} is missing connection to inport '{}'".format(node.name, port)
                self.issue_tracker.add_error(reason, node)
        map(self.visit, node.children)
        self.component = None

    @visitor.when(ast.Block)
    def visit(self, node):
        self.block = node
        assignments = [n for n in node.children if type(n) is ast.Assignment]

        # Check for multiple definitions
        assignments_ids = [a.ident for a in assignments]
        dups = [a for a in assignments_ids if assignments_ids.count(a) > 1]
        for dup in dups:
            dup_assignments = [a for a in assignments if a.ident is dup]
            reason = "Instance identifier '{}' redeclared".format(dup)
            # Relate error to last seen declaration
            self.issue_tracker.add_error(reason, dup_assignments[-1])

        map(self.visit, assignments)
        links = [n for n in node.children if type(n) is ast.Link]
        map(self.visit, links)
        port_props = [n for n in node.children if type(n) is ast.PortProperty]
        map(self.visit, port_props)


    @visitor.when(ast.Assignment)
    def visit(self, node):
        node.metadata = _lookup(node, self.issue_tracker)
        if not node.metadata['is_known']:
            # error issued in _lookup
            return

        _check_arguments(node, self.issue_tracker)

        for port in node.metadata['inputs']:
            matches = query(self.block, kind=ast.InPort, maxdepth=3, attributes={'actor':node.ident, 'port':port})
            matches = matches + query(self.block, kind=ast.InternalInPort, maxdepth=3, attributes={'actor':node.ident, 'port':port})
            if not matches:
                reason = "{} {} ({}.{}) is missing connection to inport '{}'".format(node.metadata['type'].capitalize(), node.ident, node.metadata.get('ns', 'local'), node.metadata['name'], port)
                self.issue_tracker.add_error(reason, node)

        for port in node.metadata['outputs']:
            matches = query(self.block, kind=ast.OutPort, maxdepth=3, attributes={'actor':node.ident, 'port':port})
            matches = matches + query(self.block, kind=ast.InternalOutPort, maxdepth=3, attributes={'actor':node.ident, 'port':port})
            if not matches:
                reason = "{} {} ({}.{}) is missing connection to outport '{}'".format(node.metadata['type'].capitalize(), node.ident, node.metadata.get('ns', 'local'), node.metadata['name'], port)
                self.issue_tracker.add_error(reason, node)


    def _check_port(self, node, direction, issue_tracker):
        matches = query(self.block, kind=ast.Assignment, attributes={'ident':node.actor})
        if not matches:
            reason = "Undefined actor: '{}'".format(node.actor)
            issue_tracker.add_error(reason, node)
            return
        if not matches[0].metadata['is_known']:
            # Already covered by assignment node
            return

        ports = matches[0].metadata[direction + 'puts']
        if node.port not in ports:
            metadata = matches[0].metadata
            reason = "{} {} ({}.{}) has no {}port '{}'".format(metadata['type'].capitalize(), node.actor, metadata.get('ns', 'local'), metadata['name'], direction, node.port)
            issue_tracker.add_error(reason, node)
            return

    @visitor.when(ast.InPort)
    def visit(self, node):
        self._check_port(node, 'in', self.issue_tracker)

    @visitor.when(ast.OutPort)
    def visit(self, node):
        self._check_port(node, 'out', self.issue_tracker)

    @visitor.when(ast.InternalInPort)
    def visit(self, node):
        if self.component:
            if node.port not in self.component.outports:
                reason = "Component {} has no outport '{}'".format(self.component.name, node.port)
                self.issue_tracker.add_error(reason, node)
        else:
            reason = "Internal port '.{}' outside component definition".format(node.port)
            self.issue_tracker.add_error(reason, node)


    @visitor.when(ast.InternalOutPort)
    def visit(self, node):
        if self.component:
            if node.port not in self.component.inports:
                reason = "Component {} has no inport '{}'".format(self.component.name, node.port)
                self.issue_tracker.add_error(reason, node)
        else:
            reason = "Internal port '.{}' outside component definition".format(node.port)
            self.issue_tracker.add_error(reason, node)

    @visitor.when(ast.Link)
    def visit(self, node):
        passthrough = type(node.inport) is ast.InternalInPort and type(node.outport) is ast.InternalOutPort
        if passthrough:
            self.issue_tracker.add_error('Component inport connected directly to outport.', node.inport)
        else:
            map(self.visit, node.children)

    @visitor.when(ast.PortProperty)
    def visit(self, node):
        block = node.parent
        # FIXME: If direction present but redundant, make sure it is correct wrt port
        if node.actor is None:
            iip = query(block, kind=ast.InternalInPort, maxdepth=2, attributes={'port':node.port})
            iop = query(block, kind=ast.InternalOutPort, maxdepth=2, attributes={'port':node.port})
            n_iip, n_iop = len(iip), len(iop)
            if n_iip == 0 and n_iop == 0:
                self.issue_tracker.add_error('No such port.', node)
            elif n_iip == 1 and n_iop == 1:
                if node.direction not in ["in", "out"]:
                    reason = "Port property need direction since ambigious names"
                    self.issue_tracker.add_error(reason, node)
        else:
            ip = query(block, kind=ast.InPort, maxdepth=2, attributes={'actor':node.actor, 'port':node.port})
            op = query(block, kind=ast.OutPort, maxdepth=2, attributes={'actor':node.actor, 'port':node.port})
            n_ip, n_op = len(ip), len(op)
            if n_ip == 0 and n_op == 0:
                self.issue_tracker.add_error('No such port.', node)
            elif n_ip == 1 and n_op == 1:
                if node.direction not in ["in", "out"]:
                    reason = "Port property need direction since ambigious names"
                    self.issue_tracker.add_error(reason, node)



class CodeGen(object):

    verbose = False
    verbose_nodes = False

    """
    Generate code from a source file
    FIXME: Use a writer class to generate output in various formats
    """
    def __init__(self, ast_root, script_name):
        super(CodeGen, self).__init__()
        self.root = ast_root
        # self.verify = verify
        self.app_info = {
            'name':script_name,
            'actors': {},
            'connections': {},
            'port_properties': {},
            'valid': True
        }
        # FIXME: Why is this needed here?
        program = query(ast_root, kind=ast.Block, attributes={'namespace':'__scriptname__'})
        if program:
            program[0].namespace = script_name
        self.dump_tree('ROOT')


    def dump_tree(self, heading):
        if not self.verbose:
            return
        ast.Node._verbose_desc = self.verbose_nodes
        printer = astprint.BracePrinter()
        print "========\n{}\n========".format(heading)
        printer.process(self.root)


    def expand_portlists(self, issue_tracker):
        rw = PortlistRewrite(issue_tracker)
        rw.visit(self.root)
        # self.dump_tree('Portlist Expanded')

    def substitute_implicit_outports(self, issue_tracker):
        rw = ImplicitOutPortRewrite(issue_tracker)
        rw.visit(self.root)
        # self.dump_tree('OutPort Rewrite')

    def substitute_implicit_inports(self, issue_tracker):
        rw = ImplicitInPortRewrite(issue_tracker)
        rw.visit(self.root)
        # self.dump_tree('InPort Rewrite')

    def substitute_voidports(self, issue_tracker):
        rw = VoidPortRewrite(issue_tracker)
        rw.visit(self.root)
        # self.dump_tree('VoidPort Rewrite')

    def resolve_constants(self, issue_tracker):
        rc = ReplaceConstants(issue_tracker)
        rc.process(self.root)
        # self.dump_tree('RESOLVED CONSTANTS')

    def consistency_check(self, issue_tracker):
        cc = ConsistencyCheck(issue_tracker)
        cc.process(self.root)
        self.dump_tree('Consistency Check')

    def collect_port_properties(self, issue_tracker):
        cpp = CollectPortProperties(issue_tracker)
        cpp.visit(self.root)
        self.dump_tree('Collected port properties')

    def expand_components(self, issue_tracker, verify):
        expander = Expander(issue_tracker)
        expander.process(self.root, verify)
        self.dump_tree('EXPANDED')

    def flatten(self, issue_tracker):
        flattener = Flatten(issue_tracker)
        flattener.process(self.root)
        self.dump_tree('FLATTENED')

    def coalesce_properties(self, issue_tracker):
        consolidate = CoalesceProperties(issue_tracker)
        consolidate.process(self.root)
        self.dump_tree('Coalesced')

    def merge_properties(self, issue_tracker):
        mp = MergePortProperties(issue_tracker)
        mp.visit(self.root)
        self.dump_tree('Merged properties')

    def check_properties(self, issue_tracker):
        cp = CheckPortProperties(issue_tracker)
        cp.visit(self.root)
        self.dump_tree('Checked properties')

    def generate_code_from_ast(self, issue_tracker):
        gen_app_info = AppInfo(self.app_info, self.root, issue_tracker)
        gen_app_info.process()

    def phase1(self, issue_tracker):
        # Change all ImplicitPort objects into std.Constant actors and relink
        self.substitute_implicit_outports(issue_tracker)
        # Break up list of inports into individual Link objects
        self.expand_portlists(issue_tracker)
        # Change all TransformedPort objects into std.Constantify actors and relink
        self.substitute_implicit_inports(issue_tracker)
        # Change all VoidPort objects into flow.Void/flow.Terminate actors and link
        self.substitute_voidports(issue_tracker)
        # Replace all constant objects with their values
        self.resolve_constants(issue_tracker)
        # Check graph consistency (e.g. missing connections etc.)
        self.consistency_check(issue_tracker)

    def phase2(self, issue_tracker, verify):
        # Replace Component objects with a clone of the component graph
        self.expand_components(issue_tracker, verify)
        # Move port properties from actors and PortProperty statements into ports
        self.collect_port_properties(issue_tracker)
        # Replace hierachy with namespace for all objects
        self.flatten(issue_tracker)
        # Retrieve the port properties from the ports (now with correctly namespaced actor names)
        self.coalesce_properties(issue_tracker)
        # Merge possibly conflicting port properties, remove redundant properties
        self.merge_properties(issue_tracker)
        self.check_properties(issue_tracker)

    def generate_code(self, issue_tracker, verify):
        self.phase1(issue_tracker)
        self.phase2(issue_tracker, verify)
        self.generate_code_from_ast(issue_tracker)
        self.app_info['valid'] = (issue_tracker.error_count == 0)


def query(root, kind=None, attributes=None, maxdepth=1024):
    finder = Finder()
    finder.find_all(root, kind, attributes=attributes, maxdepth=maxdepth)
    # print
    # print "QUERY", kind.__name__, attributes, finder.matches
    return finder.matches

def _calvin_cg(source_text, app_name):
    ast_root, issuetracker = calvin_parse(source_text)
    cg = CodeGen(ast_root, app_name)
    return cg, issuetracker

# FIXME: [PP] Change calvin_ to calvinscript_
def calvin_codegen(source_text, app_name, verify=True):
    """
    Generate application code from script, return deployable and issuetracker.

    Parameter app_name is required to provide a namespace for the application.
    Optional parameter verify is deprecated, defaults to True.
    """
    cg, issuetracker = _calvin_cg(source_text, app_name)
    cg.generate_code(issuetracker, verify)
    return cg.app_info, issuetracker

def calvin_astgen(source_text, app_name, verify=True):
    """
    Generate AST from script, return processed AST and issuetracker.

    Parameter app_name is required to provide a namespace for the application.
    Optional parameter verify is deprecated, defaults to True.
    """
    cg, issuetracker = _calvin_cg(source_text, app_name)
    cg.phase1(issuetracker)
    cg.phase2(issuetracker, verify)
    return cg.root, issuetracker


def calvin_components(source_text, names=None):
    """
    Generate AST from script, return requested components and issuetracker.

    If there are errors during AST processing, no components will be returned.
    Optional parameter names is a list of components to extract, if present (or None)
    return all components found in script.
    """
    cg, issuetracker = _calvin_cg(source_text, '')
    cg.phase1(issuetracker)

    if issuetracker.error_count:
        return [], issuetracker

    if names:
        comps = []
        for name in names:
            # NB. query returns a list
            comp = query(cg.root, kind=ast.Component, attributes={'name':name}, maxdepth=1)
            if not comp:
                reason = "Component '{}' not found".format(name)
                issuetracker.add_error(reason, cg.root)
            else:
                comps.extend(comp)
    else:
        comps = query(cg.root, kind=ast.Component, maxdepth=1)

    return comps, issuetracker



if __name__ == '__main__':
    from inspect import cleandoc
    import json

    script = 'inline'
    source_text = r"""
    """

    source_text = cleandoc(source_text)
    print source_text
    print
    ai, it = calvin_codegen(source_text, script)
    print
    print json.dumps(ai, indent = 4)
    print
    if it.issue_count == 0:
        print "No issues"
        print ai
    for i in it.formatted_issues(custom_format="{type!c}: {reason} {filename}:{line}:{col}", filename=script):
        print i






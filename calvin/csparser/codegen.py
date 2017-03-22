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


class ImplicitPortRewrite(object):
    """
    ImplicitPortRewrite takes care of the construct
        <value> > foo.in
    by replacing <value> with a std.Constant(data=<value>) actor.

    Running this cannot not fail and thus cannot cause an issue.
    """
    def __init__(self, issue_tracker):
        super(ImplicitPortRewrite, self).__init__()
        self.counter = 0
        self.issue_tracker = issue_tracker

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
            self.counter += 1
            const_name = '_literal_const_'+str(self.counter)
        const_actor = ast.Assignment(ident=const_name, actor_type='std.Constant', args=args)
        const_actor.debug_info = node.arg.debug_info
        const_actor_port = ast.OutPort(actor=const_name, port='token')
        link = node.parent
        link.replace_child(node, const_actor_port)
        block = link.parent
        block.add_child(const_actor)

    @visitor.when(ast.TransformedPort)
    def visit(self, node):
        # std.Constantify(constant) ports: in/out
        args = [ast.NamedArg(ident=ast.Id(ident='constant'), arg=node.value)]
        if node.label:
            transform_name = node.label.ident
        else:
            # Create a unique name if not given by label
            self.counter += 1
            transform_name = '_transform_'+str(self.counter)
        transform_actor = ast.Assignment(ident=transform_name, actor_type='std.Constantify', args=args)
        transform_actor.debug_info = node.value.debug_info
        transform_actor_outport = ast.OutPort(actor=transform_name, port='out')
        transform_actor_inport = ast.InPort(actor=transform_name, port='in')

        link = node.parent
        block = link.parent

        block.add_child(transform_actor)

        new_link = ast.Link(outport=transform_actor_outport, inport=node.port)
        block.add_child(new_link)
        link.inport = transform_actor_inport

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

        self.counter += 1
        actor_name = '_void_'+str(self.counter)
        void_actor = ast.Assignment(ident=actor_name, actor_type=actor_type)
        void_actor_port = port_class(actor=actor_name, port='void')
        link = node.parent
        link.replace_child(node, void_actor_port)
        block = link.parent
        block.add_child(void_actor)


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
            # Transfer actor declared port properties here so that they can be consolidated and validated
            for port, pp in  node.metadata['input_properties'].items():
                name = node.ident
                port_property = ast.PortProperty(actor=name, port=port, direction="in", debug_info=node.debug_info)
                for ident, value in pp.items():
                    port_property.add_property(ident, value)
                node.parent.add_child(port_property)
            for port, pp in  node.metadata['output_properties'].items():
                name = node.ident
                port_property = ast.PortProperty(actor=name, port=port, direction="out", debug_info=node.debug_info)
                for ident, value in pp.items():
                    port_property.add_property(ident, value)
                node.parent.add_child(port_property)
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
        # Clone assignment to clone the arguments
        # FIXME: Is cloning necessary here, since we construct an arg dict anyway?
        ca = node.clone()
        args = ca.children
        # Clone block from component definition
        new = compdef.clone()
        new.namespace = node.ident
        # Add arguments from assignment to block
        new.args = {x.ident.ident: x.arg for x in args}
        node.parent.replace_child(node, new)
        # Recurse
        self.visit(new)


class ResolvePortRefs(object):
    """docstring for PortlistRewrite"""
    def __init__(self, issue_tracker):
        super(ResolvePortRefs, self).__init__()
        self.issue_tracker = issue_tracker

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if node.is_leaf():
            return
        map(self.visit, node.children[:])

    @visitor.when(ast.NamedArg)
    def visit(self, node):

        def _resolve_portref(ref):
            return "{}.{}".format(v.actor, v.port)

        # Exclude constant identifiee from processing
        if type(node.arg) is ast.Id:
            return

        value = node.arg.value
        if isinstance(value, dict):
            for k, v in value.iteritems():
                if isinstance(v, ast.PortRef):
                    value[k] = _resolve_portref(v)

        if isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, ast.PortRef):
                    value[i] = _resolve_portref(v)


class Flatten(object):
    """
    Flattens a block by wrapping everything in the block's namespace
    and propagating arguments before removing the block
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

    @visitor.when(ast.Port)
    def visit(self, node):
        if node.actor:
            node.actor = self.stack[-1] + ':' + node.actor
        else:
            node.actor = self.stack[-1]

    @visitor.when(ast.PortProperty)
    def visit(self, node):
        if node.actor is not None:
            node.actor = self.stack[-1] + ':' + node.actor

    @visitor.when(ast.Block)
    def visit(self, node):
        # Recurse into blocks first
        self.stack.append(node.namespace)
        blocks = [x for x in node.children if type(x) is ast.Block]
        map(self.visit, blocks)


        consumed = set()
        produced = []

        def _clone_target(target, port):
            # N.B. is_inport is true if port is subclass of ast.OutPort
            #      since internal ports have opposite interpretation on the inside vs. outside
            is_inport = isinstance(port, ast.OutPort)
            clone = target.clone()
            linked_port = port.parent.inport if is_inport else port.parent.outport
            clone.actor = linked_port.actor
            clone.port = linked_port.port
            # Set direction since the port name might be ambiguous
            clone.direction = "in" if is_inport else "out"
            produced.append(clone)
            consumed.add(target)

        def _clone_targets(targets, port):
            for target in targets:
                _clone_target(target, port)

        def _retarget_port_properties(ports):
            for p in ports:
                targets = query(node, kind=ast.PortProperty, attributes={'actor':p.actor, 'port':p.port})
                _clone_targets(targets, p)

        def _retarget_internal_port_properties(ports):
            for p in ports:
                targets = query(node, kind=ast.PortProperty, attributes={'actor':None, 'port':p.port})
                is_inport = isinstance(p, ast.InPort)
                query_kind = ast.OutPort if is_inport else ast.InPort
                qports = query(node, kind=query_kind, attributes={'actor':p.actor, 'port':p.port})
                for qport in qports:
                    _clone_targets(targets, qport)

        iips = query(node, kind=ast.InternalInPort, maxdepth=2)
        iops = query(node, kind=ast.InternalOutPort, maxdepth=2)
        _retarget_port_properties(iips + iops)
        _retarget_internal_port_properties(iips + iops)

        for prop in consumed:
            prop.delete()

        node.add_children(produced)

        #
        # Relink
        #

        # Replace and delete links (manipulates children)
        iops = query(node, kind=ast.InternalOutPort, maxdepth=2)
        consumed = set()
        for iop in iops:
            targets = query(node, kind=ast.InPort, attributes={'actor':iop.actor, 'port':iop.port})
            if not targets:
                continue
            for target in targets:
                link = target.parent.clone()
                link.inport = iop.parent.inport.clone()
                node.add_child(link)
                # Defer deletion of link since can have multiple matches
                consumed.add(target.parent)
            iop.parent.delete()

        for link in consumed:
            link.delete()

        iips = query(node, kind=ast.InternalInPort, maxdepth=2)
        consumed = set()
        for iip in iips:
            targets = query(node, kind=ast.OutPort, attributes={'actor':iip.actor, 'port':iip.port})
            if not targets:
                continue
            for target in targets:
                link = target.parent.clone()
                link.outport = iip.parent.outport.clone()
                node.add_child(link)
                # Defer deletion of link since can have multiple matches
                consumed.add(target.parent)
            iip.parent.delete()

        for link in consumed:
            link.delete()

        # Promote ports and assignments (handled by visitors)
        non_blocks = [x for x in node.children if type(x) is not ast.Block]
        map(self.visit, non_blocks)

        # Raise promoted children to outer level
        node.parent.add_children(node.children)

        # Delete this node
        node.delete()
        self.stack.pop()


class ConsolidatePortProperty(object):
    """
    Consolidates port properties by removing duplicates and
    moving properties to one per port, and handle conflicting
    property settings. Also add the nbr_peers property for all
    ports with the number of connecting peers.
    """
    def __init__(self, issue_tracker):
        super(ConsolidatePortProperty, self).__init__()
        self.issue_tracker = issue_tracker
        self.inports = {}
        self.outports = {}

    def process(self, root):
        self.visit(root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        targets = query(node, kind=ast.PortProperty)
        keep = []
        remove = []
        for target in targets:
            if any([p.is_same_port(target) for p in keep]):
                remove.append(target)
                continue
            # Not consolidated yet
            keep.append(target)
            same_port = [t for t in targets if t.is_same_port(target)]
            for same in same_port:
                try:
                    target.consolidate(same)
                except calvinresponse.CalvinResponseException as e:
                    if e.status == calvinresponse.BAD_REQUEST:
                        self.issue_tracker.add_error(e.data, target)
                        self.issue_tracker.add_error(e.data, same)
        for p in remove:
            node.remove_child(p)

        # Count links
        links = [x for x in node.children if type(x) is ast.Link]
        map(self.visit, links)
        # Add empty port properties for any ports missing it
        inports = [(x.actor, x.port) for x in node.children if type(x) is ast.PortProperty
                        and (x.direction is None or x.direction == "in")]
        outports = [(x.actor, x.port) for x in node.children if type(x) is ast.PortProperty
                        and (x.direction is None or x.direction == "out")]
        for port, nbr in self.inports.items():
            if port not in inports:
                node.add_child(ast.PortProperty(actor=port[0], port=port[1], direction="in"))
        for port, nbr in self.outports.items():
            if port not in outports:
                node.add_child(ast.PortProperty(actor=port[0], port=port[1], direction="out"))
        # Visit all port properties
        portproperties = [x for x in node.children if type(x) is ast.PortProperty]
        map(self.visit, portproperties)

    @visitor.when(ast.Link)
    def visit(self, link):
        # Count incomming and outgoing links between ports
        name = (link.inport.actor, link.inport.port)
        self.inports[name] = self.inports.get(name, 0) + 1
        name = (link.outport.actor, link.outport.port)
        self.outports[name] = self.outports.get(name, 0) + 1

    @visitor.when(ast.PortProperty)
    def visit(self, node):
        # Apply nbr_peers property and set direction if that is missing and no ambiguity
        name = (node.actor, node.port)
        if node.direction is None and name in self.inports.keys():
            node.add_property(ident="nbr_peers", arg=self.inports[name])
            if name not in self.outports.keys():
                node.direction = "in"
            else:
                reason = "Port property need direction since ambigious names"
                self.issue_tracker.add_error(reason, node)
                node.direction = "ambigious"
        elif node.direction is None and name in self.outports.keys():
            node.add_property(ident="nbr_peers", arg=self.outports[name])
            node.direction = "out"
        elif node.direction == "in" and name in self.inports.keys():
            node.add_property(ident="nbr_peers", arg=self.inports[name])
        elif node.direction == "out" and name in self.outports.keys():
            node.add_property(ident="nbr_peers", arg=self.outports[name])

        # Validate port properties
        port_properties = {p.ident.ident: p.arg.value for p in node.children}
        for key, values in port_properties.items():
            if not isinstance(values, (list, tuple)):
                values = [values]
            for value in values:
                if key not in port_property_data.keys():
                    reason = "Port property {} is unknown".format(key)
                    self.issue_tracker.add_error(reason, node)
                    continue
                ppdata = port_property_data[key]
                if ppdata['type'] == "category":
                    if value not in ppdata['values']:
                        reason = "Port property {} can only have values {}".format(
                            key, ", ".join(ppdata['values'].keys()))
                        self.issue_tracker.add_error(reason, node)
                        continue
                    if node.direction not in ppdata['values'][value]['direction']:
                        reason = "Port property {}={} is only for {} ports".format(
                            key, value, ppdata['values'][value]['direction'])
                        self.issue_tracker.add_error(reason, node)
                        continue
                if ppdata['type'] == 'scalar':
                    if not isinstance(value, numbers.Number):
                        reason = "Port property {} can only have scalar values".format(key)
                        self.issue_tracker.add_error(reason, node)
                        continue
                if ppdata['type'] == 'string':
                    if not isinstance(value, basestring):
                        reason = "Port property {} can only have string values".format(key)
                        self.issue_tracker.add_error(reason, node)
                        continue
                if key == 'nbr_peers' and value > 1 and node.direction == 'in':
                    # Verify that inports with multiple connections have a routing property for multipeers
                    ports = query(node.parent, kind=ast.InPort, attributes={'actor': node.actor, 'port': node.port})
                    if not ports:
                        ports = [node]
                    try:
                        routings = port_properties['routing']
                        if not isinstance(routings, (list, tuple)):
                            routings = [routings]
                        removed = []
                        for routing in routings[:]:
                            if not port_property_data['routing']['values'][routing].get('multipeer', False):
                                routings.remove(routing)
                                removed.append(routing)
                        if routings:
                            # Possible routings available
                            if removed:
                                # ... but some options are removed
                                for p in node.children:
                                    if p.ident.ident == "routing":
                                        for routing_value in removed:
                                            p.arg.value.remove(routing_value)
                        else:
                            # No routing for multiple peers
                            self._issue_on_ports(ports)
                            continue
                    except KeyError:
                        self._issue_on_ports(ports)
                        continue

    def _issue_on_ports(self, ports):
        for port in ports:
            try:
                actor_name = port.actor.split(':',1)[1]
            except:
                actor_name = port.actor
            port_name = "'{}.{}'".format(actor_name, port.port)
            try:
                actor_name = port.parent.outport.actor.split(':',1)[1]
                peer_name = "('{}.{}')".format(actor_name, port.parent.outport.port)
            except:
                peer_name = ""
            reason = "Input port {} with multiple connections {} must have a routing port property.".format(
                        port_name, peer_name)
            self.issue_tracker.add_error(reason, port)


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
        constants = query(root, ast.Constant)
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
            node.replace_child(node.arg, value.clone())


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
            matches = query(node, kind=ast.InternalInPort, attributes={'port':port})
            if not matches:
                reason = "Component {} is missing connection to outport '{}'".format(node.name, port)
                self.issue_tracker.add_error(reason, node)
        for port in node.inports:
            matches = query(node, kind=ast.InternalOutPort, attributes={'port':port})
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

    @visitor.when(ast.Assignment)
    def visit(self, node):
        node.metadata = _lookup(node, self.issue_tracker)
        if not node.metadata['is_known']:
            # error issued in _lookup
            return

        _check_arguments(node, self.issue_tracker)

        for port in node.metadata['inputs']:
            matches = query(self.block, kind=ast.InPort, attributes={'actor':node.ident, 'port':port})
            matches = matches + query(self.block, kind=ast.InternalInPort, attributes={'actor':node.ident, 'port':port})
            if not matches:
                reason = "{} {} ({}.{}) is missing connection to inport '{}'".format(node.metadata['type'].capitalize(), node.ident, node.metadata.get('ns', 'local'), node.metadata['name'], port)
                self.issue_tracker.add_error(reason, node)

        for port in node.metadata['outputs']:
            matches = query(self.block, kind=ast.OutPort, attributes={'actor':node.ident, 'port':port})
            matches = matches + query(self.block, kind=ast.InternalOutPort, attributes={'actor':node.ident, 'port':port})
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
        self.dump_tree('Portlist Expanded')


    def substitute_implicit_ports(self, issue_tracker):
        # Implicit port rewrite
        rw = ImplicitPortRewrite(issue_tracker)
        rw.visit(self.root)
        self.dump_tree('Port Rewrite')

    def resolve_constants(self, issue_tracker):
        rc = ReplaceConstants(issue_tracker)
        rc.process(self.root)
        self.dump_tree('RESOLVED CONSTANTS')

    def consistency_check(self, issue_tracker):
        cc = ConsistencyCheck(issue_tracker)
        cc.process(self.root)
        self.dump_tree('Consistency Check')

    def expand_components(self, issue_tracker, verify):
        expander = Expander(issue_tracker)
        expander.process(self.root, verify)
        self.dump_tree('EXPANDED')

    def flatten(self, issue_tracker):
        flattener = Flatten(issue_tracker)
        flattener.process(self.root)
        self.dump_tree('FLATTENED')

    def resolve_portrefs(self, issue_tracker):
        resolver = ResolvePortRefs(issue_tracker)
        resolver.visit(self.root)
        self.dump_tree('RESOLVED PORTREFS')

    def consolidate(self, issue_tracker):
        consolidate = ConsolidatePortProperty(issue_tracker)
        consolidate.process(self.root)
        self.dump_tree('CONSOLIDATED')

    def generate_code_from_ast(self, issue_tracker):
        gen_app_info = AppInfo(self.app_info, self.root, issue_tracker)
        gen_app_info.process()

    def phase1(self, issue_tracker):
        self.expand_portlists(issue_tracker)
        self.substitute_implicit_ports(issue_tracker)
        self.resolve_constants(issue_tracker)
        self.consistency_check(issue_tracker)

    def phase2(self, issue_tracker, verify):
        self.expand_components(issue_tracker, verify)
        self.resolve_portrefs(issue_tracker)
        self.flatten(issue_tracker)
        self.consolidate(issue_tracker)

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
    ast_root, _, issuetracker = calvin_parse(source_text)
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

    script = 'inline'
    source_text = \
    """
    snk : io.Print()
    1 > snk.token
    """
    source_text = cleandoc(source_text)
    print source_text
    print
    ai, it = calvin_codegen(source_text, script)
    if it.issue_count == 0:
        print "No issues"
        print ai
    for i in it.formatted_issues(custom_format="{type!c}: {reason} {filename}:{line}:{col}", filename=script):
        print i






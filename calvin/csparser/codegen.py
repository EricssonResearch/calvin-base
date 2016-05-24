import astnode as ast
import visitor
import astprint
from calvin.actorstore.store import DocumentationStore, GlobalStore


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
        # FIXME: Harmonize metadata
        metadata = DocumentationStore().actor_docs(node.actor_type)
        if metadata:
            metadata['is_known'] = True
            metadata['inputs'] = [p for p, _ in metadata['inputs']]
            metadata['outputs'] = [p for p, _ in metadata['outputs']]
        else:
            metadata = {'is_known': False}
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
    given_idents = {a.children[0].ident: a.children[0] for a in given_args}
    given_keys = [a.children[0].ident for a in given_args]
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
        arg_id, arg_val = arg_node.children
        if type(arg_val) is ast.Value:
            args[arg_id.ident] = arg_val.value
        else:
            reason = "Undefined identifier: '{}'".format(arg_val.ident)
            issue_tracker.add_error(reason, arg_val)
    return args



class IssueTracker(object):
    def __init__(self):
        super(IssueTracker, self).__init__()
        self.issues = []
        self.err_count = 0
        self.warn_count = 0

    def _add_issue(self, issue_type, reason, node):
        issue = {
            'type': issue_type,
            'reason': reason,
        }
        issue.update(node.debug_info or {'line':0, 'col':0, 'FIXME':True})
        if issue not in self.issues:
            self.issues.append(issue)
            if issue['type'] is 'error':
                self.err_count += 1
            else:
                self.warn_count +=1

    def add_error(self, reason, node):
        self._add_issue('error', reason, node)

    def add_warning(self, reason, node):
        self._add_issue('warning', reason, node)


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
        const_value = node.children[0]
        args = [ ast.NamedArg(ident=ast.Id(ident='data'), arg=const_value),  ast.NamedArg(ident=ast.Id(ident='n'), arg=ast.Value(value=-1))]
        self.counter += 1
        const_name = '_literal_const_'+str(self.counter)
        const_actor = ast.Assignment(ident=const_name, actor_type='std.Constant', args=args)
        const_actor_port = ast.OutPort(actor=const_name, port='token')
        link = node.parent
        link.replace_child(node, const_actor_port)
        block = link.parent
        block.add_child(const_actor)


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
        # FIXME: Change to use new metadata storage
        if not node.metadata:
            node.metadata = _lookup(node, self.issue_tracker)
        if node.metadata['is_known'] and node.metadata['type'] is 'actor':
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
        ca = node.clone()
        args = ca.children
        # Clone block from component definition
        new = compdef.clone()
        new.namespace = node.ident
        # Add arguments from assignment to block
        new.args = {x.children[0].ident: x.children[1] for x in args}
        node.parent.replace_child(node, new)
        # Recurse
        self.visit(new)


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
        value_node = node.children[1]
        if type(value_node) is ast.Id:
            # Get value from grandparent (block)
            block = node.parent.parent
            key = value_node.ident
            if key in block.args:
                value = block.args[key]
                node.replace_child(value_node, value)

    @visitor.when(ast.Port)
    def visit(self, node):
        if node.actor:
            node.actor = self.stack[-1] + ':' + node.actor
        else:
            node.actor = self.stack[-1]

    @visitor.when(ast.Block)
    def visit(self, node):
        # Recurse into blocks first
        self.stack.append(node.namespace)
        blocks = [x for x in node.children if type(x) is ast.Block]
        map(self.visit, blocks)

        # Replace and delete links (manipulates children)
        iops = query(node, kind=ast.InternalOutPort, maxdepth=2)
        consumed = set()
        for iop in iops:
            targets = query(node, kind=ast.InPort, attributes={'actor':iop.actor, 'port':iop.port})
            if len(targets) is not 1:
                # Covered by consistency check
                continue
            # if not targets:
            #     continue
            # if len(targets) > 1:
            #     reason = "Actor '{name}' has multiple connections to inport '{port}'".format(name=iop.actor, port=iop.port)
            #     for target in targets:
            #         self.issue_tracker.add_error(reason, target)

            target = targets[0]
            link = target.parent.clone()
            link.inport = iop.parent.inport.clone()
            node.add_child(link)
            iop.parent.delete()
            # Defer deletion of link since can have multiple matches
            consumed.add(target.parent)

        for link in consumed:
            link.delete()

        iips = query(node, kind=ast.InternalInPort, maxdepth=2)
        for iip in iips:
            targets = query(node, kind=ast.OutPort, attributes={'actor':iip.actor, 'port':iip.port})
            if not targets:
                continue
            for target in targets:
                target.parent.outport = iip.parent.outport.clone()
            iip.parent.delete()

        # Promote ports and assignments (handled by visitors)
        non_blocks = [x for x in node.children if type(x) is not ast.Block]
        map(self.visit, non_blocks)

        # Raise promoted children to outer level
        node.parent.add_children(node.children)

        # Delete this node
        node.delete()
        self.stack.pop()



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


class ReplaceConstants(object):
    """docstring for ReplaceConstants"""
    def __init__(self, issue_tracker):
        super(ReplaceConstants, self).__init__()
        self.issue_tracker = issue_tracker

    def process(self, root):
        constants = query(root, ast.Constant)
        defined = {c.children[0].ident: c.children[1] for c in constants if type(c.children[1]) is ast.Value}
        unresolved = [c for c in constants if type(c.children[1]) is ast.Id]
        seen = [c.children[0].ident for c in constants if type(c.children[1]) is ast.Id]
        while True:
            did_replace = False
            for c in unresolved[:]:
                key, const_key = c.children
                if const_key.ident in defined:
                    defined[key.ident] = defined[const_key.ident]
                    unresolved.remove(c)
                    seen.append(c.children[0].ident)
                    did_replace = True
            if not did_replace:
                break
        for c in unresolved:
            key, const_key = c.children
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
        arg = node.children[1]
        if type(arg) is ast.Value:
            return
        if arg.ident in self.definitions:
            value = self.definitions[arg.ident]
            node.replace_child(arg, value.clone())


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
            referenced_values = [m.children[1].ident for m in matches if type(m.children[1]) is ast.Id]
            if not arg_name in referenced_values:
                reason = "Unused argument: '{}'".format(arg_name)
                self.issue_tracker.add_error(reason, node)

        for port in node.outports:
            matches = query(node, kind=ast.InternalInPort, attributes={'port':port})
            if not matches:
                reason = "Component {} is missing connection to outport '{}'".format(node.name, port)
                self.issue_tracker.add_error(reason, node)
            elif len(matches) > 1:
                reason = "Component {} has multiple connections to outport '{}'".format(node.name, port)
                for match in matches:
                    self.issue_tracker.add_error(reason, match)
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
                reason = "Actor {} ({}.{}) is missing connection to inport '{}'".format(node.ident, node.metadata['ns'], node.metadata['name'], port)
                self.issue_tracker.add_error(reason, node)
            elif len(matches) > 1:
                reason = "Actor {} ({}.{}) has multiple connections to inport '{}'".format(node.ident, node.metadata['ns'], node.metadata['name'], port)
                for match in matches:
                    self.issue_tracker.add_error(reason, match)

        for port in node.metadata['outputs']:
            matches = query(self.block, kind=ast.OutPort, attributes={'actor':node.ident, 'port':port})
            matches = matches + query(self.block, kind=ast.InternalOutPort, attributes={'actor':node.ident, 'port':port})
            if not matches:
                reason = "Actor {} ({}.{}) is missing connection to outport '{}'".format(node.ident, node.metadata['ns'], node.metadata['name'], port)
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
            reason = "Actor {} ({}.{}) has no {}port '{}'".format(node.actor, metadata['ns'], metadata['name'], direction, node.port)
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
    def __init__(self, ast_root, script_name, verify=True):
        super(CodeGen, self).__init__()
        self.root = ast_root
        self.verify = verify
        self.app_info = {
            'name':script_name,
            'actors': {},
            'connections': {},
            'valid': True
        }
        program = query(ast_root, kind=ast.Block, attributes={'namespace':'__scriptname__'})
        if program:
            program[0].namespace = script_name


    def dump_tree(self, heading):
        if not self.verbose:
            return
        ast.Node._verbose_desc = self.verbose_nodes
        printer = astprint.BracePrinter()
        print "========\n{}\n========".format(heading)
        printer.process(self.root)


    def run(self):
        issue_tracker = IssueTracker()

        ##
        # Tree re-write
        #
        self.dump_tree('ROOT')

        ##
        # Implicit port rewrite
        rw = ImplicitPortRewrite(issue_tracker)
        rw.visit(self.root)
        self.dump_tree('Port Rewrite')

        ##
        # Resolve Constants
        rc = ReplaceConstants(issue_tracker)
        rc.process(self.root)
        self.dump_tree('RESOLVED CONSTANTS')

        ##
        # Check graph consistency
        cc = ConsistencyCheck(issue_tracker)
        cc.process(self.root)
        self.dump_tree('Consistency Check')

        ##
        # Expand components
        expander = Expander(issue_tracker)
        expander.process(self.root, self.verify)
        self.dump_tree('EXPANDED')

        ##
        # Flatten blocks
        flattener = Flatten(issue_tracker)
        flattener.process(self.root)
        self.dump_tree('FLATTENED')

        ##
        # "code" generation
        gen_app_info = AppInfo(self.app_info, self.root, issue_tracker)
        gen_app_info.process()

        self.app_info['valid'] = (issue_tracker.err_count == 0)
        self.issues = issue_tracker.issues

def query(root, kind=None, attributes=None, maxdepth=1024):
    finder = Finder()
    finder.find_all(root, kind, attributes=attributes, maxdepth=maxdepth)
    return finder.matches

def generate_app_info(ast, name='anonymous', verify=True):
    cg = CodeGen(ast, name, verify=verify)
    cg.run()
    return cg.app_info, cg.issues


if __name__ == '__main__':
    from parser_regression_tests import run_issue_check
    run_issue_check(tests=['undefined_constant'], testdir='/Users/eperspe/Source/calvin-base/calvin/csparser/testscripts/issue-reporting-tests')


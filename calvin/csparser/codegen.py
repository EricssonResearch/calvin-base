import astnode as ast
import visitor
import astprint
from calvin.actorstore.store import DocumentationStore, GlobalStore


def _create_signature(actor_type, metadata):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    signature_desc = {'is_primitive': True,
                      'actor_type': actor_type,
                      'inports': [p for p,_ in metadata['inputs']],
                      'outports': [p for p,_ in metadata['outputs']]}
    return GlobalStore.actor_signature(signature_desc)


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
        const_actor_port = ast.Port(actor=const_name, port='token')
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
        local_components = query(root, kind=ast.Component, maxdepth=1)
        self.components = {comp.name : comp.children[0] for comp in local_components}
        # Remove from AST
        for comp in local_components:
            comp.delete()

        self.visit(root)

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

        def is_local_component(actor_type):
            return '.' not in actor_type

        def construct_metadata(node):
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

        # FIXME: Change to use new metadata storage
        if not is_local_component(node.actor_type):
            metadata = DocumentationStore().actor_docs(node.actor_type)
            if metadata and metadata['type'] is 'actor':
                metadata['is_known']=True
                node.metadata = metadata
                return

            if not metadata:
                # Unknown actor => construct metadata from graph + args unless verify is True
                if self.verify:
                    reason = "Unknown actor type: '{}'".format(node.actor_type)
                    self.issue_tracker.add_error(reason, node)
                else:
                    metadata = construct_metadata(node)
                    node.metadata = metadata
                    reason = "Not validating actor type: '{}'".format(node.actor_type)
                    self.issue_tracker.add_warning(reason, node)
                return

            # Component from store
            compdef = metadata['definition']
            v = RestoreParents()
            v.visit(compdef)
        else:
            if node.actor_type not in self.components:
                reason = "Unknown local component: '{}'".format(node.actor_type)
                self.issue_tracker.add_error(reason, node)
                return
            # Component from script
            compdef = self.components[node.actor_type]

        #
        # We end up here if node is in fact a component
        #
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

    def process(self, root, name):
        self.stack.append(name) # FIXME: Fix this by making root node ast.Block instead of ast.Node
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
        # Propagate parameters
        for key, value_node in node.args.iteritems():
            if type(value_node) is ast.Id:
                # Get value from parent (block)
                block = node.parent
                parent_key = value_node.ident
                if parent_key in block.args:
                    value = block.args[parent_key]
                    node.args[key] = value

        # Recurse into blocks first
        if node.namespace: # FIXME: Fix this by making root node ast.Block instead of ast.Node
            self.stack.append(node.namespace)
        blocks = [x for x in node.children if type(x) is ast.Block]
        map(self.visit, blocks)

        # Replace and delete links (manipulates children)
        # links = query(node, kind=ast.Link, maxdepth=2)
        iops = query(node, kind=ast.InternalOutPort, maxdepth=2)
        # Handle with care, potential fan-out from internal outport
        mapping = {}
        for iop in iops:
            key = (iop.actor, iop.port)
            mapping.setdefault(key, []).append(iop.parent.inport)

        for key in mapping:
            replacements = mapping[key]

            # There should be at most one target
            actor, port = key
            targets = query(node, kind=ast.InPort, attributes={'actor':actor, 'port':port})
            if len(targets) > 1:
                raise Exception("There can be only one")

            if targets:
                target = targets[0]
                link = target.parent
                for replacement in replacements:
                    new = link.clone()
                    new.inport = replacement.clone()
                    node.add_child(new)
                    replacement.parent.delete()
                link.delete()

        iips = query(node, kind=ast.InternalInPort, maxdepth=2)
        for iip in iips:
            replacement = iip.parent.outport
            targets = query(node, kind=ast.OutPort, attributes={'actor':iip.actor, 'port':iip.port})
            if targets:
                for target in targets:
                    link = target.parent
                    new = link.clone()
                    new.outport = replacement.clone()
                    node.add_child(new)
                    target.parent.delete()
                iip.parent.delete()

        # Promote ports and assignments (handled by visitors)
        non_blocks = [x for x in node.children if type(x) is not ast.Block]
        map(self.visit, non_blocks)

        # Raise promoted children to outer level
        node.parent.add_children(node.children)

        # Delete this node
        node.delete()
        if node.namespace: # FIXME: Fix this by making root node ast.Block instead of ast.Node
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

    def check_arguments(self, assignment):
        """
        Verify that all arguments are present and valid when instantiating actors.
        """
        metadata = assignment.metadata
        given_args = assignment.children
        mandatory = set(metadata['args']['mandatory'])
        optional = set(metadata['args']['optional'].keys())
        given_idents = {a.children[0].ident: a.children[0] for a in given_args}
        given_keys = [a.children[0].ident for a in given_args]
        given = set(given_keys)

        # Case 0: Duplicated arguments
        duplicates = set([x for x in given_keys if given_keys.count(x) > 1])
        for m in duplicates:
            reason = "Duplicated argument: '{}'".format(m)
            self.issue_tracker.add_error(reason, given_idents[m])


        # Case 1: Missing arguments
        missing = mandatory - given
        for m in missing:
            reason = "Missing argument: '{}'".format(m)
            self.issue_tracker.add_error(reason, assignment)

        # Case 2: Extra (unused) arguments
        unused = given - (mandatory | optional)
        for m in unused:
            reason = "Unused argument: '{}'".format(m)
            self.issue_tracker.add_error(reason, given_idents[m])

        # Case 3: Deprecation warning if optional args not explicitly given
        deprecated = optional - given
        for m in deprecated:
            reason = "Using default value for implicit parameter '{}'".format(m)
            self.issue_tracker.add_warning(reason, assignment)

        # Assing and return args dictionary
        args = {}
        for arg_node in given_args:
            arg_id, arg_val = arg_node.children
            if type(arg_val) is ast.Value:
                args[arg_id.ident] = arg_val.value
            else:
                reason = "Undefined identifier: '{}'".format(arg_val.ident)
                self.issue_tracker.add_error(reason, arg_val)
        return args


    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.Assignment)
    def visit(self, node):
        if not node.metadata:
            # No metadata => we have already generated an error, just skip
            return

        value = {}
        value['actor_type'] = node.actor_type
        value['args'] = self.check_arguments(node)
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


class CodeGen(object):
    """
    Generate code from a source file
    FIXME: Use a writer class to generate output in various formats
    """
    def __init__(self, ast_root, script_name, verbose=False, verify=True):
        super(CodeGen, self).__init__()
        self.root = ast_root
        # self.script_name = script_name
        self.printer = astprint.BracePrinter()
        self.verbose = verbose
        self.verify = verify
        self.app_info = {
            'name':script_name,
            'actors': {},
            'connections': {},
            'valid': True
        }


    def dump_tree(self, heading):
        if not self.verbose:
            return
        print "========\n{}\n========".format(heading)
        self.printer.process(self.root)


    def run(self, verbose=False):
        ast.Node._verbose_desc = verbose
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
        # Expand local components
        expander = Expander(issue_tracker)
        expander.process(self.root, self.verify)
        self.dump_tree('EXPANDED')

        ##
        # Flatten blocks
        flattener = Flatten(issue_tracker)
        flattener.process(self.root, self.app_info['name'])
        self.dump_tree('FLATTENED')

        ##
        # Resolve Constants
        rc = ReplaceConstants(issue_tracker)
        rc.process(self.root)
        self.dump_tree('RESOLVED CONSTANTS')

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
    cg = CodeGen(ast, name, verbose=False, verify=verify)
    cg.run()
    return cg.app_info, cg.issues


if __name__ == '__main__':
    from parser_regression_tests import run_issue_check
    run_issue_check(tests=['undefined_constant'], testdir='/Users/eperspe/Source/calvin-base/calvin/csparser/testscripts/issue-reporting-tests')


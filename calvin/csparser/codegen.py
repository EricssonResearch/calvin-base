import astnode as ast
import visitor
import astprint
from calvin.actorstore.store import ActorStore, GlobalStore


def _create_signature(actor_class, actor_type):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    signature_desc = {'is_primitive': True,
                      'actor_type': actor_type,
                      'inports': actor_class.inport_names,
                      'outports': actor_class.outport_names}
    return GlobalStore.actor_signature(signature_desc)

def _create_signature_for_component(actor_class, actor_type):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    print actor_class, actor_type
    signature_desc = {'is_primitive': True,
                      'actor_type': actor_type,
                      'inports': actor_class['inports'],
                      'outports': actor_class['outports']}
    return GlobalStore.actor_signature(signature_desc)


def _create_signature_for_unknown(actor_class, actor_type):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    signature_desc = {'is_primitive': True,
                      'actor_type': actor_type,
                      'inports': actor_class.inport_names,
                      'outports': actor_class.outport_names}
    return GlobalStore.actor_signature(signature_desc)


class IssueTracker(object):
    def __init__(self):
        super(IssueTracker, self).__init__()
        self.issues = []

    def _add_issue(self, issue_type, reason, node):
        issue = {
            'type': issue_type,
            'reason': reason,
        }
        issue.update(node.debug_info or {'line':0, 'col':0, 'FIXME':True})
        if issue not in self.issues:
            self.issues.append(issue)

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
    Expands a tree with components provided as a dictionary
    """
    def __init__(self, components, issue_tracker):
        self.components = components
        self.issue_tracker = issue_tracker

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
        found, is_actor, meta, _ = ActorStore().lookup(node.actor_type)
        if found and is_actor:
            # Plain actor
            return
        if found:
            compdef = meta.children[0]
            v = RestoreParents()
            v.visit(compdef)
        elif node.actor_type in self.components:
            compdef = self.components[node.actor_type].children[0]
        else:
            return
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
        # map(self.visit, new.children)
        self.visit(new)


class Flatten(object):
    """
    Flattens a block by wrapping everything in the block's namespace
    and propagating arguments before removing the block
    """
    def __init__(self, issue_tracker):
        self.stack = []
        self.constants = {}
        self.issue_tracker = issue_tracker

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Constant)
    def visit(self, node):
        key = node.children[0].ident
        value_node = node.children[1]
        self.constants[key] = value_node

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children[:])

    @visitor.when(ast.Assignment)
    def visit(self, node):
        # if node.ident is None:
        #     import pdb ; pdb.set_trace()
        self.stack.append(node.ident)
        node.ident = ':'.join(self.stack)
        self.stack.pop()
        map(self.visit, node.children[:])


    @visitor.when(ast.NamedArg)
    def visit(self, node):
        value_node = node.children[1]
        if type(value_node) is ast.Id:
            # Get value from grandparent (block)
            block = node.parent.parent
            key = value_node.ident
            if key not in block.args:
                # Check constants
                if key not in self.constants:
                    reason = "Missing symbol '{}'".format(key)
                    self.issue_tracker.add_error(reason, value_node)
                    return
                value = self.constants[key]
            else:
                value = block.args[key]
            node.replace_child(value_node, value)


    @visitor.when(ast.Port)
    def visit(self, node):
        if node.actor:
            node.actor = ':'.join(self.stack + [node.actor])
        else:
            node.actor = ':'.join(self.stack)

    @visitor.when(ast.Block)
    def visit(self, node):
        for key, value_node in node.args.iteritems():
            if type(value_node) is ast.Id:
                # Get value from parent (block)
                block = node.parent
                parent_key = value_node.ident
                if parent_key in block.args:
                    value = block.args[parent_key]
                    node.args[key] = value
                elif parent_key not in self.constants:
                    reason = "Missing symbol '{}'".format(parent_key)
                    self.issue_tracker.add_error(reason, value_node)

        if node.namespace:
            self.stack.append(node.namespace)
        # Iterate over a copy of children since we manipulate the list
        map(self.visit, node.children[:])
        if node.namespace:
            self.stack.pop()

        node.parent.add_children(node.children)
        node.delete()


class AppInfo(object):
    """docstring for AppInfo"""
    def __init__(self, script_name, root, issue_tracker, verify=True):
        super(AppInfo, self).__init__()
        self.root = root
        self.verify = verify
        self.app_info = {
            'name':script_name,
            'actors': {},
            'connections': {},
            'valid': True
        }
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
        namespace = self.app_info['name']
        key = "{}:{}".format(namespace, node.ident)
        value = {}
        # if is_actor is False, actor_class is component definition
        found, is_actor, actor_class, _ = ActorStore().lookup(node.actor_type)
        if self.verify and not found:
            self.app_info['valid'] = False
            return
        value['actor_type'] = node.actor_type
        args = {}
        for arg_node in node.children:
            if type(arg_node) is ast.NamedArg:
                arg_id, arg_val = arg_node.children
                if type(arg_val) is ast.Value:
                    args[arg_id.ident] = arg_val.value
                else:
                    reason = "Missing symbol '{}'".format(arg_val.ident)
                    self.issue_tracker.add_error(reason, arg_val)
                    continue
        value['args'] = args
        if found:
            if is_actor:
                value['signature'] = _create_signature(actor_class, node.actor_type)
            else:
                value['signature'] = _create_signature_for_component(actor_class, node.actor_type)
        else:
            # FIXME: Handle the case where the actor is unknown, but verify is FALSE
            raise Exception("Cannot compute signature of unknown actor")
            value['signature'] = _create_signature_for_unknown(node, )
        self.app_info['actors'][key] = value

    @visitor.when(ast.Link)
    def visit(self, node):
        namespace = self.app_info['name']
        key = "{}:{}.{}".format(namespace, node.outport.actor, node.outport.port)
        value = "{}:{}.{}".format(namespace, node.inport.actor, node.inport.port)
        self.app_info['connections'].setdefault(key, []).append(value)


class ResolveConstants(object):
    """docstring for ResolveConstants"""
    def __init__(self, root, issue_tracker):
        super(ResolveConstants, self).__init__()
        self.root = root
        self.defs = {}
        self.issue_tracker = issue_tracker

    def process(self):
        finder = Finder()
        consts = finder.find_all(self.root, ast.Constant)
        self.defs = {c.children[0].ident: c.children[1].value for c in consts if type(c.children[1]) is ast.Value}
        unresolved = [c for c in consts if type(c.children[1]) is ast.Id]
        done = False
        while not done:
            did_replace = False
            for c in unresolved[:]:
                key, const_key = c.children
                if const_key.ident in self.defs:
                    self.defs[key.ident] = self.defs[const_key.ident]
                    unresolved.remove(c)
                    did_replace = True
            if unresolved and not did_replace:
                for c in unresolved:
                    reason = "Undefined constant '{}'".format(const_key.ident)
                    self.issue_tracker.add_error(reason, const_key)
                return
            done = not (unresolved and did_replace)

        self.visit(self.root)

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
        if type(arg) is ast.Id and arg.ident in self.defs:
            val = ast.Value(value=self.defs[arg.ident])
            node.replace_child(arg, val)


class CodeGen(object):
    """
    Generate code from a source file
    FIXME: Use a writer class to generate output in various formats
    """
    def __init__(self, ast_root, script_name, verbose=False, verify=True):
        super(CodeGen, self).__init__()
        self.root = ast_root
        self.script_name = script_name
        self.local_components = {}
        self.printer = astprint.BracePrinter()
        self.verbose = verbose
        self.verify = verify


    def dump_tree(self, heading):
        if not self.verbose:
            return
        print "========\n{}\n========".format(heading)
        self.printer.process(self.root)

    def run(self, verbose=False):
        ast.Node._verbose_desc = verbose
        issue_tracker = IssueTracker()

        ## FIXME:
        # Check for errors
        #

        ##
        # Tree re-write
        #
        print
        self.dump_tree('ROOT')

        ##
        # Expand local components
        #
        components = self.query(self.root, kind=ast.Component, maxdepth=1)
        for c in components:
            self.local_components[c.name] = c

        expander = Expander(self.local_components, issue_tracker)
        expander.visit(self.root)
        # All component definitions can now be removed
        for comp in components:
            comp.delete()
        self.dump_tree('EXPANDED')

        ##
        # Implicit port rewrite
        rw = ImplicitPortRewrite(issue_tracker)
        rw.visit(self.root)
        self.dump_tree('Port Rewrite')

        ##
        # Flatten blocks
        flattener = Flatten(issue_tracker)
        flattener.visit(self.root)
        self.dump_tree('FLATTENED')

        ##
        # Resolve Constants
        rc = ResolveConstants(self.root, issue_tracker)
        rc.process()
        self.dump_tree('RESOLVED CONSTANTS')

        ##
        # # Resolve portmaps
        consumed = []
        iops = self.query(self.root, kind=ast.InternalOutPort)
        for iop in iops:
            ps = self.query(self.root, kind=ast.InPort, attributes={'actor':iop.actor, 'port':iop.port})
            for p in ps:
                link = p.parent
                block = link.parent
                new = link.clone()
                new.inport = iop.parent.inport.clone()
                block.add_child(new)
                consumed.append(link)

        iips = self.query(self.root, kind=ast.InternalInPort)
        for iip in iips:
            ps = self.query(self.root, kind=ast.OutPort, attributes={'actor':iip.actor, 'port':iip.port})
            for p in ps:
                p.parent.outport = iip.parent.outport.clone()

        for ip in self.query(self.root, kind=ast.InternalOutPort) + self.query(self.root, kind=ast.InternalInPort):
            ip.parent.delete()

        for x in set(consumed):
            if x.parent:
                x.delete()

        self.dump_tree('RESOLVED PORTMAPS')

        ##
        # "code" generation
        gen_app_info = AppInfo(self.script_name, self.root, issue_tracker, self.verify)
        gen_app_info.process()
        self.app_info = gen_app_info.app_info

        # import json
        # print json.dumps(self.app_info, indent=4)

        for issue in issue_tracker.issues:
            print issue

        self.issues = issue_tracker.issues

    def query(self, root, kind=None, attributes=None, maxdepth=1024):
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


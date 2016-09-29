import astnode as ast
import visitor
import astprint
from parser import calvin_parse

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

class DeployInfo(object):
    """docstring for DeployInfo"""
    def __init__(self, deploy_info, root, issue_tracker, known_actors=None):
        super(DeployInfo, self).__init__()
        self.root = root
        self.deploy_info = deploy_info
        self.issue_tracker = issue_tracker
        self.current_target = None
        self.stacked_target = None

    def process(self):
        self.visit(self.root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.RuleApply)
    def visit(self, node):
        for target in node.children:
            actor_name = target.ident
            self.deploy_info['requirements'].setdefault(actor_name, [])
            self.current_target = self.deploy_info['requirements'][actor_name]
            if not node.rule.is_leaf():
                map(self.visit, node.rule.children)
            self.current_target = None

    @visitor.when(ast.RulePredicate)
    def visit(self, node):
        if self.current_target is None:
            return
        value = {}
        if "|" in node.op.op and not self.stacked_target:
            union_group = {'op': "union_group", 'type': '+', 'requirements': []}
            self.current_target.append(union_group)
            self.stacked_target = self.current_target
            self.current_target = union_group['requirements']
        value['type'] = "-" if "~" in node.op.op else "+"
        value['op'] = node.predicate.ident
        value['kwargs'] = {a.ident.ident: a.arg.ident if isinstance(a.arg, ast.Id) else a.arg.value
                            for a in node.children}
        self.current_target.append(value)
        # FIXME We don't handle mixing union and intersection in same expression
        if node.next_sibling() is None:
            self.current_target = self.stacked_target
            self.stacked_target = None

class FoldInRuleExpression(object):
    """docstring for FoldInRuleExpression"""
    def __init__(self, issue_tracker):
        super(FoldInRuleExpression, self).__init__()
        self.issue_tracker = issue_tracker

    def process(self, root):
        self.root = root
        self.visit(root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.RuleApply)
    def visit(self, node):
        if not node.rule.is_leaf():
            map(self.visit, node.rule.children)

    @visitor.when(ast.RulePredicate)
    def visit(self, node):
        if node.type != "rule":
            return
        rules = query(self.root, kind=ast.Rule, attributes={('rule', 'ident'): node.predicate.ident})
        if not rules:
            reason = "Refers to undefined rule {}".format(node.predicate.ident)
            self.issue_tracker.add_error(reason, node)
            return
        # There should only be one rule with this ident and it should only have one child
        clone = rules[0].children[0].clone()
        node.parent.replace_child(node, clone)
        del node
        # Make sure that the clone is visited
        if not clone.is_leaf():
            map(self.visit, clone.children)

class SetOpOnFirstPredicate(object):
    """docstring for SetOpOnFirstPredicate"""
    def __init__(self, issue_tracker):
        super(SetOpOnFirstPredicate, self).__init__()
        self.issue_tracker = issue_tracker

    def process(self, root):
        self.root = root
        self.visit(root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.RuleApply)
    def visit(self, node):
        if not node.rule.is_leaf():
            map(self.visit, node.rule.children)

    @visitor.when(ast.RulePredicate)
    def visit(self, node):
        if len(node.op.op) == 0 or (len(node.op.op) == 1 and node.op.op == "~"):
            next_predicate = node.next_sibling()
            if next_predicate is None:
                # Alone in the expression set & anyway
                node.op.op = "&" + node.op.op
            else:
                # Make the op match the next predicate (besides any ~ operator)
                node.op.op = next_predicate.op.op[0] + node.op.op

class DSCodeGen(object):

    verbose = False
    verbose_nodes = False

    """
    Generate code from a deploy script file
    """
    def __init__(self, ast_root, script_name):
        super(DSCodeGen, self).__init__()
        self.root = ast_root
        self.deploy_info = {
            'requirements':{},
            'valid': True
        }
        self.dump_tree('ROOT')


    def dump_tree(self, heading):
        if not self.verbose:
            return
        ast.Node._verbose_desc = self.verbose_nodes
        printer = astprint.BracePrinter()
        print "========\n{}\n========".format(heading)
        printer.process(self.root)

    def set_op_on_first_predicates(self, issue_tracker):
        f = SetOpOnFirstPredicate(issue_tracker)
        f.process(self.root)
        self.dump_tree('Set Op On First Predicate')

    def fold_in_rule_expr(self, issue_tracker):
        f = FoldInRuleExpression(issue_tracker)
        f.process(self.root)
        self.dump_tree('Fold In Rule Expression')

    def generate_code_from_ast(self, issue_tracker):
        gen_deploy_info = DeployInfo(self.deploy_info, self.root, issue_tracker)
        gen_deploy_info.process()

    def generate_code(self, issue_tracker):
        self.set_op_on_first_predicates(issue_tracker)
        self.fold_in_rule_expr(issue_tracker)
        self.generate_code_from_ast(issue_tracker)
        self.deploy_info['valid'] = (issue_tracker.error_count == 0)


def query(root, kind=None, attributes=None, maxdepth=1024):
    finder = Finder()
    finder.find_all(root, kind, attributes=attributes, maxdepth=maxdepth)
    # print
    # print "QUERY", kind.__name__, attributes, finder.matches
    return finder.matches

def _calvin_cg(source_text, app_name):
    _, ast_root, issuetracker = calvin_parse(source_text)
    cg = DSCodeGen(ast_root, app_name)
    return cg, issuetracker

def calvin_dscodegen(source_text, app_name):
    """
    Generate deployment info from script, return deploy_info and issuetracker.

    Parameter app_name is required to provide a namespace for the application.
    """
    cg, issuetracker = _calvin_cg(source_text, app_name)
    cg.generate_code(issuetracker)
    return cg.deploy_info, issuetracker


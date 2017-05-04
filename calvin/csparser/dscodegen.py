import astnode as ast
import visitor
import astprint
from parser import calvin_parse
from codegen import query


class RuleExpander(object):
    """docstring for RuleExpander"""
    def __init__(self, root, issue_tracker):
        super(RuleExpander, self).__init__()
        self.root = root
        self.issue_tracker = issue_tracker

    def process(self):
        self.result = []
        self.visit(self.root)

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        if not node.is_leaf():
            map(self.visit, node.children)

    @visitor.when(ast.Rule)
    def visit(self, node):
        print "rule", node

    @visitor.when(ast.RulePredicate)
    def visit(self, node):
        # print "predicate", node
        pred = {c.ident.ident:c.arg.value for c in node.children}
        res = {"kwargs":pred, "type":"+", "op":node.predicate.ident}
        self.result.append(res)


class DeployInfo(object):
    """docstring for DeployInfo"""
    def __init__(self, root, issue_tracker):
        super(DeployInfo, self).__init__()
        self.root = root
        self.issue_tracker = issue_tracker

    def process(self):
        self.requirements = {}
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
        rule_name = node.rule.ident
        matched = query(self.root, kind=ast.RuleDefinition, attributes={('name', 'ident'):rule_name}, maxdepth=1024)
        # print matched, rule_name
        rule_def = matched[0]
        expr = expand_rule(rule_def.rule, self.issue_tracker)
        for c in node.children:
            self.requirements[c.ident] = expr


class DSCodeGen(object):

    verbose = True
    verbose_nodes = True

    """
    Generate code from a deploy script file
    """
    def __init__(self, ast_root, script_name):
        super(DSCodeGen, self).__init__()
        self.root = ast_root
        self.dump_tree('ROOT')

    def dump_tree(self, heading):
        if not self.verbose:
            return
        ast.Node._verbose_desc = self.verbose_nodes
        printer = astprint.BracePrinter()
        print "========\n{}\n========".format(heading)
        printer.process(self.root)


    def generate_code_from_ast(self, issue_tracker):
        gen_deploy_info = DeployInfo(self.root, issue_tracker)
        gen_deploy_info.process()
        return gen_deploy_info.requirements

    def generate_code(self, issue_tracker):
        # self.set_op_on_first_predicates(issue_tracker)
        # self.fold_in_rule_expr(issue_tracker)
        requirements = self.generate_code_from_ast(issue_tracker)
        self.deploy_info = {'requirements':requirements}
        self.deploy_info['valid'] = (issue_tracker.error_count == 0)


def expand_rule(node, issue_tracker):
    rule_expander = RuleExpander(node, issue_tracker)
    rule_expander.process()
    return rule_expander.result

def _calvin_cg(source_text, app_name):
    ast_root, issuetracker = calvin_parse(source_text)
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


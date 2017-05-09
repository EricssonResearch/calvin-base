import astnode as ast
import visitor
import astprint
from parser import calvin_parse
from codegen import query, ReplaceConstants


class ExpandRules(object):
    """docstring for ExpandRules"""
    def __init__(self, issue_tracker):
        super(ExpandRules, self).__init__()
        self.issue_tracker = issue_tracker

    def process(self, root):
        self.expanded_rules = {}
        rules = query(root, ast.RuleDefinition)
        seen = [rule.name.ident for rule in rules]
        unresolved = rules
        while True:
            self._replaced = False
            for rule in unresolved[:]:
                rule_resolved = self._expand_rule(rule)
                if rule_resolved:
                    self.expanded_rules[rule.name.ident] = rule.rule
                    unresolved.remove(rule)
            if not unresolved:
                # Done
                break
            if not self._replaced:
                # Give up
                for rule in unresolved:
                    reason = "Cannot expand rule '{}'".format(rule.name.ident)
                    self.issue_tracker.add_error(reason, rule)
                return self.expanded_rules
        # OK, final pass over RuleApply
        applies = query(root, ast.RuleApply)
        for a in applies:
            self._expand_rule(a)
        # FIXME: Run a second pass to catch errors

    def _expand_rule(self, rule):
        self._clean = True
        self.visit(rule.rule)
        return self._clean

    @visitor.on('node')
    def visit(self, node):
        pass

    @visitor.when(ast.Node)
    def visit(self, node):
        pass

    @visitor.when(ast.SetOp)
    def visit(self, node):
        self.visit(node.left)
        self.visit(node.right)

    @visitor.when(ast.UnarySetOp)
    def visit(self, node):
        self.visit(node.rule)

    @visitor.when(ast.Id)
    def visit(self, node):
        self._clean = False
        if node.ident in self.expanded_rules:
            node.parent.replace_child(node, self.expanded_rules[node.ident].clone())
            self._replaced = True


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
        rule = self.visit(node.rule)
        for t in node.targets:
            self.requirements[t.ident] = rule

    @visitor.when(ast.RulePredicate)
    def visit(self, node):
        pred = {
            "predicate":node.predicate.ident,
            "kwargs":{arg.ident.ident:arg.arg.value for arg in node.args}
        }
        return pred

    @visitor.when(ast.SetOp)
    def visit(self, node):
        rule = {
            "operator":node.op,
            "operands":[self.visit(node.left), self.visit(node.right)]
        }
        return rule

    @visitor.when(ast.UnarySetOp)
    def visit(self, node):
        rule = {
            "operator":node.op,
            "operand":self.visit(node.rule)
        }
        return rule


class Backport(object):
    """docstring for Backport"""
    def __init__(self, issuetracker):
        super(Backport, self).__init__()
        self.issuetracker = issuetracker

    def transform(self, requirements):
        for actor, rule in requirements.iteritems():
            try:
                new_rule = self.mangle(rule)
                requirements[actor] = new_rule if type(new_rule) is list else [new_rule]
            except Exception as e:
                self.issuetracker.add_error("Cannot mangle rule for actor '{}'".format(actor), info={'line':0, 'col':0})
        return requirements

    def mangle(self, rule):

        def is_predicate(rule):
            return 'predicate' in rule

        def is_intersection(rule):
            return 'operands' in rule and rule['operator'] == '&'

        def is_union(rule):
            return 'operands' in rule and rule['operator'] == '|'

        def is_unary_not(rule):
            return 'operand' in rule and rule['operator'] == '~'

        if is_predicate(rule):
            new_rule = {
                "op": rule["predicate"],
                "kwargs": rule["kwargs"],
                "type": "+"
            }
            return new_rule

        if is_intersection(rule):
            try:
                left = self.mangle(rule['operands'][0])
                right = self.mangle(rule['operands'][1])
                new_rule = (left if type(left) is list else [left]) + (right if type(right) is list else [right])
            except Exception as e:
                print "REASON:", e
                raise Exception("EXCEPTION (&)\n{}\n{}".format(left, right))
            return new_rule

        if is_union(rule):
            left = self.mangle(rule['operands'][0])
            right = self.mangle(rule['operands'][1])
            ll, rd = False, False
            try:
                if type(left) is dict and 'requirements' in left:
                    left = left['requirements']
                    ll = True
                if type(left) is dict:
                    left.pop('type', None)
                if type(right) is dict and 'requirements' in right:
                    right = right['requirements']
                if type(right) is dict:
                    right.pop('type', None)
                    rd = True
                if  ll and rd:
                    reqs = left + [right]
                else:
                    reqs = [left, right]
                new_rule = {
                    "op": "union_group",
                    "requirements":reqs,
                    "type": "+"
                }
            except Exception as e:
                raise Exception("EXCEPTION (|)\n{}\n{}".format(left, right))
            return new_rule


        if is_unary_not(rule):
            new_rule = {
                "op": rule["operand"]["predicate"],
                "kwargs": rule["operand"]["kwargs"],
                "type": "-"
            }
            return new_rule

        return None


class DSCodeGen(object):

    verbose = False
    verbose_nodes = False

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
        rc = ReplaceConstants(issue_tracker)
        rc.process(self.root)
        self.dump_tree('RESOLVED CONSTANTS')


        er = ExpandRules(issue_tracker)
        er.process(self.root)
        self.dump_tree('EXPANDED')

        gen_deploy_info = DeployInfo(self.root, issue_tracker)
        gen_deploy_info.process()

        bp = Backport(issue_tracker)
        return bp.transform(gen_deploy_info.requirements)

    def generate_code(self, issue_tracker):
        requirements = self.generate_code_from_ast(issue_tracker)
        self.deploy_info = {'requirements':requirements}
        self.deploy_info['valid'] = (issue_tracker.error_count == 0)


def _calvin_cg(source_text, app_name):
    global global_root
    ast_root, issuetracker = calvin_parse(source_text)
    global_root = ast_root
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

if __name__ == '__main__':
    from inspect import cleandoc
    import json

    script = 'inline'
    source_text = \
    """
    snk : io.Print()
    1 > snk.token

    rule r1 : a() & b() & c() & d() & e()
    rule r2 : a() | b() | c() | d() | e()
    rule r3 : a() | b() & c() & d()
    rule r4 : a() & b() | c() & d()
    rule r5 : a() & b() | c() & d() | e() | f()

    apply snk : r2

    """
    source_text = cleandoc(source_text)
    print source_text
    print
    ai, it = calvin_dscodegen(source_text, script)
    if it.issue_count == 0:
        print "No issues"
    for i in it.formatted_issues(custom_format="{type!c}: {reason} {filename}:{line}:{col}", filename=script):
        print i
    print "-------------"
    print json.dumps(ai, indent=4)


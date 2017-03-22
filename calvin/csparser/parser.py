# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import ply.lex as lex
import ply.yacc as yacc
import calvin_rules
from calvin_rules import tokens as calvin_tokens
import astnode as ast
from calvin.utilities.issuetracker import IssueTracker


class CalvinParser(object):
    """docstring for CalvinParser"""
    def __init__(self, lexer=None):
        super(CalvinParser, self).__init__()
        if lexer:
            self.lexer = lexer
        else:
            self.lexer = lex.lex(module=calvin_rules, debug=False, optimize=False)
        # Since the parse may be called from other scripts, we want to have control
        # over where parse tables (and parser.out log) will be put if the tables
        # have to be recreated
        this_file = os.path.realpath(__file__)
        containing_dir = os.path.dirname(this_file)
        self.parser = yacc.yacc(module=self, debug=False, optimize=True, outputdir=containing_dir)

    tokens = calvin_tokens

    def p_script(self, p):
        """script : opt_constdefs opt_compdefs opt_program"""
        s = ast.Node()
        s.add_children(p[1] + p[2] + p[3][0])
        root = ast.Node()
        root.add_child(s.clone())
        d = ast.Node()
        d.add_children(p[1] + p[3][1])
        root.add_child(d)
        p[0] = root

    def p_opt_constdefs(self, p):
        """opt_constdefs :
                         | constdefs"""
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = []

    def p_constdefs(self, p):
        """constdefs : constdefs constdef
                     | constdef"""
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1]]


    def p_constdef(self, p):
        """constdef : DEFINE identifier EQ argument"""
        constdef = ast.Constant(ident=p[2], arg=p[4], debug_info=self.debug_info(p, 1))
        p[0] = constdef


    def p_opt_compdefs(self, p):
        """opt_compdefs :
                         | compdefs"""
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = []

    def p_compdefs(self, p):
        """compdefs : compdefs compdef
                    | compdef"""
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1]]


    def p_compdef(self, p):
        """compdef : COMPONENT qualified_name LPAREN identifiers RPAREN identifiers RARROW identifiers LBRACE docstring comp_statements RBRACE"""
        p[0] = ast.Component(name=p[2], arg_names=p[4], inports=p[6], outports=p[8], docstring=p[10], program=p[11], debug_info=self.debug_info(p, 1))


    def p_docstring(self, p):
        """docstring :
                     | DOCSTRING """
        if len(p) == 1:
            p[0] = "Someone(TM) should write some documentation for this component."
        else:
            p[0] = p[1]

    def p_comp_statements(self, p):
        """comp_statements : comp_statements comp_statement
                           | comp_statement"""
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[2]]

    def p_comp_statement(self, p):
        """comp_statement : assignment
                          | port_property
                          | internal_port_property
                          | link"""
        p[0] = p[1]

    def p_opt_program(self, p):
        """opt_program :
                       | program"""
        if len(p) == 1:
            p[0] = [[],[]]
        else:
            p[0] = [
                [ast.Block(program=p[1][0], namespace='__scriptname__', debug_info=self.debug_info(p, 1))],
                p[1][1]
            ]

    def p_program(self, p):
        """program : program statement
                   | statement """
        if len(p) == 2:
            if type(p[1]) in [ast.Group, ast.Rule, ast.RuleApply]:
                p[0] = [[], [p[1]]]
            else:
                p[0] = [[p[1]], []]
        else:
            if type(p[2]) in [ast.Group, ast.Rule, ast.RuleApply]:
                p[0] = [p[1][0], p[1][1] + [p[2]]]
            else:
                p[0] = [p[1][0] + [p[2]], p[1][1]]

    def p_statement(self, p):
        """statement : assignment
                     | port_property
                     | link
                     | rule
                     | group
                     | apply"""
        p[0] = p[1]

    def p_group(self, p):
        """group : GROUP identifier COLON ident_list"""
        p[0] = ast.Group(group=p[2], members=p[4], debug_info=self.debug_info(p, 1))

    def p_ident_list(self, p):
        """ident_list :
                       | ident_list identifier COMMA
                       | ident_list identifier"""
        if len(p) > 2:
            p[1].append(p[2])
        p[0] = p[1] if len(p) > 1 else []

    def p_rule(self, p):
        """rule : RULE identifier COLON expression"""
        p[0] = ast.Rule(rule=p[2], expression=p[4], debug_info=self.debug_info(p, 1))

    def p_expression(self, p):
        """expression : expression predicate
                      | first_predicate"""
        if len(p) > 2:
            p[1].add_child(p[2])
            p[0] = p[1]
        else:
            p[0] = ast.RuleExpression(first_predicate=p[1])

    def p_first_predicate(self, p):
        """first_predicate : identifier
                           | NOT identifier
                           | identifier LPAREN named_args RPAREN
                           | NOT identifier LPAREN named_args RPAREN"""
        # print p[1], p[3], self.debug_info(p, 1)
        if len(p) == 2:
            # identifier
            p[0] = ast.RulePredicate(predicate=p[1], type="rule", debug_info=self.debug_info(p, 1))
        elif len(p) == 3:
            # NOT identifier
            p[0] = ast.RulePredicate(predicate=p[2], type="rule", op=ast.RuleSetOp(op="~"), debug_info=self.debug_info(p, 1))
        elif len(p) == 5:
            # identifier LPAREN named_args RPAREN
            p[0] = ast.RulePredicate(predicate=p[1], type="constraint", args=p[3], debug_info=self.debug_info(p, 1))
        else:
            # NOT identifier LPAREN named_args RPAREN
            p[0] = ast.RulePredicate(predicate=p[2], type="constraint", op=ast.RuleSetOp(op="~"), args=p[4], debug_info=self.debug_info(p, 1))

    def p_predicate(self, p):
        """predicate : setop identifier
                     | setop identifier LPAREN named_args RPAREN"""
        # print p[1], p[3], self.debug_info(p, 1)
        if len(p) == 3:
            # setop identifier
            p[0] = ast.RulePredicate(predicate=p[2], type="rule", op=p[1], debug_info=self.debug_info(p, 1))
        else:
            # setop identifier LPAREN named_args RPAREN
            p[0] = ast.RulePredicate(predicate=p[2], type="constraint", op=p[1], args=p[4], debug_info=self.debug_info(p, 1))

    def p_setop(self, p):
        """setop : AND
                 | OR
                 | AND NOT
                 | OR NOT"""
        #print p[1], self.debug_info(p, 1)
        if len(p) == 2:
            p[0] = ast.RuleSetOp(op=p[1])
        else:
            p[0] = ast.RuleSetOp(op=p[1] + p[2])

    def p_apply(self, p):
        """apply : APPLY ident_list COLON expression
                 | APPLY STAR ident_list COLON expression"""
        if len(p) == 5:
            # print p[2], p[4], self.debug_info(p, 1)
            p[0] = ast.RuleApply(optional=False, targets=p[2], rule=p[4], debug_info=self.debug_info(p,1))
        else:
            # print p[2], p[3], p[5], self.debug_info(p, 1)
            p[0] = ast.RuleApply(optional=True, targets=p[3], rule=p[5], debug_info=self.debug_info(p,1))

    def p_assignment(self, p):
        """assignment : IDENTIFIER COLON qualified_name LPAREN named_args RPAREN"""
        p[0] = ast.Assignment(ident=p[1], actor_type=p[3], args=p[5], debug_info=self.debug_info(p, 1))


    def p_opt_direction(self, p):
        """opt_direction :
                         | LBRACK IDENTIFIER RBRACK"""
        if len(p) == 1:
            p[0] = None
        else:
            if p[2] not in ['in', 'out']:
                info = {
                    'line': p.lineno(2),
                    'col': self._find_column(p.lexpos(2))
                }
                self.issuetracker.add_error('Invalid direction ({}).'.format(p[2]), info)
            p[0] = p[2]


    def p_port_property(self, p):
        """port_property : IDENTIFIER DOT IDENTIFIER opt_direction LPAREN named_args RPAREN"""
        p[0] = ast.PortProperty(actor=p[1], port=p[3], direction=p[4], args=p[6], debug_info=self.debug_info(p, 1))


    def p_internal_port_property(self, p):
        """internal_port_property : DOT IDENTIFIER opt_direction LPAREN named_args RPAREN"""
        p[0] = ast.PortProperty(actor=None, port=p[2], direction=p[3], args=p[5], debug_info=self.debug_info(p, 1))


    def p_link(self, p):
        """link : outport GT port
                | outport GT portlist
                | outport GT void
                | implicit_port GT port
                | implicit_port GT portlist
                | internal_outport GT inport
                | internal_outport GT inportlist
                | void GT inport
                | void GT inportlist
        """
        p[0] = ast.Link(outport=p[1], inport=p[3], debug_info=self.debug_info(p, 1))

    def p_link_error(self, p):
        """link : internal_outport GT internal_inport"""
        info = {
            'line': p.lineno(2),
            'col': self._find_column(p.lexpos(2))
        }
        self.issuetracker.add_error('Component inport connected directly to outport.', info)

    # def p_portmap(self, p):
    #     """portmap : port GT internal_port
    #                | internal_port GT port"""
    #     p[0] = ast.Portmap(p[1], p[3])

    def p_void(self, p):
        """void : VOIDPORT"""
        p[0] = ast.Void(debug_info=self.debug_info(p, 1))

    def p_portlist(self, p):
        """portlist : portlist COMMA port
                    | port COMMA port"""
        if type(p[1]) is ast.PortList:
            p[1].add_child(p[3])
            p[0] = p[1]
        else:
            p[0] = ast.PortList()
            p[0].add_child(p[1])
            p[0].add_child(p[3])

    def p_inportlist(self, p):
        """inportlist : inportlist COMMA inport
                    | inport COMMA inport"""
        if type(p[1]) is ast.PortList:
            p[1].add_child(p[3])
            p[0] = p[1]
        else:
            p[0] = ast.PortList()
            p[0].add_child(p[1])
            p[0].add_child(p[3])


    def p_port(self, p):
        """port : inport
                | internal_inport
                | transformed_inport"""
        p[0]=p[1]

    def p_transformed_inport(self, p):
        """transformed_inport : SLASH argument SLASH port
                              | SLASH COLON identifier argument SLASH port"""
        if len(p) > 5:
            p[0] = ast.TransformedPort(port=p[6], value=p[4], label=p[3], debug_info=self.debug_info(p, 4))
        else:
            p[0] = ast.TransformedPort(port=p[4], value=p[2], debug_info=self.debug_info(p, 4))

    def p_implicit_port(self, p):
        """implicit_port : argument
                         | COLON identifier argument"""
        if len(p) > 2:
            p[0] = ast.ImplicitPort(arg=p[3], label=p[2], debug_info=self.debug_info(p, 1))
        else:
            p[0] = ast.ImplicitPort(arg=p[1], debug_info=self.debug_info(p, 1))


    def p_inport(self, p):
        """inport : IDENTIFIER DOT IDENTIFIER"""
        p[0] = ast.InPort(actor=p[1], port=p[3], debug_info=self.debug_info(p, 1))

    def p_outport(self, p):
        """outport : IDENTIFIER DOT IDENTIFIER"""
        p[0] = ast.OutPort(actor=p[1], port=p[3], debug_info=self.debug_info(p, 1))


    def p_internal_inport(self, p):
        """internal_inport : DOT IDENTIFIER"""
        p[0] = ast.InternalInPort(port=p[2], debug_info=self.debug_info(p, 1))


    def p_internal_outport(self, p):
        """internal_outport : DOT IDENTIFIER"""
        p[0] = ast.InternalOutPort(port=p[2], debug_info=self.debug_info(p, 1))


    def p_named_args(self, p):
        """named_args :
                      | named_args named_arg COMMA
                      | named_args named_arg"""
        if len(p) > 1:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []


    def p_named_arg(self, p):
        """named_arg : identifier EQ argument"""
        p[0] = ast.NamedArg(ident=p[1], arg=p[3], debug_info=self.debug_info(p, 1))


    def p_argument(self, p):
        """argument : value
                    | identifier"""
        p[0] = p[1]

    def p_identifier(self, p):
        """identifier : IDENTIFIER"""
        p[0] = ast.Id(ident=p[1], debug_info=self.debug_info(p, 1))

    # Concatenation of strings separated only by whitespace
    # since linebreaks are not allowed inside strings
    def p_string(self, p):
        """string : STRING
                  | string STRING"""
        p[0] = p[1] if len(p) == 2 else p[1] + p[2]

    def p_value(self, p):
        """value : dictionary
                 | array
                 | bool
                 | null
                 | NUMBER
                 | string
                 | portref"""
        p[0] = ast.Value(value=p[1], debug_info=self.debug_info(p, 1))


    def p_portref(self, p):
        """portref : AND IDENTIFIER DOT IDENTIFIER opt_direction
                   | AND DOT IDENTIFIER opt_direction """
        if len(p) == 6:
            _, _, actor, _, port, direction = p[:]
            ref = ast.PortRef(actor=actor, port=port, direction=direction, debug_info=self.debug_info(p, 1))
        else:
            _, _, _, port, direction = p[:]
            ref = ast.InternalPortRef(port=port, direction=direction, debug_info=self.debug_info(p, 1))
        p[0] = ref


    def p_bool(self, p):
        """bool : TRUE
                | FALSE"""
        p[0] = bool(p.slice[1].type == 'TRUE')


    def p_null(self, p):
        """null : NULL"""
        p[0] = None


    def p_dictionary(self, p):
        """dictionary : LBRACE members RBRACE"""
        p[0] = dict(p[2])


    def p_members(self, p):
        """members :
                    | members member COMMA
                    | members member"""
        if len(p) == 1:
            p[0] = list()
        else:
            p[1].append(p[2])
            p[0] = p[1]


    def p_member(self, p):
        """member : string COLON value"""
        p[0] = (p[1], p[3].value)


    def p_values(self, p):
        """values :
                    | values value COMMA
                    | values value"""
        if len(p) == 1:
            p[0] = list()
        else:
            p[1].append(p[2].value)
            p[0] = p[1]


    def p_array(self, p):
        """array :  LBRACK values RBRACK"""
        p[0] = p[2]


    def p_identifiers(self, p):
        """identifiers :
                       | identifiers IDENTIFIER COMMA
                       | identifiers IDENTIFIER"""
        if len(p) > 2:
            p[1].append(p[2])
        p[0] = p[1] if len(p) > 1 else []


    def p_qualified_name(self, p):
        """qualified_name : qualified_name DOT IDENTIFIER
                          | IDENTIFIER"""
        if len(p) == 4:
            # Concatenate name
            p[0] = p[1] + p[2] + p[3]
        else:
            p[0] = p[1]


    # Error rule for syntax errors
    def p_error(self, token):
        if not token:
            # Unexpected EOF
            lines = self.source_text.splitlines()
            info = {
                'line': len(lines),
                'col': len(lines[-1])
            }
            self.issuetracker.add_error('Unexpected end of file.', info)
            return

        info = {
            'line': token.lineno,
            'col': self._find_column(token.lexpos)
        }
        self.issuetracker.add_error('Syntax error.', info)


    def _find_column(self, lexpos):
        last_cr = self.source_text.rfind('\n', 0, lexpos)
        # rfind returns -1 if not found, i.e. on 1st line,
        # which is exactly what we need in that case...
        column = lexpos - last_cr
        return column


    def debug_info(self, p, n):
        info = {
            'line': p.lineno(n),
            'col': self._find_column(p.lexpos(n))
        }
        return info


    def parse(self, source_text, logger=None):
        # return ir (AST) and issuetracker
        self.issuetracker = IssueTracker()
        self.source_text = source_text
        root = None

        try:
            root = self.parser.parse(source_text, debug=logger)
        except SyntaxError as e:
            self.issuetracker.add_error(e.text, {'line':e.lineno, 'col':e.offset})
        finally:
            ir, deploy_ir = root.children if root else (ast.Node(), ast.Node())

        return ir, deploy_ir, self.issuetracker


# FIXME: [PP] Optionally supply an IssueTracker
def calvin_parse(source_text):
    """Parse source text and return ir (AST) and issuetracker."""
    parser = CalvinParser()
    return parser.parse(source_text)


if __name__ == '__main__':
    import os
    import sys
    import json
    import astprint
    import logging

    logging.basicConfig(
        level = logging.DEBUG,
        filename = "{}/parselog.txt".format(os.path.dirname(os.path.realpath(__file__))),
        filemode = "w",
        format = "%(filename)10s:%(lineno)4d:%(message)s"
    )

    if len(sys.argv) < 2:
        log = logging.getLogger()
        script = 'inline'
        source_text = \
'''
define NODE1={"organization": "org.testexample", "name": "testNode1"}
define NODE2={"organization": "org.testexample", "name": "testNode2"}


define ARG=-1

component Foo(arg) in -> out {
  """
  Foo(arg)
  Documentation please
  """

  init : flow.Init(data=arg)

  .in > init.in
  init.out > .out
}

src : Foo(arg=ARG)
delay : std.ClassicDelay()
print : io.Print()

src.out > print.token
src.out > delay.token
delay.token > src.in

src.out(routing="round-robin")
delay.token[in](routing="round-robin")

# define rules
rule src_rule: node_attr(node_spec=NODE1)

rule dst_rule: node_attr(node_spec=NODE1) | node_attr(node_spec={"name": "testNode2"})
rule src_rule: node_attr(node_spec=NODE1) | node_attr(node_spec=NODE2) &~ current()
rule combined_rule: dst_rule & src_rule | current()

# define a group
group group_name: actor, some_group

# apply rules, '*' indicates optional rule
apply actor: some_rule
apply* actor, actor: some_rule
apply actor, actor: some_rule | node_attr(node_spec=NODE1) &~ current()

'''
    else:
        script = sys.argv[1]
        script = os.path.expanduser(script)
        try:
            with open(script, 'r') as source:
                source_text = source.read()
        except:
            print "Error: Could not read file: '%s'" % script
            sys.exit(1)

    parser = CalvinParser()
    ir, deploy_ir, it = parser.parse(source_text, logger=log)
    if it.issue_count == 0:
        print "No issues"
    for i in it.formatted_issues(custom_format="{type!c}: {reason} {filename}:{line}:{col}", filename=script):
        print i

    print "CalvinScript:"
    bp = astprint.BracePrinter()
    bp.visit(ir)
    print
    print "DeployScript:"
    bp = astprint.BracePrinter()
    bp.visit(deploy_ir)



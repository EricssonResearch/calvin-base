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
from astprint import BraceFormatter
from calvin.utilities.issuetracker import IssueTracker

_parser_instance = None
def get_parser():
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = CalvinParser()
    return _parser_instance


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
        self.parser = yacc.yacc(module=self, debug=True, optimize=False, outputdir=containing_dir)

    tokens = calvin_tokens

    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('right', 'UNOT'),
    )

    def p_script(self, p):
        """script : opt_constdefs opt_compdefs opt_program"""
        root = ast.Node()
        root.add_children(p[1] + p[2] + p[3])
        p[0] = root

    def p_empty(self, p):
        """empty : """
        pass

    def p_opt_constdefs(self, p):
        """opt_constdefs : constdefs
                         | empty"""

        p[0] = p[1] or []

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
        """opt_compdefs : compdefs
                        | empty"""
        p[0] = p[1] or []

    def p_compdefs(self, p):
        """compdefs : compdefs compdef
                    | compdef"""
        if len(p) == 3:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1]]


    def p_compdef(self, p):
        """compdef : COMPONENT qualified_name LPAREN opt_argnames RPAREN opt_argnames RARROW opt_argnames LBRACE docstring comp_statements RBRACE"""
        p[0] = ast.Component(name=p[2], arg_names=p[4], inports=p[6], outports=p[8], docstring=p[10], program=p[11], debug_info=self.debug_info(p, 1))


    def p_docstring(self, p):
        """docstring : DOCSTRING
                     | empty"""
        p[0] = p[1] or "Someone(TM) should write some documentation for this component."

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
        """opt_program : program
                       | empty"""
        p[0] = [] if p[1] is None else [ast.Block(program=p[1], namespace='__scriptname__', debug_info=self.debug_info(p, 1))]

    def p_program(self, p):
        """program : program statement
                   | statement """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[2]]

    def p_statement(self, p):
        """statement : assignment
                     | port_property
                     | link
                     | define_rule
                     | group
                     | apply"""
        p[0] = p[1]


    def p_assignment(self, p):
        """assignment : IDENTIFIER COLON qualified_name LPAREN named_args RPAREN"""
        p[0] = ast.Assignment(ident=p[1], actor_type=p[3], args=p[5], debug_info=self.debug_info(p, 1))


    def p_opt_direction(self, p):
        """opt_direction : LBRACK IDENTIFIER RBRACK
                         | empty"""
        if p[1] is None:
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
        """port_property : qualified_port opt_direction LPAREN named_args RPAREN"""
        _, (actor, port), direction, _, args, _ = p[:]
        p[0] = ast.PortProperty(actor=actor, port=port, direction=direction, args=args, debug_info=self.debug_info(p, 3))


    def p_internal_port_property(self, p):
        """internal_port_property : unqualified_port opt_direction LPAREN named_args RPAREN"""
        _, (actor, port), direction, _, args, _ = p[:]
        p[0] = ast.PortProperty(actor=actor, port=port, direction=direction, args=args, debug_info=self.debug_info(p, 3))


    def p_link_error(self, p):
        """link : void GT void"""
        info = {
            'line': p.lineno(2),
            'col': self._find_column(p.lexpos(2))
        }
        self.issuetracker.add_error('Pointless construct.', info)

    def p_link(self, p):
        """link : real_outport GT void
                | void GT real_inport_list
                | real_outport GT inport_list
                | implicit_outport GT inport_list
                | internal_outport GT inport_list"""
        p[0] = ast.Link(outport=p[1], inport=p[3], debug_info=self.debug_info(p, 1))


    def p_void(self, p):
        """void : VOIDPORT"""
        p[0] = ast.Void(debug_info=self.debug_info(p, 1))

    def p_inport_list(self, p):
        """inport_list : inport_list COMMA inport
                       | inport"""
        if len(p) == 2:
            p[0] = ast.PortList()
            p[0].add_child(p[1])
        else:
            p[1].add_child(p[3])
            p[0] = p[1]


    def p_real_inport_list(self, p):
        """real_inport_list : inport_list COMMA real_inport
                       | real_inport"""
        if len(p) == 2:
            p[0] = ast.PortList()
            p[0].add_child(p[1])
        else:
            p[1].add_child(p[3])
            p[0] = p[1]

    def p_inport(self, p):
        """inport : real_or_internal_inport
                  | transformed_inport"""
        p[0]=p[1]

    def p_transformed_inport(self, p):
        """transformed_inport : port_transform real_or_internal_inport"""
        arg, label = p[1]
        p[0] = ast.TransformedPort(port=p[2], value=arg, label=label, debug_info=self.debug_info(p, 2))

    def p_implicit_outport(self, p):
        """implicit_outport : argument
                            | label argument"""
        arg, label = (p[1], None) if len(p) == 2 else (p[2], p[1])
        p[0] = ast.ImplicitPort(arg=arg, label=label, debug_info=self.debug_info(p, 1))

    def p_real_or_internal_inport(self, p):
        """real_or_internal_inport : real_inport
                                   | internal_inport"""
        p[0] = p[1]

    def p_opt_tag(self, p):
        """opt_tag : AT tag_value
                   | empty"""
        p[0] = p[1] if p[1] is None else p[2]

    def p_tag_value(self, p):
        """tag_value : NUMBER
                     | STRING"""
        # FIXME: Verify that number is positive integer
        p[0] = p[1]

    def p_real_inport(self, p):
        """real_inport : opt_tag qualified_port"""
        _, tag, (actor, port) = p[:]
        p[0] = ast.InPort(actor=actor, port=port, tag=tag, debug_info=self.debug_info(p, 2))

    def p_real_outport(self, p):
        """real_outport : qualified_port"""
        actor, port = p[1]
        p[0] = ast.OutPort(actor=actor, port=port, debug_info=self.debug_info(p, 1))


    def p_internal_inport(self, p):
        """internal_inport : unqualified_port"""
        _, port = p[1]
        p[0] = ast.InternalInPort(port=port, debug_info=self.debug_info(p, 1))


    def p_internal_outport(self, p):
        """internal_outport : unqualified_port"""
        _, port = p[1]
        p[0] = ast.InternalOutPort(port=port, debug_info=self.debug_info(p, 1))


    def p_port_transform(self, p):
        """port_transform : SLASH argument SLASH
                          | SLASH label argument SLASH"""
        p[0] = (p[2], None) if len(p) == 4 else (p[3], p[2])

    def p_qualified_port(self, p):
        """qualified_port : IDENTIFIER DOT IDENTIFIER"""
        p[0] = (p[1], p[3])

    def p_unqualified_port(self, p):
        """unqualified_port : DOT IDENTIFIER"""
        p[0] = (None, p[2])


    def p_label(self, p):
        """label : COLON identifier"""
        p[0] = p[2]

    def p_named_args(self, p):
        """named_args : named_args named_arg COMMA
                      | named_args named_arg
                      | empty"""
        p[0] = p[1] + [p[2]] if p[1] is not None else []

    def p_named_arg(self, p):
        """named_arg : identifier EQ argument"""
        p[0] = ast.NamedArg(ident=p[1], arg=p[3], debug_info=self.debug_info(p, 1))


    def p_argument(self, p):
        """argument : value
                    | identifier"""
        p[0] = p[1]


    def p_opt_argnames(self, p):
        """opt_argnames : argnames
                           | empty"""
        p[0] = p[1] if p[1] is not None else []


    def p_argnames(self, p):
        """argnames : argnames COMMA IDENTIFIER
                    | IDENTIFIER"""
        p[0] = [p[1]] if len(p) == 2 else p[1]+ [p[3]]


    # def p_opt_identifiers(self, p):
    #     """opt_identifiers : identifiers
    #                        | empty"""
    #     p[0] = [p[1]] if p[1] is not None else []

    def p_identifiers(self, p):
        """identifiers : identifiers COMMA identifier
                       | identifier"""
        p[0] = [p[1]] if len(p) == 2 else p[1]+ [p[3]]


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
                 | string"""
        p[0] = ast.Value(value=p[1], debug_info=self.debug_info(p, 1))


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
        """members : members member COMMA
                   | members member
                   | empty"""
        p[0] = p[1] + [p[2]] if p[1] is not None else []

    def p_member(self, p):
        """member : string COLON value"""
        p[0] = (p[1], p[3].value)


    def p_values(self, p):
        """values : values value COMMA
                  | values value
                  | empty"""
        p[0] = p[1] + [p[2].value] if p[1] is not None else []

    def p_array(self, p):
        """array :  LBRACK values RBRACK"""
        p[0] = p[2]

    def p_qualified_name(self, p):
        """qualified_name : qualified_name DOT IDENTIFIER
                          | IDENTIFIER"""
        if len(p) == 4:
            # Concatenate name
            p[0] = p[1] + p[2] + p[3]
        else:
            p[0] = p[1]

    ########################################################################################
    #
    # Deploy rules
    #
    #   defrule : RULE identifier COLON rule
    #
    #   rule : rule op rule
    #        | LPAREN rule RPAREN
    #        | UNOT rule
    #        | predicate
    #        | identifier
    #
    #   op : AND
    #      | OR
    #
    #   predicate : identifier LPAREN named_arguments RPAREN
    #
    #   apply : APPLY identifier_list COLON rule
    #   (or possibly)
    #   apply : APPLY rule COLON identifier_list
    #
    ########################################################################################

    def p_define_rule(self, p):
        """define_rule : RULE identifier COLON rule"""
        p[0] = ast.RuleDefinition(name=p[2], rule=p[4], debug_info=self.debug_info(p, 1))

    def p_combine_rule(self, p):
        """rule : rule AND rule
                | rule OR rule"""
        p[0] = ast.SetOp(left=p[1], op=p[2], right=p[3], debug_info=self.debug_info(p, 1))

    def p_negate_rule(self, p):
        """rule : UNOT rule"""
        p[0] = ast.UnarySetOp(rule=p[2], op=p[1], debug_info=self.debug_info(p, 1))

    def p_subrule(self, p):
        """rule : LPAREN rule RPAREN"""
        p[0] = p[2]

    def p_rule(self, p):
        """rule : identifier
                | predicate"""
        p[0] = p[1]

    def p_predicate(self, p):
        """predicate : identifier LPAREN named_args RPAREN"""
        p[0] = ast.RulePredicate(predicate=p[1], args=p[3], debug_info=self.debug_info(p, 1))

    def p_apply(self, p):
        """apply : APPLY identifiers COLON rule"""
        # or possibly
        # """apply : APPLY rule COLON identifiers"""
        p[0] = ast.RuleApply(optional=False, targets=p[2], rule=p[4], debug_info=self.debug_info(p,1))

    def p_group(self, p):
        """group : GROUP identifier COLON identifiers"""
        p[0] = ast.Group(group=p[2], members=p[4], debug_info=self.debug_info(p, 1))


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
            ir = root or ast.Node()

        return ir, self.issuetracker

# FIXME: [PP] Optionally supply an IssueTracker
def calvin_parse(source_text):
    """Parse source text and return ir (AST) and issuetracker."""
    parser = get_parser()
    return parser.parse(source_text)

def printable_ir(source_text):
    ir, it = calvin_parse(source_text)
    bf = BraceFormatter()
    ir_str = bf.process(ir)
    return ir_str, it


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
component Foo(a, b, c)  -> out {
        foo : std.Identity()
        .in > foo.token
        foo.token > .out
}

src : std.CountTimer()
snk : test.Sink(store_tokens=1, quiet=1)
src.integer > snk.token

rule simple : node_attr_match(index=["node_name", {"organization": "com.ericsson"}])

apply src, snk : simple

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

    parser = get_parser()
    ir, it = parser.parse(source_text, logger=log)
    if it.issue_count == 0:
        print "No issues"
    for i in it.formatted_issues(custom_format="{type!c}: {reason} {filename}:{line}:{col}", filename=script):
        print i

    print "CalvinScript:"
    bp = astprint.BracePrinter()
    bp.process(ir)
    # print
    # print "DeployScript:"
    # bp = astprint.BracePrinter()
    # bp.process(deploy_ir)



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
            self.lexer = lex.lex(module=calvin_rules, debug=False, optimize=True)
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
        s.add_children(p[1] + p[2] + p[3])
        p[0] = s


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
        """compdef : COMPONENT qualified_name LPAREN identifiers RPAREN identifiers RARROW identifiers LBRACE docstring program RBRACE"""
        p[0] = ast.Component(name=p[2], arg_names=p[4], inports=p[6], outports=p[8], docstring=p[10], program=p[11], debug_info=self.debug_info(p, 1))


    def p_docstring(self, p):
        """docstring :
                     | DOCSTRING """
        if len(p) == 1:
            p[0] = "Someone(TM) should write some documentation for this component."
        else:
            p[0] = p[1]


    def p_opt_program(self, p):
        """opt_program :
                       | program"""
        if len(p) == 1:
            p[0] = []
        else:
            p[0] = [ast.Block(program=p[1], namespace='__scriptname__', debug_info=self.debug_info(p, 1))]


    def p_program(self, p):
        """program : program statement
                   | statement """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = p[1] + [p[2]]


    def p_statement(self, p):
        """statement : assignment
                     | link"""
        p[0] = p[1]


    def p_assignment(self, p):
        """assignment : IDENTIFIER COLON qualified_name LPAREN named_args RPAREN"""
        p[0] = ast.Assignment(ident=p[1], actor_type=p[3], args=p[5], debug_info=self.debug_info(p, 1))


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
        """void : VOID"""
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
                | internal_inport"""
        p[0]=p[1]

    def p_implicit_port(self, p):
        """implicit_port : argument"""
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


    def p_value(self, p):
        """value : dictionary
                 | array
                 | bool
                 | null
                 | NUMBER
                 | STRING"""
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
        """members :
                    | members member COMMA
                    | members member"""
        if len(p) == 1:
            p[0] = list()
        else:
            p[1].append(p[2])
            p[0] = p[1]


    def p_member(self, p):
        """member : STRING COLON value"""
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

        # FIXME: Better recovery
        # FIXME: [PP] This originated as an exception in the lexer,
        #             there is more info to extract.
        info = {
            'line': token.lineno,
            'col': self._find_column(token.lexpos)
        }
        self.issuetracker.add_error('Syntax error.', info)
        # print self.parser.statestack
        # print self.parser.symstack

        # Trying to recover from here...

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

    def parse(self, source_text):
        # return ir (AST) and issuetracker
        self.issuetracker = IssueTracker()
        self.source_text = source_text
        try:
            ir = self.parser.parse(source_text)
        except SyntaxError as e:
            self.issuetracker.add_error(e.text, {'line':e.lineno, 'col':e.offset})
            ir = ast.Node()
        return ir, self.issuetracker


# FIXME: [PP] Optionally supply an IssueTracker
def calvin_parse(source_text):
    """Parse source text and return ir (AST) and issuetracker."""
    parser = CalvinParser()
    return parser.parse(source_text)


if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) < 2:
        script = 'inline'
        source_text = \
'''
define ARG=-1

component Foo(arg) in -> out {
  """
  Foo(arg)
  Documentation please
  """

  init : std.Init(data=arg)

  .in > init.in
  init.out > .out
}

src : Foo(arg=ARG)
delay : std.ClassicDelay()
print : io.Print()

src.out > print.token
src.out > delay.token
delay.token > src.in
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

    ir, it = calvin_parse(source_text)
    if it.issue_count == 0:
        print "No issues"
    for i in it.formatted_issues(custom_format="{type!c}: {reason} {filename}:{line}:{col}", filename=script):
        print i

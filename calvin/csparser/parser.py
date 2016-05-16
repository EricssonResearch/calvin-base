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



class CalvinParser(object):
    """docstring for CalvinParser"""
    def __init__(self, lexer):
        super(CalvinParser, self).__init__()
        self.lexer = lexer
        self.parser = yacc.yacc(module=self)
        self.issues = []

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
        """constdef : DEFINE IDENTIFIER EQ argument"""
        constdef = ast.Constant(ident=ast.Id(ident=p[2]), arg=p[4])
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
        p[0] = ast.Component(name=p[2], arg_names=p[4], inports=p[6], outports=p[8], docstring=p[10], program=p[11])


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
            p[0] = [ast.Block(program=p[1])]


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
        p[0] = ast.Assignment(ident=p[1], actor_type=p[3], args=p[5])


    def p_link(self, p):
        """link : outport GT inport
                | outport GT internal_inport
                | internal_outport GT inport
                | implicit_port GT inport"""
        p[0] = ast.Link(outport=p[1], inport=p[3])


    # def p_portmap(self, p):
    #     """portmap : port GT internal_port
    #                | internal_port GT port"""
    #     p[0] = ast.Portmap(p[1], p[3])


    def p_implicit_port(self, p):
        """implicit_port : argument"""
        p[0] = ast.ImplicitPort(arg=p[1])


    def p_inport(self, p):
        """inport : IDENTIFIER DOT IDENTIFIER"""
        p[0] = ast.InPort(actor=p[1], port=p[3])

    def p_outport(self, p):
        """outport : IDENTIFIER DOT IDENTIFIER"""
        p[0] = ast.OutPort(actor=p[1], port=p[3])


    def p_internal_inport(self, p):
        """internal_inport : DOT IDENTIFIER"""
        p[0] = ast.InternalInPort(port=p[2])


    def p_internal_outport(self, p):
        """internal_outport : DOT IDENTIFIER"""
        p[0] = ast.InternalOutPort(port=p[2])


    def p_named_args(self, p):
        """named_args :
                      | named_args named_arg COMMA
                      | named_args named_arg"""
        if len(p) > 1:
            p[0] = p[1] + [p[2]]
        else:
            p[0] = []


    def p_named_arg(self, p):
        """named_arg : IDENTIFIER EQ argument"""
        p[0] = ast.NamedArg(ident=ast.Id(ident=p[1]), arg=p[3])


    def p_argument(self, p):
        """argument : value
                    | IDENTIFIER"""
        if p.slice[1].type.upper() == 'IDENTIFIER':
            p[0] = ast.Id(ident=p[1])
        else:
            p[0] = p[1]

    # def p_identifier(self, p):
    #     """identifier : IDENTIFIER"""
    #     p[0] = ast.Id(p[1])


    def p_value(self, p):
        """value : dictionary
                 | array
                 | bool
                 | null
                 | NUMBER
                 | STRING"""
        p[0] = ast.Value(value=p[1])


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
            error = {
                'type': 'error',
                'reason': 'Unexpected end of file.',
                'line': len(lines),
                'col': len(lines[-1])
            }
            self.issues.append(error)
            return
        # FIXME: Better recovery
        error = {
            'type': 'error',
            'reason': 'Syntax error.',
            'line': token.lineno,
            'col': self._find_column(token)
        }
        self.issues.append(error)
        # print self.parser.statestack
        # print self.parser.symstack

        # Trying to recover from here...

    def _find_column(self, token):
    # Compute column.
    #     input is the input text string
    #     token is a token instance
        last_cr = self.source_text.rfind('\n', 0, token.lexpos)
        # rfind returns -1 if not found, i.e. on 1st line,
        # which is exactly what we need in that case...
        column = token.lexpos - last_cr
        return column


    def debug_info(self, token):
        info = {
            'line': token.lineno,
            'col': self._find_column(token)
        }
        return info

    def parse(self, source_text):
        self.source_text = source_text
        return self.parser.parse(source_text)



# def _calvin_parser():
#     # Set up a logging object
#     import logging
#     logging.basicConfig(
#         level = logging.DEBUG,
#         filename = "parselog.txt",
#         filemode = "w",
#         format = "%(filename)10s:%(lineno)4d:%(message)s"
#     )
#     log = logging.getLogger()
#
#
#     lexer = lex.lex(module=calvin_rules)
#     lexer.zerocol = 0
#     # Since the parse may be called from other scripts, we want to have control
#     # over where parse tables (and parser.out log) will be put if the tables
#     # have to be recreated
#     this_file = os.path.realpath(__file__)
#     containing_dir = os.path.dirname(this_file)
#     parser = yacc.yacc(write_tables=False, debug=True)
#     # parser = yacc.yacc(debuglog=log, debug=True)
#     return parser


def calvin_parser(source_text, source_file=''):

    lexer = lex.lex(module=calvin_rules)
    parser = CalvinParser(lexer)
    result = parser.parse(source_text)

    return result, parser.issues, []




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

    # result, issues = calvin_parser(source_text, script)
    lexer = lex.lex(module=calvin_rules)
    parser = CalvinParser(lexer)
    result = parser.parse(source_text)

    for issue in parser.issues:
        print "{type} : {reason} {script} [{line}:{col}]".format(script=script, **issue)

    n_errors = len([x for x in parser.issues if x['type'] is 'error'])
    print "err count", n_errors
    print result
    if not n_errors:
        import astprint
        bp = astprint.BracePrinter()
        bp.visit(result)
        #print
        #print result.children

        # print result
        # print(json.dumps(result, indent=4, sort_keys=True))

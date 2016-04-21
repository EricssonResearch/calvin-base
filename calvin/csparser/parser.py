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
from calvin_rules import tokens
import astnode as ast


class CalvinSyntaxError(Exception):
    def __init__(self, message, token):
        super(CalvinSyntaxError, self).__init__(message)
        self.token = token


class CalvinEOFError(Exception):
    def __init__(self, message):
        super(CalvinEOFError, self).__init__(message)


def p_script(p):
    """script : opt_constdefs opt_compdefs opt_program"""
    s = ast.Node()
    s.add_children(p[1] + p[2] + p[3])
    p[0] = s


def p_opt_constdefs(p):
    """opt_constdefs :
                     | constdefs"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = []

def p_constdefs(p):
    """constdefs : constdefs constdef
                 | constdef"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]


def p_constdef(p):
    """constdef : DEFINE IDENTIFIER EQ argument"""
    constdef = ast.Constant(ast.Id(p[2]), p[4])
    p[0] = constdef


def p_opt_compdefs(p):
    """opt_compdefs :
                     | compdefs"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = []

def p_compdefs(p):
    """compdefs : compdefs compdef
                | compdef"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]


def p_compdef(p):
    """compdef : COMPONENT qualified_name LPAREN identifiers RPAREN identifiers RARROW identifiers LBRACE docstring program RBRACE"""
    p[0] = ast.Component(p[2], p[4], p[6], p[8], p[10], p[11])


def p_docstring(p):
    """docstring :
                 | DOCSTRING """
    if len(p) == 1:
        p[0] = "Someone(TM) should write some documentation for this component."
    else:
        p[0] = p[1]


def p_opt_program(p):
    """opt_program :
                   | program"""
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = [ast.Block(p[1])]


def p_program(p):
    """program : program statement
               | statement """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]


def p_statement(p):
    """statement : assignment
                 | link
                 | portmap"""
    p[0] = p[1]


def p_assignment(p):
    """assignment : IDENTIFIER COLON qualified_name LPAREN named_args RPAREN"""
    p[0] = ast.Assignment(p[1], p[3], p[5])


def p_link(p):
    """link : port GT port
            | implicit_port GT port"""
    p[0] = ast.Link(p[1], p[3])


def p_portmap(p):
    """portmap : port GT internal_port
               | internal_port GT port"""
    p[0] = ast.Portmap(p[1], p[3])


def p_implicit_port(p):
    """implicit_port : argument"""
    p[0] = ast.ImplicitPort(p[1])


def p_port(p):
    """port : IDENTIFIER DOT IDENTIFIER"""
    p[0] = ast.Port(p[1], p[3])


def p_internal_port(p):
    """internal_port : DOT IDENTIFIER"""
    p[0] = ast.InternalPort(p[2])


def p_named_args(p):
    """named_args :
                  | named_args named_arg COMMA
                  | named_args named_arg"""
    if len(p) > 1:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []


def p_named_arg(p):
    """named_arg : IDENTIFIER EQ argument"""
    p[0] = ast.NamedArg(ast.Id(p[1]), p[3])


def p_argument(p):
    """argument : value
                | IDENTIFIER"""
    if p.slice[1].type.upper() == 'IDENTIFIER':
        p[0] = ast.Id(p[1])
    else:
        p[0] = p[1]

# def p_identifier(p):
#     """identifier : IDENTIFIER"""
#     p[0] = ast.Id(p[1])


def p_value(p):
    """value : dictionary
             | array
             | bool
             | null
             | NUMBER
             | STRING"""
    p[0] = ast.Value(p[1])


def p_bool(p):
    """bool : TRUE
            | FALSE"""
    p[0] = bool(p.slice[1].type == 'TRUE')


def p_null(p):
    """null : NULL"""
    p[0] = None


def p_dictionary(p):
    """dictionary : LBRACE members RBRACE"""
    p[0] = dict(p[2])


def p_members(p):
    """members :
                | members member COMMA
                | members member"""
    if len(p) == 1:
        p[0] = list()
    else:
        p[1].append(p[2])
        p[0] = p[1]


def p_member(p):
    """member : STRING COLON value"""
    p[0] = (p[1], p[3].value)


def p_values(p):
    """values :
                | values value COMMA
                | values value"""
    if len(p) == 1:
        p[0] = list()
    else:
        p[1].append(p[2].value)
        p[0] = p[1]


def p_array(p):
    """array :  LBRACK values RBRACK"""
    p[0] = p[2]


def p_identifiers(p):
    """identifiers :
                   | identifiers IDENTIFIER COMMA
                   | identifiers IDENTIFIER"""
    if len(p) > 2:
        p[1].append(p[2])
    p[0] = p[1] if len(p) > 1 else []


def p_qualified_name(p):
    """qualified_name : qualified_name DOT IDENTIFIER
                      | IDENTIFIER"""
    if len(p) == 4:
        # Concatenate name
        p[0] = p[1] + p[2] + p[3]
    else:
        p[0] = p[1]


# Error rule for syntax errors
def p_error(p):
    if not p:
        raise CalvinEOFError("Unexpected end of file.")
    else:
        raise CalvinSyntaxError("Syntax error.", p)


def _calvin_parser():
    # Set up a logging object
    import logging
    logging.basicConfig(
        level = logging.DEBUG,
        filename = "parselog.txt",
        filemode = "w",
        format = "%(filename)10s:%(lineno)4d:%(message)s"
    )
    log = logging.getLogger()


    lexer = lex.lex(module=calvin_rules)
    lexer.zerocol = 0
    # Since the parse may be called from other scripts, we want to have control
    # over where parse tables (and parser.out log) will be put if the tables
    # have to be recreated
    this_file = os.path.realpath(__file__)
    containing_dir = os.path.dirname(this_file)
    parser = yacc.yacc(write_tables=False, debug=True)
    # parser = yacc.yacc(debuglog=log, debug=True)
    return parser


# Compute column.
#     input is the input text string
#     token is a token instance
def _find_column(input, token):
    last_cr = input.rfind('\n', 0, token.lexpos)
    if last_cr < 0:
        last_cr = 0
    column = (token.lexpos - last_cr) + 1
    return column


def calvin_parser(source_text, source_file=''):
    parser = _calvin_parser()
    result = ast.Node()
    # Until there is error recovery, there will only be a single error at a time
    errors = []
    result.sourcefile = source_file

    try:
        result = parser.parse(source_text)
    except CalvinSyntaxError as e:
        error = {
            'reason': str(e),
            'line': e.token.lexer.lineno,
            'col': _find_column(source_text, e.token)
        }
        errors.append(error)
    except CalvinEOFError as e:
        lines = source_text.splitlines()
        error = {
            'reason': str(e),
            'line': len(lines),
            'col': len(lines[-1])
        }
        errors.append(error)



    warnings = []

    return result, errors, warnings


if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) < 2:
        script = 'inline'
        source_text = \
'''
# Test 6: comp w arguements
component Foo(delay, n) -> out {
    src : std.CountTimer(sleep = delay, steps = n)

    src.integer > .out
}

src : Foo(delay=0.1, n=10)
snk : io.StandardOut()

src.out > snk.token
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

    result, errors, warnings = calvin_parser(source_text, script)
    if errors:
        print "{reason} {script} [{line}:{col}]".format(script=script, **errors[0])
    else:
        import astprint
        bp = astprint.BracePrinter()
        bp.visit(result)
        #print
        #print result.children

        # print result
        # print(json.dumps(result, indent=4, sort_keys=True))

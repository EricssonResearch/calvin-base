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


class CalvinSyntaxError(Exception):
    def __init__(self, message, token):
        super(CalvinSyntaxError, self).__init__(message)
        self.token = token


class CalvinEOFError(Exception):
    def __init__(self, message):
        super(CalvinEOFError, self).__init__(message)


def p_script(p):
    """script : constdefs compdefs opt_program"""
    p[0] = {'constants': p[1], 'components': p[2], 'structure': p[3]}


def p_constdefs(p):
    """constdefs :
                 | constdefs constdef
                 | constdef"""
    if len(p) == 3:
        p[1].update(p[2])
    p[0] = p[1] if len(p) > 1 else {}


def p_constdef(p):
    """constdef : DEFINE IDENTIFIER EQ argument"""
    constdef = {p[2]: p[4]}
    p[0] = constdef


def p_compdefs(p):
    """compdefs :
                | compdefs compdef
                | compdef"""
    if len(p) == 3:
        p[1].update(p[2])
    p[0] = p[1] if len(p) > 1 else {}


def p_compdef(p):
    """compdef : COMPONENT qualified_name LPAREN identifiers RPAREN identifiers RARROW identifiers LBRACE docstring program RBRACE"""
    name = p[2]
    arg_ids = p[4]
    inputs = p[6]
    outputs = p[8]
    docstring = p[10]
    structure = p[11]
    comp = {
        'name': name,
        'inports': inputs,
        'outports': outputs,
        'arg_identifiers': arg_ids,
        'structure': structure,
        'docstring': docstring,
        'dbg_line': p.lineno(2)
    }
    p[0] = {name: comp}


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
        p[0] = {'connections': [], 'actors': {}}
    else:
        p[0] = p[1]


def p_program(p):
    """program : program statement
               | statement """
    if len(p) == 3:
        # Update dict
        # p[1] is dict and p[2] is tuple (assignment|link, statement)
        kind, stmt = p[2]
        if kind is 'link':
            p[1]['connections'].append(stmt)
        else:
            p[1]['actors'].update(stmt)
        p[0] = p[1]
    else:
        # Create dict, p[1] is tuple (assignment|link, statement)
        kind, stmt = p[1]
        if kind is 'link':
            p[0] = {'connections': [stmt], 'actors': {}}
        else:
            p[0] = {'connections': [], 'actors': stmt}


def p_statement(p):
    """statement : assignment
                 | link"""
    p[0] = p[1]


def p_assignment(p):
    """assignment : IDENTIFIER COLON qualified_name LPAREN named_args RPAREN"""
    p[0] = ('assignment', {p[1]: {'actor_type': p[3], 'args': p[5], 'dbg_line': p.lineno(2)}})


def p_link(p):
    """link : port GT port
            | argument GT port"""
    kind, value = p[1]
    (src, port) = value if kind == 'PORT' else (None, (kind, value))
    d = {}
    d['src'] = src
    d['src_port'] = port
    _, (dst, port) = p[3]
    d['dst'] = dst
    d['dst_port'] = port
    d['dbg_line'] = p.lineno(2)
    p[0] = ('link', d)


def p_port(p):
    """port : IDENTIFIER DOT IDENTIFIER
            | DOT IDENTIFIER"""
    p[0] = ('PORT', (p[1], p[2] if len(p) == 3 else p[3]))


def p_named_args(p):
    """named_args :
                  | named_args named_arg COMMA
                  | named_args named_arg"""

    if len(p) > 2:
        p[1].update(p[2])
    p[0] = p[1] if len(p) > 1 else {}


def p_named_arg(p):
    """named_arg : IDENTIFIER EQ argument"""
    p[0] = {p[1]: p[3]}


def p_argument(p):
    """argument : value
                | IDENTIFIER"""
    p[0] = (p.slice[1].type.upper(), p[1])


def p_value(p):
    """value : dictionary
             | array
             | bool
             | null
             | NUMBER
             | STRING"""
    p[0] = p[1]


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
    p[0] = (p[1], p[3])


def p_values(p):
    """values :
                | values value COMMA
                | values value"""
    if len(p) == 1:
        p[0] = list()
    else:
        p[1].append(p[2])
        p[0] = p[1]


def p_array(p):
    """array :  LBRACK values RBRACK"""
    p[0] = p[2]


# def p_opt_id_list(p):
#     """opt_id_list :
#                    | id_list"""
#     if len(p) == 1:
#         p[0] = []
#     else:
#         p[0] = p[1]

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
    lexer = lex.lex(module=calvin_rules)
    lexer.zerocol = 0
    # Since the parse may be called from other scripts, we want to have control
    # over where parse tables (and parser.out log) will be put if the tables
    # have to be recreated
    this_file = os.path.realpath(__file__)
    containing_dir = os.path.dirname(this_file)
    parser = yacc.yacc(debug=False, optimize=True, outputdir=containing_dir)
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
    result = {}
    # Until there is error recovery, there will only be a single error at a time
    errors = []

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

    result['sourcefile'] = source_file

    warnings = []

    return result, errors, warnings


if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) < 2:
        script = 'inline'
        source_text = \
'''        # Test script
        define FOO = true
        define BAR = false
        # define BAZ = 43
        component Count(len)  -> a,b,seq {
            """FOO"""
            src : std.Constant(data="hup", n=len)
            src.token > .seq
        }
        # component Count2(len) -> seq {
        #     src : std.Constant(data="hup", n=len)
        #     src.token > .seq
        # }
        #
        src: Count(len=5)
        snk : io.StandardOut()
        42 > snk.token
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
        print(json.dumps(result, indent=4, sort_keys=True))

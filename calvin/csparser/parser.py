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
    """script : opt_constdef_list opt_compdef_list opt_program"""
    p[0] = {'constants': p[1], 'components': p[2], 'structure': p[3]}


def p_opt_constdef_list(p):
    """opt_constdef_list :
                        | constdef_list"""
    p[0] = {} if len(p) == 1 else p[1]


def p_constdef_list(p):
    """constdef_list : constdef_list constdef
                    | constdef"""
    if len(p) == 3:
        p[1].update(p[2])
        p[0] = p[1]
    else:
        p[0] = p[1]

def p_constdef(p):
    """constdef : CONSTANT IDENTIFIER LET value"""
    constdef = {p[2]:p[4]}
    p[0] = constdef

def p_opt_compdef_list(p):
    """opt_compdef_list :
                        | compdef_list"""
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = p[1]


def p_compdef_list(p):
    """compdef_list : compdef_list compdef
                    | compdef"""
    if len(p) == 3:
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]


def p_compdef(p):
    """compdef : COMPONENT qualified_name LPAREN opt_id_list RPAREN opt_id_list RARROW opt_id_list LBRACE opt_docstring program RBRACE"""
    name = p[2]
    arg_ids = p[4]
    inputs = p[6]
    outputs = p[8]
    docstring = p[10]
    structure = p[11]
    p[0] = {
        'name': name,
        'inports': inputs,
        'outports': outputs,
        'arg_identifiers': arg_ids,
        'structure': structure,
        'docstring': docstring,
        'dbg_line':p.lineno(2)
    }


def p_opt_docstring(p):
    """opt_docstring :
                     | docstring """
    if len(p) == 1:
        p[0] = "Someone(TM) should write some documentation for this component."
    else:
        p[0] = p[1]


def p_docstring(p):
    """docstring : DOCSTRING """
    p[0] = p[1]


def p_opt_program(p):
    """opt_program :
                   | program"""
    if len(p) == 1:
        p[0] = {'connections': [], 'actors': {}}
    else:
        p[0] = p[1]


def p_program(p):
    """program : statement_list"""
    # Return a dictionary {'connections':[ [<conn1>], [<conn2>], ... ],
    # 'actors':{ <name1>:{}, <name2>:{} }}
    p[0] = p[1]


def p_statement_list(p):
    """statement_list : statement_list statement
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
    """assignment : IDENTIFIER COLON qualified_name LPAREN opt_named_argument_list RPAREN"""
    p[0] = ('assignment', {p[1]: {'actor_type': p[3], 'args': p[5], 'dbg_line':p.lineno(2)}})


def p_link(p):
    """link : qualified_port GT qualified_port
            | qualified_port GT IDENTIFIER
            | IDENTIFIER GT qualified_port
            | value GT qualified_port"""
    left_qp = type(p[1]) is list
    right_qp = type(p[3]) is list
    d = {}
    d['src'] = p[1][0] if left_qp else None
    d['src_port'] = p[1][1] if left_qp else p[1]
    d['dst'] = p[3][0] if right_qp else None
    d['dst_port'] = p[3][1] if right_qp else p[3]
    d['dbg_line'] = p.lineno(2)
    p[0] = ('link', d)


def p_qualified_port(p):
    """qualified_port : IDENTIFIER DOT IDENTIFIER"""
    p[0] = [p[1], p[3]]


def p_opt_named_argument_list(p):
    """opt_named_argument_list :
                               | named_argument_list"""
    if len(p) == 1:
        p[0] = {}
    else:
        p[0] = p[1]


def p_named_argument_list(p):
    """named_argument_list : named_argument_list COMMA named_argument
                           | named_argument"""
    if len(p) == 4:
        # Update dict
        p[1].update(p[3])
        p[0] = p[1]
    else:
        # Create dict, p[1] is in fact a dictionary
        p[0] = p[1]


def p_named_argument(p):
    """named_argument : IDENTIFIER EQ value"""
    p[0] = {p[1]: p[3]}


def p_value(p):
    """value : object
             | array
             | STRING
             | NUMBER
             | IDENTIFIER"""
    p[0] = (p.slice[1].type.upper(), p[1])


def p_value_false(p):
  """value : FALSE"""
  p[0] = False


def p_value_true(p):
  """value : TRUE"""
  p[0] = True


def p_value_null(p):
  """value : NULL"""
  p[0] = None


def p_object(p):
  """object : LBRACE members RBRACE"""
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


def p_opt_id_list(p):
    """opt_id_list :
                   | id_list"""
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = p[1]

def p_id_list(p):
    """id_list : id_list COMMA IDENTIFIER
               | IDENTIFIER"""
    if len(p) == 4:
        # Append list
        p[0] = p[1] + [p[3]]
    else:
        # Create list
        p[0] = [p[1]]

def p_qualified_name(p):
    """qualified_name : qualified_name DOT IDENTIFIER
                      | IDENTIFIER"""
    if len(p) == 4:
        # Append list
        p[0] = p[1] + p[2] + p[3]
    else:
        # Create list
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
    parser = yacc.yacc(debug=0, outputdir=containing_dir)
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
            'reason':str(e),
            'line':e.token.lexer.lineno,
            'col':_find_column(source_text, e.token)
        }
        errors.append(error)
    except CalvinEOFError as e:
        lines = source_text.splitlines()
        error = {
            'reason':str(e),
            'line':len(lines),
            'col':len(lines[-1])
        }
        errors.append(error)

    result['sourcefile'] = source_file

    warnings = []

    return result, errors, warnings


if __name__ == '__main__':
    import sys
    import os
    import json

    if len(sys.argv) < 2:
        script = 'inline'
        source_text = \
"""# Test script
constant xyz := 11
constant baz := "abc"
constant foo := baz
x:std.Foo()
y:std.Bar()
x.out > y.in
[false, true, null, 1, {"ABCdef":11}] > x.in
"""
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

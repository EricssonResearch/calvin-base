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

import ply.lex as lex

# Make sure we have an initial value for zerocol
lex.Lexer.zerocol = 0

keywords = {x:x.upper() for x in ['component', 'define', 'voidport', 'rule', 'group', 'apply']}

tokens = [
    'IDENTIFIER', 'STRING', 'NUMBER',
    'LPAREN', 'RPAREN',
    'LBRACE', 'RBRACE',
    'LBRACK', 'RBRACK',
    'DOT', 'COMMA', 'COLON',
    'GT', 'EQ',
    'AND', 'OR', 'UNOT',
    'RARROW', 'SLASH',
    'DOCSTRING',
    'FALSE', 'TRUE', 'NULL',
    'AT'
] + list(keywords.values())

t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LBRACK = r'\['
t_RBRACK = r'\]'
t_DOT = r'\.'
t_COMMA = r','
t_COLON = r':'
t_GT = r'>'
t_EQ = r'='
t_RARROW = r'->'
t_SLASH = r'/'
t_AND = r'&'
t_OR = r'\|'
t_UNOT = r'~'
t_AT = r'@'

# t_FALSE = r'false'
# t_TRUE = r'true'
# t_NULL = r'null'


def t_COMMENT(t):
    # FIXME: // is deprecated as line-comment
    r'(/\*(.|\n)*?\*/)|(//.*)|(\#.*)'
    t.lexer.lineno += t.value.count('\n')


def t_DOCSTRING(t):
    r'"""(.|\n)*?"""'
    t.lexer.lineno += t.value.count('\n')
    t.value = t.value.strip('"')
    t.value = t.value.strip(' \n\t')
    return t

# String allows escaping of any character
# Multiline strings are not allowed, but
# parser will concatenate sequential strings
# separated by any number/kind of whitespace.
# FIXME: The second form is a temporary workaround until we have reimplemented the port mappings
def t_STRING(t):
    r'(?:!?\"(?:[^\"\\\n]|(?:\\.))*?\")|(?:&[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*)'
#   r'!?"([^"\\\n]|(\\.))*?"'
    is_raw = False
    if t.value.startswith('&'):
        t.value = t.value[1:]
        return t
    if t.value.startswith('!'):
        # Keep as raw string
        is_raw = True
        t.value = t.value[1:]
    # Remove the double quotes
    t.value = t.value[1:-1]
    if not is_raw:
        t.value = t.value.decode('string_escape')
    return t


def t_NUMBER(t):
    r'-?\d+(?:\.\d*)?'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_TRUE(t):
    r'true'
    return t

def t_FALSE(t):
    r'false'
    return t

def t_NULL(t):
    r'null'
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z][a-zA-Z0-9_]*'
    t.type = keywords.get(t.value, 'IDENTIFIER')  # Check for reserved words
    return t

# Track line numbers


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.lexer.zerocol = t.lexpos

t_ignore = ' \t'

# Error handling rule


def t_error(t):
    msg = "Illegal character '{}'".format(t.value[0])
    syntax_error = SyntaxError(msg)
    syntax_error.text = msg
    syntax_error.lineno = t.lexer.lineno
    syntax_error.offset = t.lexpos - t.lexer.zerocol
    raise syntax_error






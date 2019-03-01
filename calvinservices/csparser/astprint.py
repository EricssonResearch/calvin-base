# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
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


from __future__ import print_function
from __future__ import absolute_import
from . import astnode as ast
from .visitor import Visitor

class DotPrinter(Visitor):
    """docstring for DotPrinter"""
    def __init__(self):
        super(DotPrinter, self).__init__()
        self.statements = []


    def generic_visit(self, node):
        self.vertex(node)
        self.decorate(node)
        self.properties(node)
        self.edges(node)
        self._visit_children(node.children)

    def add(self, stmt):
        self.statements.append(stmt)

    def vertex(self, node):
        stmt = '"{}" [label="{}"];'.format(hex(id(node)), node.__class__.__name__)
        self.add(stmt)

    def edges(self, node):
        for child in node.children or []:
            stmt = '"{}" -> "{}";'.format(hex(id(node)), hex(id(child)))
            self.add(stmt)

    def decorate(self, node):
        pass

    def properties(self, node):
        pass

    def process(self, node):
        self.add('digraph TMP {')
        self.visit(node)
        self.add('}')
        print("\n".join(self.statements))


class DotDebugPrinter(DotPrinter):
    """docstring for DotDebugPrinter"""
    def __init__(self):
        super(DotDebugPrinter, self).__init__()

    def decorate(self, node):
        if node.parent:
            stmt = '"{}" -> "{}" [color=red];'.format(hex(id(node)), hex(id(node.parent)))
            self.add(stmt)

    def properties(self, node):
        if type(node) is ast.Value:
            stmt = '"{}" -> "{}";'.format(hex(id(node)), hex(id(node))+"_value")
            self.add(stmt)
            stmt = '"{}" [shape=box, label="{}"];'.format(hex(id(node))+"_value", node.value)
            self.add(stmt)


class BraceFormatter(Visitor):
    def __init__(self):
        self.indent = 0

    def _visit(self, node, preorder=None, inorder=None, postorder=None):
        if preorder: preorder(node)
        if not node.children:
            if inorder: inorder(node)
        else:
            left, last = node.children[0:-1], node.children[-1:]
            if not left:
                if last: self.visit(last[0])
                if inorder: inorder(node)
            else:
                self.indent +=1
                for child in left:
                    self.visit(child)
                    if inorder: inorder(node)
                self.visit(last[0])
                self.indent -=1
        if postorder: postorder(node)

    def _indentation(self):
        return "    "*self.indent

    def process(self, node):
        self.indent = 0
        self.result = []
        self.visit(node)
        return "\n".join(self.result)


    def generic_visit(self, node):
        def f(node):
            self.result.append("{}( {}".format(self._indentation(), node.__class__.__name__))
            self.indent += 1
        def g(node):
            self.indent -= 1
            self.result.append("{})".format(self._indentation()))
        self._visit(node, preorder=f, postorder=g)

    # @visitor.when(ast.Block)
    # def visit(self, node):
    #     def f(node):
    #         xtra_indent = self._indentation() + " "*11
    #         self.result.append("{}( {}\n{}namespace: {},\n{}args: {}".format(
    #             self._indentation(), node,
    #             xtra_indent, node.namespace,
    #             xtra_indent, node.args
    #         ))
    #     def g(node):
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)
    #
    def visit_Id(self, node):
        self.result.append("{}( {} {} )".format(self._indentation(), node.__class__.__name__, node.ident))

    def visit_Value(self, node):
        self.result.append("{}( {} {} )".format(self._indentation(), node.__class__.__name__, node.value))

    # @visitor.when(ast.Assignment)
    # def visit(self, node):
    #     def f(node):
    #         self.result.append("{}( {} {} {}".format(self._indentation(), node, node.ident, node.actor_type))
    #         self.indent += 1
    #     def g(node):
    #         self.indent -= 1
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)
    #
    # @visitor.when(ast.Link)
    # def visit(self, node):
    #     def f(node):
    #         self.result.append("{}( {}".format(self._indentation(), node.__class__.__name__))
    #         self.indent += 1
    #     def g(node):
    #         self.indent -= 1
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)
    #
    #
    # @visitor.when(ast.Port)
    # def visit(self, node):
    #     # self.result.append("{}( {} {}.{} )".format(self._indentation(), node, node.actor, node.port))
    #     def f(node):
    #         self.result.append("{}( {} {}".format(self._indentation(), node.__class__.__name__, node.name))
    #         self.indent += 1
    #     def g(node):
    #         self.indent -= 1
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)
    #
    #
    #
    def visit_InPort(self, node):
        def f(node):
            self.result.append("{}( {} {}".format(self._indentation(), node.__class__.__name__, node.name))
            self.indent += 1
        def g(node):
            self.indent -= 1
            self.result.append("{})".format(self._indentation()))
        self._visit(node, preorder=f, postorder=g)
    # #
    def visit_OutPort(self, node):
        def f(node):
            self.result.append("{}( {} {}".format(self._indentation(), node.__class__.__name__, node.name))
            self.indent += 1
        def g(node):
            self.indent -= 1
            self.result.append("{})".format(self._indentation()))
        self._visit(node, preorder=f, postorder=g)

    def visit_PortProperty(self, node):
        def f(node):
            self.result.append("{}( {} {}.{}[{}]".format(self._indentation(), node.__class__.__name__, node.actor, node.port, node.direction))
            self.indent += 1
        def g(node):
            self.indent -= 1
            self.result.append("{})".format(self._indentation()))
        self._visit(node, preorder=f, postorder=g)
    #
    # @visitor.when(ast.ImplicitPort)
    # def visit(self, node):
    #     def f(node):
    #         self.result.append("{}( {}".format(self._indentation(), node))
    #         self.indent += 1
    #     def g(node):
    #         self.indent -= 1
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)
    #
    def visit_InternalInPort(self, node):
        def f(node):
            self.result.append("{}( {} {}".format(self._indentation(), node.__class__.__name__, node.name))
            self.indent += 1
        def g(node):
            self.indent -= 1
            self.result.append("{})".format(self._indentation()))
        self._visit(node, preorder=f, postorder=g)

    def visit_InternalOutPort(self, node):
        def f(node):
            self.result.append("{}( {} {}".format(self._indentation(), node.__class__.__name__, node.name))
            self.indent += 1
        def g(node):
            self.indent -= 1
            self.result.append("{})".format(self._indentation()))
        self._visit(node, preorder=f, postorder=g)

    # @visitor.when(ast.Component)
    # def visit(self, node):
    #     def f(node):
    #         self.result.append("{}( {} {}".format(self._indentation(), node, node.name))
    #         self.indent += 1
    #     def g(node):
    #         self.indent -= 1
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)
    #
    # @visitor.when(ast.Group)
    # def visit(self, node):
    #     def f(node):
    #         self.result.append("{}( {} {}".format(self._indentation(), node, node.group.ident))
    #         self.indent += 1
    #     def g(node):
    #         self.indent -= 1
    #         self.result.append("{})".format(self._indentation()))
    #     self._visit(node, preorder=f, postorder=g)


class BracePrinter(BraceFormatter):
    """docstring for BracePrinter"""
    def __init__(self):
        super(BracePrinter, self).__init__()

    def process(self, node):
        text = super(BracePrinter, self).process(node)
        print(text)

if __name__ == '__main__':
    ast.Node._verbose_desc = True

    n = ast.Node()
    bp = BracePrinter()
    bp.process(n)

    dp = DotPrinter()
    dp.process(n)



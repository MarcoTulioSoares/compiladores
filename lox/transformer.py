"""
Implementa o transformador da árvore sintática que converte entre as representações

    lark.Tree -> lox.ast.Node.

A resolução de vários exercícios requer a modificação ou implementação de vários
métodos desta classe.
"""

from typing import Callable
from lark import Transformer, v_args

from . import runtime as op
from .ast import VarDef, Literal, Var, Print, Call, Program, BinOp


def op_handler(op: Callable):
    """
    Fábrica de métodos que lidam com operações binárias na árvore sintática.

    Recebe a função que implementa a operação em tempo de execução.
    """

    def method(self, left, right):
        return BinOp(left, right, op)

    return method


@v_args(inline=True)
class LoxTransformer(Transformer):
    # Programa
    def program(self, *stmts):
        return Program(list(stmts))

    # Operações matemáticas básicas
    mul = op_handler(op.mul)
    div = op_handler(op.truediv)
    sub = op_handler(op.sub)
    add = op_handler(op.add)

    # Comparações
    gt = op_handler(op.gt)
    lt = op_handler(op.lt)
    ge = op_handler(op.ge)
    le = op_handler(op.le)
    eq = op_handler(op.eq)
    ne = op_handler(op.ne)

    # Outras expressões
    def call(self, name: Var, params: list):
        return Call(name.name, params)
        
    def params(self, *args):
        params = list(args)
        return params

    # Comandos
    def print_cmd(self, expr):
        return Print(expr)

    def var_decl(self, name, value=None):
        if value is None:
            value = Literal(None)
        return VarDef(name.name, value)

    def block(self, *stmts):
        return Block(list(stmts))

    def if_cmd(self, condition, then_branch, else_branch=None):
        if else_branch is None:
            # Se não há else, criamos um bloco vazio
            else_branch = Block([])
        return If(condition, then_branch, else_branch)

    def VAR(self, token):
        name = str(token)
        return Var(name)

    def NUMBER(self, token):
        num = float(token)
        return Literal(num)
    
    def STRING(self, token):
        text = str(token)[1:-1]
        return Literal(text)
    
    def NIL(self, _):
        return Literal(None)

    def BOOL(self, token):
        return Literal(token == "true")

    def unary(self, op_token, expr):
        if str(op_token) == '!':
            return UnaryOp(op.not_, expr)
        elif str(op_token) == '-':
            return UnaryOp(op.neg, expr)
        else:
            raise NotImplementedError(f"Operador unário desconhecido: {op_token}")
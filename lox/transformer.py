"""
Implementa o transformador da árvore sintática que converte entre as representações

    lark.Tree -> lox.ast.Node.

A resolução de vários exercícios requer a modificação ou implementação de vários
métodos desta classe.
"""

from typing import Callable
from lark import Transformer, v_args

from . import runtime as op
from .ast import *
from .ast import If, Block


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

    # Operadores lógicos
    def logical_or(self, *args):
        return args[0]

    def logical_and(self, *args):
        return args[0]

    def equality(self, *args):
        if len(args) == 1:
            return args[0]
        # args[0] é o primeiro valor, args[1:] são pares (op, valor)
        result = args[0]
        for i in range(1, len(args), 2):
            if i + 1 < len(args):
                op_token = args[i]
                right = args[i + 1]
                if op_token == "==":
                    result = BinOp(result, right, op.eq)
                elif op_token == "!=":
                    result = BinOp(result, right, op.ne)
        return result

    def comparison(self, *args):
        if len(args) == 1:
            return args[0]
        result = args[0]
        for i in range(1, len(args), 2):
            if i + 1 < len(args):
                op_token = args[i]
                right = args[i + 1]
                if op_token == ">":
                    result = BinOp(result, right, op.gt)
                elif op_token == ">=":
                    result = BinOp(result, right, op.ge)
                elif op_token == "<":
                    result = BinOp(result, right, op.lt)
                elif op_token == "<=":
                    result = BinOp(result, right, op.le)
        return result

    def term(self, *args):
        print(f"DEBUG: term called with args={args}, len={len(args)}")
        if len(args) == 1:
            return args[0]
        result = args[0]
        for i in range(1, len(args), 2):
            if i + 1 < len(args):
                op_token = args[i]
                right = args[i + 1]
                print(f"DEBUG: applying {op_token} to {result} and {right}")
                if op_token == "+":
                    result = BinOp(result, right, op.add)
                elif op_token == "-":
                    result = BinOp(result, right, op.sub)
        return result

    def factor(self, *args):
        print(f"DEBUG: factor called with args={args}, len={len(args)}")
        if len(args) == 1:
            return args[0]
        result = args[0]
        for i in range(1, len(args), 2):
            if i + 1 < len(args):
                op_token = args[i]
                right = args[i + 1]
                if op_token == "*":
                    result = BinOp(result, right, op.mul)
                elif op_token == "/":
                    result = BinOp(result, right, op.truediv)
        return result

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

    def while_cmd(self, condition, body):
        return While(condition, body)

    def for_cmd(self, init, cond, incr, body):
        # Se init for None, vira Literal(None)
        if init is None:
            init = Literal(None)
        # Se cond for None, vira Literal(True)
        if cond is None:
            cond = Literal(True)
        # Se incr for None, vira Literal(None)
        if incr is None:
            incr = Literal(None)
        # Corpo do while: { body; incr }
        from .ast import Block, While
        while_body = Block([body] + ([] if isinstance(incr, Literal) and incr.value is None else [incr]))
        while_node = While(cond, while_body)
        # Bloco final: { init; while (cond) { body; incr } }
        return Block([init, while_node])

    def for_init(self, *args):
        if len(args) == 0:
            return None
        return args[0]

    def for_cond(self, *args):
        if len(args) == 0:
            return None
        return args[0]

    def for_incr(self, *args):
        if len(args) == 0:
            return None
        return args[0]

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

    def unary(self, *args):
        print(f"DEBUG: unary called with args: {args}")
        if len(args) == 2:
            op_token, expr = args
            if str(op_token) == '!':
                return UnaryOp(op.not_, expr)
            elif str(op_token) == '-':
                return UnaryOp(op.neg, expr)
            else:
                raise NotImplementedError(f"Operador unário desconhecido: {op_token}")
        elif len(args) == 1:
            return args[0]
        else:
            raise TypeError("unary espera 1 ou 2 argumentos")

    def assign(self, var, value):
        return Assign(var.name, value)

    def atom(self, *args):
        return args[0]

    def add(self, left, right):
        return BinOp(left, right, op.add)
    def sub(self, left, right):
        return BinOp(left, right, op.sub)
    def mul(self, left, right):
        return BinOp(left, right, op.mul)
    def div(self, left, right):
        return BinOp(left, right, op.truediv)
    def eq(self, left, right):
        return BinOp(left, right, op.eq)
    def ne(self, left, right):
        return BinOp(left, right, op.ne)
    def gt(self, left, right):
        return BinOp(left, right, op.gt)
    def ge(self, left, right):
        return BinOp(left, right, op.ge)
    def lt(self, left, right):
        return BinOp(left, right, op.lt)
    def le(self, left, right):
        return BinOp(left, right, op.le)
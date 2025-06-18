from abc import ABC
from dataclasses import dataclass
from typing import Callable, Optional

from .ctx import Ctx
from .node import Cursor
from .errors import SemanticError

# Declaramos nossa classe base num módulo separado para esconder um pouco de
# Python relativamente avançado de quem não se interessar pelo assunto.
#
# A classe Node implementa um método `pretty` que imprime as árvores de forma
# legível. Também possui funcionalidades para navegar na árvore usando cursores
# e métodos de visitação.
from .node import Node

# Palavras reservadas que não podem ser usadas como nomes de variáveis
RESERVED_WORDS = {
    "true", "false", "nil", "and", "or", "class", "else", "for", 
    "fun", "if", "print", "return", "super", "this", "var", "while"
}

#
# TIPOS BÁSICOS
#

# Tipos de valores que podem aparecer durante a execução do programa
Value = bool | str | float | None


class Expr(Node, ABC):
    """
    Classe base para expressões.

    Expressões são nós que podem ser avaliados para produzir um valor.
    Também podem ser atribuídos a variáveis, passados como argumentos para
    funções, etc.
    """


class Stmt(Node, ABC):
    """
    Classe base para comandos.

    Comandos são associdos a construtos sintáticos que alteram o fluxo de
    execução do código ou declaram elementos como classes, funções, etc.
    """


@dataclass
class Program(Node):
    """
    Representa um programa.

    Um programa é uma lista de comandos.
    """

    stmts: list[Stmt]

    def eval(self, ctx: Ctx):
        for stmt in self.stmts:
            stmt.eval(ctx)


#
# EXPRESSÕES
#
@dataclass
class BinOp(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x + y, 2 * x, 3.14 > 3 and 3.14 < 4
    """

    left: Expr
    right: Expr
    op: Callable[[Value, Value], Value]

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        right_value = self.right.eval(ctx)
        return self.op(left_value, right_value)


@dataclass
class Var(Expr):
    """
    Uma variável no código

    Ex.: x, y, z
    """

    name: str

    def eval(self, ctx: Ctx):
        try:
            return ctx[self.name]
        except KeyError:
            raise NameError(f"variável {self.name} não existe!")

    def validate_self(self, cursor: Cursor):
        if self.name in RESERVED_WORDS:
            raise SemanticError("nome inválido", token=self.name)


@dataclass
class Literal(Expr):
    """
    Representa valores literais no código, ex.: strings, booleanos,
    números, etc.

    Ex.: "Hello, world!", 42, 3.14, true, nil
    """

    value: Value

    def eval(self, ctx: Ctx):
        return self.value


@dataclass
class And(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x and y
    """
    left: Expr
    right: Expr
    
    def eval(self, ctx: Ctx):
        from .runtime import truthy
        left_value = self.left.eval(ctx)
        if not truthy(left_value):  # Curto-circuito: se left é falsy, retorna left
            return left_value
        return self.right.eval(ctx)  # Só avalia right se left for truthy


@dataclass
class Or(Expr):
    """
    Uma operação infixa com dois operandos.
    Ex.: x or y
    """
    left: Expr
    right: Expr
    
    def eval(self, ctx: Ctx):
        from .runtime import truthy
        left_value = self.left.eval(ctx)
        if truthy(left_value):  # Curto-circuito: se left é truthy, retorna left
            return left_value
        return self.right.eval(ctx)  # Só avalia right se left for falsy


@dataclass
class UnaryOp(Expr):
    """
    Uma operação prefixa com um operando.

    Ex.: -x, !x
    """
    op: callable
    expr: Expr

    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx)
        return self.op(value)


@dataclass
class Call(Expr):
    """
    Uma chamada de função.

    Ex.: fat(42)
    """
    callee: Expr
    params: list[Expr]
    
    def eval(self, ctx: Ctx):
        # Avalia o callee (pode ser uma variável ou um acesso a atributo)
        callee_value = self.callee.eval(ctx)
        
        # Avalia os parâmetros
        params = []
        for param in self.params:
            params.append(param.eval(ctx))
        
        # Se o callee é callable, chama-o
        if callable(callee_value):
            return callee_value(*params)
        else:
            raise TypeError(f"'{callee_value}' não é uma função!")


@dataclass
class This(Expr):
    """
    Acesso ao `this`.

    Ex.: this
    """
    _: None = None  # Campo vazio para garantir __annotations__
    
    def eval(self, ctx: Ctx):
        try:
            return ctx["this"]
        except KeyError:
            raise NameError("'this' não pode ser usado fora de um método!")


@dataclass
class Super(Expr):
    """
    Acesso a method ou atributo da superclasse.

    Ex.: super.x
    """


@dataclass
class Assign(Expr):
    """
    Atribuição de variável.

    Ex.: x = 42
    """
    name: str
    value: Expr

    def eval(self, ctx: Ctx):
        val = self.value.eval(ctx)
        ctx[self.name] = val
        return val


@dataclass
class Getattr(Expr):
    """
    Acesso a atributo de um objeto.

    Ex.: x.y
    """
    obj: Expr
    attr: str

    def eval(self, ctx: Ctx):
        obj_value = self.obj.eval(ctx)
        try:
            return getattr(obj_value, self.attr)
        except AttributeError:
            raise AttributeError(f"objeto não possui atributo '{self.attr}'")


@dataclass
class Setattr(Expr):
    """
    Atribuição de atributo de um objeto.

    Ex.: x.y = 42
    """
    obj: Expr
    attr: str
    value: Expr

    def eval(self, ctx: Ctx):
        obj_value = self.obj.eval(ctx)
        val = self.value.eval(ctx)
        setattr(obj_value, self.attr, val)
        return val


#
# COMANDOS
#
@dataclass
class Print(Stmt):
    """
    Representa uma instrução de impressão.

    Ex.: print "Hello, world!";
    """
    expr: Expr
    
    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx)
        from .runtime import show
        print(show(value))


@dataclass
class Return(Stmt):
    """
    Representa uma instrução de retorno.

    Ex.: return x;
    """
    expr: Expr

    def eval(self, ctx: Ctx):
        # Avalia a expressão e levanta uma exceção LoxReturn com o valor
        from .runtime import LoxReturn
        value = self.expr.eval(ctx)
        raise LoxReturn(value)


@dataclass
class VarDef(Stmt):
    name: str
    value: Expr

    def eval(self, ctx: Ctx):
        val = self.value.eval(ctx)
        ctx.var_def(self.name, val)

    def validate_self(self, cursor: Cursor):
        if self.name in RESERVED_WORDS:
            raise SemanticError("nome inválido", token=self.name)


@dataclass
class If(Stmt):
    """
    Representa uma instrução condicional.

    Ex.: if (x > 0) { ... } else { ... }
    """
    condition: Expr
    then_branch: Stmt
    else_branch: Stmt
    
    def eval(self, ctx: Ctx):
        condition_value = self.condition.eval(ctx)
        if condition_value:
            self.then_branch.eval(ctx)
        else:
            self.else_branch.eval(ctx)
        return None


@dataclass
class While(Stmt):
    """
    Representa um laço de repetição.

    Ex.: while (x > 0) { ... }
    """
    condition: Expr
    body: Stmt
    
    def eval(self, ctx: Ctx):
        while self.condition.eval(ctx):
            self.body.eval(ctx)
        return None


@dataclass
class Block(Node):
    """
    Representa bloco de comandos.

    Ex.: { var x = 42; print x;  }
    """
    stmts: list[Stmt]
    
    def eval(self, ctx: Ctx):
        # Cria um novo escopo para o bloco
        new_ctx = ctx.push({})
        for stmt in self.stmts:
            stmt.eval(new_ctx)
        return None

    def validate_self(self, cursor: Cursor):
        # Coleta todos os nomes de variáveis declaradas neste bloco
        var_names = set()
        for stmt in self.stmts:
            if isinstance(stmt, VarDef):
                if stmt.name in var_names:
                    raise SemanticError("Already a variable with this name in this scope.", token=stmt.name)
                var_names.add(stmt.name)


@dataclass
class Function(Stmt):
    """
    Representa uma função.

    Ex.: fun f(x, y) { ... }
    """
    name: str
    params: list[str]
    body: Block

    def eval(self, ctx: Ctx):
        # Cria uma instância de LoxFunction com o contexto atual
        from .runtime import LoxFunction
        function = LoxFunction(self.name, self.params, self.body, ctx)
        
        # Define a função no contexto
        ctx.var_def(self.name, function)
        return function

    def validate_self(self, cursor: Cursor):
        # Verifica se há parâmetros duplicados
        if len(self.params) != len(set(self.params)):
            # Encontra o primeiro parâmetro duplicado
            seen = set()
            for param in self.params:
                if param in seen:
                    raise SemanticError("Already a variable with this name in this scope.", token=param)
                seen.add(param)
        
        # Verifica se os parâmetros não são palavras reservadas
        for param in self.params:
            if param in RESERVED_WORDS:
                raise SemanticError("nome inválido", token=param)
        
        # Verifica se há variáveis locais com o mesmo nome que parâmetros
        param_set = set(self.params)
        for stmt in self.body.stmts:
            if isinstance(stmt, VarDef):
                if stmt.name in param_set:
                    raise SemanticError("Already a variable with this name in this scope.", token=stmt.name)


@dataclass
class Method(Node):
    """
    Representa um método de classe.

    Ex.: fun f(x, y) { return x + y; }
    """
    name: str
    params: list[str]
    body: Block


@dataclass
class Class(Stmt):
    """
    Representa uma classe.

    Ex.: class B < A { ... }
    """
    name: str
    superclass: Optional[str] = None
    methods: list = None

    def eval(self, ctx: Ctx):
        from .runtime import LoxClass, LoxFunction
        
        # Carrega a superclasse, caso exista
        superclass = None
        if self.superclass:
            superclass = ctx[self.superclass]
        
        # Avaliamos cada método
        methods = {}
        for method in self.methods or []:
            method_name = method.name
            method_args = method.params
            method_body = method.body
            method_impl = LoxFunction(method_name, method_args, method_body, ctx)
            methods[method_name] = method_impl

        lox_class = LoxClass(self.name, methods, superclass)
        ctx.var_def(self.name, lox_class)
        return lox_class

from .runtime import LoxInstance  # Adicionado para os testes encontrarem LoxInstance

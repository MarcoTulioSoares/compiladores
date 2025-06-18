import builtins
from dataclasses import dataclass
from operator import add, eq, ge, gt, le, lt, mul, ne, neg, not_, sub, truediv
from typing import TYPE_CHECKING, Optional
from types import FunctionType, BuiltinFunctionType

from .ctx import Ctx

if TYPE_CHECKING:
    from .ast import Stmt, Value

__all__ = [
    "add",
    "eq",
    "ge",
    "gt",
    "le",
    "lt",
    "mul",
    "ne",
    "neg",
    "not_",
    "print",
    "show",
    "sub",
    "truthy",
    "truediv",
]


class LoxInstance:
    """
    Classe base para todos os objetos Lox.
    """
    
    def __init__(self, klass):
        """
        Construtor que recebe a classe associada à instância.
        """
        self.__klass = klass
        self.__fields = {}
    
    def __getattr__(self, attr):
        """
        self.__getattr__(self, "attr") <==> self.attr 
            (se o objeto não definir attr explicitamente)
        """
        # Primeiro, verifica se é um campo da instância
        if attr in self.__fields:
            return self.__fields[attr]
        
        # Se não for um campo, procura o método na classe
        try:
            method = self.__klass.get_method(attr)
            # Vincula o método à instância atual
            return method.bind(self)
        except LoxError:
            raise AttributeError(attr)
    
    def __setattr__(self, attr, value):
        """
        self.__setattr__(self, "attr", value) <==> self.attr = value
        """
        # Se é um atributo especial (começa com __), usa o comportamento padrão
        if attr.startswith('_'):
            super().__setattr__(attr, value)
        else:
            # Caso contrário, armazena como campo da instância
            self.__fields[attr] = value


@dataclass
class LoxFunction:
    """
    Classe base para todas as funções Lox.
    """

    name: str
    params: list[str]
    body: "Stmt"
    ctx: Ctx
    is_method: bool = False

    def call(self, args: list["Value"], this=None):
        # Cria um novo escopo para a função
        function_ctx = self.ctx.push({})
        
        # Se é um método, define 'this' no contexto
        if this is not None:
            function_ctx.var_def("this", this)
        
        # Associa cada parâmetro com seu valor correspondente no novo escopo
        for param_name, arg in zip(self.params, args):
            function_ctx.var_def(param_name, arg)
        
        # Executa o corpo da função no novo contexto
        try:
            self.body.eval(function_ctx)
        except LoxReturn as ex:
            return ex.value
        
        # Se não há return explícito, retorna None
        return None

    def bind(self, obj: "Value") -> "LoxFunction":
        """
        Cria uma nova função com 'this' vinculado à instância.
        """
        # Cria um novo contexto com this vinculado à instância
        bound_ctx = self.ctx.push({"this": obj})
        return LoxFunction(self.name, self.params, self.body, bound_ctx, True)

    def __call__(self, *args):
        return self.call(args)


class LoxReturn(Exception):
    """
    Exceção para retornar de uma função Lox.
    """

    def __init__(self, value):
        self.value = value
        super().__init__()


class LoxError(Exception):
    """
    Exceção para erros de execução Lox.
    """


nan = float("nan")
inf = float("inf")


def print(value: "Value"):
    """
    Imprime um valor lox.
    """
    builtins.print(show(value))


def show(value: "Value") -> str:
    """
    Converte valor lox para string, seguindo a semântica do Lox.
    """
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        # Remove .0 se for inteiro
        s = str(value)
        if s.endswith('.0'):
            return s[:-2]
        return s
    if isinstance(value, str):
        return value
    # LoxFunction
    if hasattr(value, "__class__") and value.__class__.__name__ == "LoxFunction":
        return f"<fn {getattr(value, 'name', '?')}>"
    # LoxInstance
    if hasattr(value, "__class__") and value.__class__.__name__ == "LoxInstance":
        klass = getattr(value, '_LoxInstance__klass', None)
        if klass and hasattr(klass, 'name'):
            return f"{klass.name} instance"
        return "instance"
    # LoxClass
    if hasattr(value, "__class__") and value.__class__.__name__ == "LoxClass":
        return str(value)
    # Função nativa Python
    if isinstance(value, (FunctionType, BuiltinFunctionType)):
        return "<native fn>"
    # Por padrão, retorna o nome da classe
    return str(value)


def show_repr(value: "Value") -> str:
    """
    Mostra um valor lox, mas coloca aspas em strings.
    """
    if isinstance(value, str):
        return f'"{value}"'
    return show(value)


def truthy(value: "Value") -> bool:
    """
    Converte valor lox para booleano segundo a semântica do lox.
    """
    if value is None or value is False:
        return False
    return True


def not_(value):
    return not truthy(value)


# Operações matemáticas e comparações Lox

def add(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a + b
    if isinstance(a, str) and isinstance(b, str):
        return a + b
    raise LoxError("Operação '+' só é permitida entre números ou entre strings.")

def sub(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a - b
    raise LoxError("Operação '-' só é permitida entre números.")

def mul(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a * b
    raise LoxError("Operação '*' só é permitida entre números.")

def truediv(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a / b
    raise LoxError("Operação '/' só é permitida entre números.")

def ge(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a >= b
    raise LoxError("Comparação '>=' só é permitida entre números.")

def le(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a <= b
    raise LoxError("Comparação '<=' só é permitida entre números.")

def gt(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a > b
    raise LoxError("Comparação '>' só é permitida entre números.")

def lt(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return a < b
    raise LoxError("Comparação '<' só é permitida entre números.")

def eq(a, b):
    # Em Lox, valores de tipos diferentes nunca são iguais
    if type(a) != type(b):
        return False
    return a == b

def ne(a, b):
    return not eq(a, b)


@dataclass
class LoxClass:
    """
    Classe base para todas as classes Lox.
    """
    name: str
    methods: dict[str, LoxFunction]
    base: Optional["LoxClass"]

    def __call__(self, *args):
        """
        self.__call__(x, y) <==> self(x, y)

        Em Lox, criamos instâncias de uma classe chamando-a como uma função. É
        exatamente como em Python :)
        """
        # Por enquanto, retornamos instâncias genéricas
        return LoxInstance(self)

    def get_method(self, name: str) -> "LoxFunction":
        # Procure o método na classe atual. 
        # Se não encontrar, procure nas bases.
        # Se não existir em nenhum dos dois lugares, levante uma exceção do
        # tipo LoxError.
        if name in self.methods:
            return self.methods[name]
        
        if self.base:
            return self.base.get_method(name)
        
        raise LoxError(f"Undefined property '{name}'.")

    def __str__(self):
        return self.name

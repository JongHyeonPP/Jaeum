from dataclasses import dataclass
from typing import List, Any, Optional
from .tokens import Token

# Base Classes
class Stmt:
    pass

class Expr:
    pass

# Expressions
@dataclass
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Grouping(Expr):
    expression: Expr

@dataclass
class Literal(Expr):
    value: Any

@dataclass
class Unary(Expr):
    operator: Token
    right: Expr

@dataclass
class Variable(Expr):
    name: Token

@dataclass
class Assign(Expr):
    name: Token
    value: Expr

@dataclass
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr

@dataclass
class Call(Expr):
    callee: Expr
    paren: Token # For error reporting location
    arguments: List[Expr]

# Statements
@dataclass
class Expression(Stmt):
    expression: Expr

@dataclass
class Function(Stmt):
    name: Token
    params: List[Token]
    body: List[Stmt]

@dataclass
class If(Stmt):
    condition: Expr
    then_branch: 'Block' # Jaeum uses blocks strictly
    else_branch: Optional['Block']

@dataclass
class Print(Stmt):
    expression: Expr

@dataclass
class Return(Stmt):
    keyword: Token
    value: Expr

@dataclass
class Var(Stmt):
    name: Token
    initializer: Expr # Null/Undefined if not present

@dataclass
class While(Stmt):
    condition: Expr
    body: 'Block'

@dataclass
class Block(Stmt):
    statements: List[Stmt]

@dataclass
class Input(Stmt):
    name: Token

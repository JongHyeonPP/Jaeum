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
    paren: Token 
    arguments: List[Expr]

@dataclass
class ArrayLiteral(Expr):
    elements: List[Expr]
    bracket: Token 

@dataclass
class Get(Expr):
    object: Expr
    name: Expr # Can be index expression
    bracket: Token

@dataclass
class Set(Expr):
    object: Expr
    name: Expr
    value: Expr
    bracket: Token
    
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
    then_branch: 'Block' 
    else_branch: Optional['Block']

@dataclass
class Print(Stmt):
    expression: Expr

@dataclass
class Input(Stmt):
    name: Token

@dataclass
class FileWrite(Stmt):
    path: Expr
    content: Expr

@dataclass
class FileAppend(Stmt):
    path: Expr
    content: Expr

@dataclass
class FileRead(Stmt):
    path: Expr
    target_var: Token

@dataclass
class Return(Stmt):
    keyword: Token
    value: Expr

@dataclass
class While(Stmt):
    condition: Expr
    body: 'Block'

@dataclass
class Block(Stmt):
    statements: List[Stmt]

@dataclass
class Break(Stmt):
    keyword: Token

@dataclass
class Continue(Stmt):
    keyword: Token

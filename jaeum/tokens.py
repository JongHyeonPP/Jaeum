from enum import Enum, auto
from dataclasses import dataclass
from typing import Any

class TokenType(Enum):
    # End of File
    EOF = auto()
    
    # Identifiers & Literals
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    
    # Keywords (Consonants)
    VAR = auto()      # ㅄ (Variable)
    IF = auto()       # ㄹㅇ (Real? / If)
    ELSE = auto()     # ㄴㄴ (No No / Else)
    WHILE = auto()    # ㅁㅈ (Right / While)
    FOR = auto()      # ㅂㅂ (ByeBye? / For) - Actually just mapping, user defined logic
    BREAK = auto()    # ㅃ
    CONTINUE = auto() # ㅋ
    FUNC = auto()     # ㅎㅅ (Function)
    RETURN = auto()   # ㄹㅌ (Return)
    PRINT = auto()    # ㅊㄹ (Print)
    INPUT = auto()    # ㅇㄹ (Input)
    FILE_WRITE = auto() # ㅍㅇㅊㄹ (File Write)
    FILE_READ = auto()  # ㅍㅇㅇㄹ (File Read)
    
    # Constants
    TRUE = auto()     # ㅇ (Yes)
    FALSE = auto()    # ㄴ (No)
    NULL = auto()     # ㄴㄴㄴ (Null)
    UNDEFINED = auto() # ㄱ (Go? / Undefined)
    
    # Operators and Delimiters
    PLUS = auto()     # +
    MINUS = auto()    # -
    STAR = auto()     # *
    SLASH = auto()    # /
    PERCENT = auto()  # %
    
    EQUAL = auto()        # =
    EQUAL_EQUAL = auto()  # ==
    BANG = auto()         # !
    BANG_EQUAL = auto()   # !=
    LESS = auto()         # <
    LESS_EQUAL = auto()   # <=
    GREATER = auto()      # >
    GREATER_EQUAL = auto() # >=
    
    AND = auto()      # &&
    OR = auto()       # ||
    
    LPAREN = auto()   # (
    RPAREN = auto()   # )
    LBRACE = auto()   # {
    RBRACE = auto()   # }
    LBRACKET = auto() # [
    RBRACKET = auto() # ]
    SEMICOLON = auto() # ;
    COMMA = auto()    # ,

@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    
    def __repr__(self):
        return f"{self.type} {self.lexeme} {self.literal}"

# Keyword Map
KEYWORDS = {
    "ㅄ": TokenType.VAR,
    "ㄹㅇ": TokenType.IF,
    "ㄴㄴ": TokenType.ELSE,
    "ㅂㅂ1": TokenType.WHILE,
    "ㅂㅂ2": TokenType.FOR,
    "ㅃ": TokenType.BREAK,
    "ㄹㄹ": TokenType.CONTINUE,
    "ㅎㅅ": TokenType.FUNC,
    "ㄹㅌ": TokenType.RETURN,
    "ㅊㄹ": TokenType.PRINT,
    "ㅇㄹ": TokenType.INPUT,
    "ㅍㅇㅊㄹ": TokenType.FILE_WRITE,
    "ㅍㅇㅇㄹ": TokenType.FILE_READ,
    "ㅇ": TokenType.TRUE,
    "ㄴ": TokenType.FALSE,
    "ㄴㄴㄴ": TokenType.NULL,
    "ㅇㅅ": TokenType.UNDEFINED,
}

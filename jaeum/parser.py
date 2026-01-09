from typing import List, Optional
from .tokens import TokenType, Token
from . import ast_nodes as ast

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> List[ast.Stmt]:
        statements = []
        while not self.is_at_end():
            decl = self.declaration()
            if decl:
                statements.append(decl)
        return statements

    # Declarations
    def declaration(self) -> Optional[ast.Stmt]:
        try:
            if self.match(TokenType.FUNC):
                return self.function("function")
            if self.match(TokenType.VAR):
                return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return None

    def function(self, kind: str) -> ast.Function:
        name = self.consume(TokenType.IDENTIFIER, f"Expect {kind} name.")
        self.consume(TokenType.LPAREN, f"Expect '(' after {kind} name.")
        parameters = []
        if not self.check(TokenType.RPAREN):
            while True:
                parameters.append(self.consume(TokenType.IDENTIFIER, "Expect parameter name."))
                if not self.match(TokenType.COMMA):
                    break
        self.consume(TokenType.RPAREN, "Expect ')' after parameters.")
        self.consume(TokenType.LBRACE, f"Expect '{{' before {kind} body.")
        body = self.block()
        return ast.Function(name, parameters, body.statements)

    def var_declaration(self) -> ast.Var:
        name = self.consume(TokenType.IDENTIFIER, "Expect variable name.")
        initializer = None
        if self.match(TokenType.EQUAL):
            initializer = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after variable declaration.")
        return ast.Var(name, initializer)

    # Statements
    def statement(self) -> ast.Stmt:
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.WHILE):
            return self.while_statement()
        if self.match(TokenType.FOR):
            return self.for_statement()
        if self.match(TokenType.PRINT):
            return self.print_statement()
        if self.match(TokenType.INPUT):
            return self.input_statement()
        if self.match(TokenType.FILE_WRITE):
            return self.file_write_statement()
        if self.match(TokenType.FILE_READ):
            return self.file_read_statement()
        if self.match(TokenType.RETURN):
            return self.return_statement()
        if self.match(TokenType.LBRACE):
            return self.block()
        return self.expression_statement()

    def if_statement(self) -> ast.If:
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㄹㅇ'.")
        condition = self.expression()
        self.consume(TokenType.RPAREN, "Expect ')' after if condition.")
        
        # Block is mandatory in Jaeum design
        self.consume(TokenType.LBRACE, "Expect '{' before if body.")
        then_branch = self.block()
        
        else_branch = None
        if self.match(TokenType.ELSE):
            self.consume(TokenType.LBRACE, "Expect '{' after 'ㄴㄴ'.")
            else_branch = self.block()
            
        return ast.If(condition, then_branch, else_branch)

    def while_statement(self) -> ast.While:
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㅂㅂ1'.")
        condition = self.expression()
        self.consume(TokenType.RPAREN, "Expect ')' after while condition.")
        self.consume(TokenType.LBRACE, "Expect '{' before while body.")
        body = self.block()
        return ast.While(condition, body)
        
    def for_statement(self) -> ast.Stmt:
        # Desugar For to block with while
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㅂㅂ2'.")
        
        initializer = None
        if self.match(TokenType.SEMICOLON):
            initializer = None
        elif self.match(TokenType.VAR):
            initializer = self.var_declaration()
        else:
            initializer = self.expression_statement()
        
        condition = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after loop condition.")
        
        increment = None
        if not self.check(TokenType.RPAREN):
            increment = self.expression()
        self.consume(TokenType.RPAREN, "Expect ')' after for clauses.")
        
        self.consume(TokenType.LBRACE, "Expect '{' before loop body.")
        body = self.block()
        
        # Desugaring
        if increment is not None:
            body.statements.append(ast.Expression(increment))
        
        if condition is None:
            condition = ast.Literal(True)
            
        body = ast.While(condition, body)
        
        if initializer is not None:
            body = ast.Block([initializer, body])
            
        return body

    def print_statement(self) -> ast.Print:
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㅊㄹ'.")
        value = self.expression()
        self.consume(TokenType.RPAREN, "Expect ')' after value.")
        self.consume(TokenType.SEMICOLON, "Expect ';' after value.")
        return ast.Print(value)

    def input_statement(self) -> ast.Input:
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㅇㄹ'.")
        name = self.consume(TokenType.IDENTIFIER, "Expect variable name for input.")
        self.consume(TokenType.RPAREN, "Expect ')' after variable name.")
        self.consume(TokenType.SEMICOLON, "Expect ';' after input statement.")
        return ast.Input(name)

    def file_write_statement(self) -> ast.FileWrite:
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㅍㅇㅊㄹ'.")
        path = self.expression()
        self.consume(TokenType.COMMA, "Expect ',' between path and content.")
        content = self.expression()
        self.consume(TokenType.RPAREN, "Expect ')' after content.")
        self.consume(TokenType.SEMICOLON, "Expect ';' after file write.")
        # ㅍㅇㅊㄹ(경로, 내용);
        return ast.FileWrite(path, content)

    def file_read_statement(self) -> ast.FileRead:
        self.consume(TokenType.LPAREN, "Expect '(' after 'ㅍㅇㅇㄹ'.")
        target = self.consume(TokenType.IDENTIFIER, "Expect variable name to store file content.")
        self.consume(TokenType.COMMA, "Expect ',' between variable and path.")
        path = self.expression()
        self.consume(TokenType.RPAREN, "Expect ')' after path.")
        self.consume(TokenType.SEMICOLON, "Expect ';' after file read.")
        # ㅍㅇㅇㄹ(변수, 경로);
        return ast.FileRead(path, target)

    def return_statement(self) -> ast.Return:
        keyword = self.previous()
        value = None
        if not self.check(TokenType.SEMICOLON):
            value = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after return value.")
        return ast.Return(keyword, value)

    def expression_statement(self) -> ast.Expression:
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Expect ';' after expression.")
        return ast.Expression(expr)

    def block(self) -> ast.Block:
        statements = []
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            statements.append(self.declaration())
        self.consume(TokenType.RBRACE, "Expect '}' after block.")
        return ast.Block(statements)

    # Expressions
    def expression(self) -> ast.Expr:
        return self.assignment()

    def assignment(self) -> ast.Expr:
        expr = self.or_expr()
        if self.match(TokenType.EQUAL):
            equals = self.previous()
            value = self.assignment()
            if isinstance(expr, ast.Variable):
                name = expr.name
                return ast.Assign(name, value)
            elif isinstance(expr, ast.Get):
                return ast.Set(expr.object, expr.name, value, expr.bracket)
            self.error(equals, "Invalid assignment target.")
        return expr

    def or_expr(self) -> ast.Expr:
        expr = self.and_expr()
        while self.match(TokenType.OR):
            operator = self.previous()
            right = self.and_expr()
            expr = ast.Logical(expr, operator, right)
        return expr

    def and_expr(self) -> ast.Expr:
        expr = self.equality()
        while self.match(TokenType.AND):
            operator = self.previous()
            right = self.equality()
            expr = ast.Logical(expr, operator, right)
        return expr

    def equality(self) -> ast.Expr:
        expr = self.comparison()
        while self.match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            operator = self.previous()
            right = self.comparison()
            expr = ast.Binary(expr, operator, right)
        return expr

    def comparison(self) -> ast.Expr:
        expr = self.term()
        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            operator = self.previous()
            right = self.term()
            expr = ast.Binary(expr, operator, right)
        return expr

    def term(self) -> ast.Expr:
        expr = self.factor()
        while self.match(TokenType.MINUS, TokenType.PLUS):
            operator = self.previous()
            right = self.factor()
            expr = ast.Binary(expr, operator, right)
        return expr

    def factor(self) -> ast.Expr:
        expr = self.unary()
        while self.match(TokenType.SLASH, TokenType.STAR, TokenType.PERCENT):
            operator = self.previous()
            right = self.unary()
            expr = ast.Binary(expr, operator, right)
        return expr

    def unary(self) -> ast.Expr:
        if self.match(TokenType.BANG, TokenType.MINUS):
            operator = self.previous()
            right = self.unary()
            return ast.Unary(operator, right)
        return self.call()

    def call(self) -> ast.Expr:
        expr = self.primary()
        while True:
            if self.match(TokenType.LPAREN):
                expr = self.finish_call(expr)
            elif self.match(TokenType.LBRACKET):
                expr = self.finish_index(expr)
            else:
                break
        return expr

    def finish_index(self, object: ast.Expr) -> ast.Expr:
        name = self.expression()
        bracket = self.consume(TokenType.RBRACKET, "Expect ']' after index.")
        return ast.Get(object, name, bracket)

    def finish_call(self, callee: ast.Expr) -> ast.Expr:
        arguments = []
        if not self.check(TokenType.RPAREN):
            while True:
                arguments.append(self.expression())
                if not self.match(TokenType.COMMA):
                    break
        paren = self.consume(TokenType.RPAREN, "Expect ')' after arguments.")
        return ast.Call(callee, paren, arguments)

    def primary(self) -> ast.Expr:
        if self.match(TokenType.FALSE): return ast.Literal(False)
        if self.match(TokenType.TRUE): return ast.Literal(True)
        if self.match(TokenType.NULL): return ast.Literal(None)
        if self.match(TokenType.UNDEFINED): return ast.Literal("UNDEFINED")
                                                                         # Python has no undefined. Let's use string "UNDEFINED" or special object.
                                                                         # Let's use None for Null and maybe ... (Ellipsis) for Undefined?
                                                                         # Or just a string "UNDEFINED". Design says 'ㄱ' is undefined.
                                                                         # Better: define a singleton.
        
        if self.match(TokenType.NUMBER, TokenType.STRING):
            return ast.Literal(self.previous().literal)
        
        if self.match(TokenType.IDENTIFIER):
            return ast.Variable(self.previous())
        
        if self.match(TokenType.LPAREN):
            expr = self.expression()
            self.consume(TokenType.RPAREN, "Expect ')' after expression.")
            return ast.Grouping(expr)
            
        if self.match(TokenType.LBRACKET):
            elements = []
            if not self.check(TokenType.RBRACKET):
                while True:
                    elements.append(self.expression())
                    if not self.match(TokenType.COMMA):
                        break
            bracket = self.consume(TokenType.RBRACKET, "Expect ']' after array elements.")
            return ast.ArrayLiteral(elements, bracket)

        raise self.error(self.peek(), "Expect expression.")

    # Helpers
    def match(self, *types) -> bool:
        for type in types:
            if self.check(type):
                self.advance()
                return True
        return False

    def check(self, type) -> bool:
        if self.is_at_end(): return False
        return self.peek().type == type

    def advance(self) -> Token:
        if not self.is_at_end(): self.current += 1
        return self.previous()

    def is_at_end(self) -> bool:
        return self.peek().type == TokenType.EOF

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def consume(self, type, message: str) -> Token:
        if self.check(type): return self.advance()
        raise self.error(self.peek(), message)

    def error(self, token: Token, message: str):
        # Implementation Detail: Simple error raising
        return ParseError(f"[Line {token.line}] {message}")

    def synchronize(self):
        self.advance()
        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON: return
            if self.peek().type in [
                TokenType.FUNC, TokenType.VAR, TokenType.FOR,
                TokenType.IF, TokenType.WHILE, TokenType.PRINT,
                TokenType.RETURN, TokenType.INPUT
            ]:
                return
            self.advance()


from typing import Any, List, Optional
from .tokens import TokenType, Token
from . import ast_nodes as ast
import sys

# Constants
UNDEFINED = "UNDEFINED"

class RuntimeError(Exception):
    def __init__(self, token: Token, message: str):
        super().__init__(message)
        self.token = token

class Return(Exception):
    def __init__(self, value: Any):
        self.value = value

class Break(Exception): pass
class Continue(Exception): pass

class Environment:
    def __init__(self, enclosing: Optional['Environment'] = None):
        self.values = {}
        self.enclosing = enclosing

    def define(self, name: str, value: Any):
        self.values[name] = value

    def get(self, name: Token) -> Any:
        if name.lexeme in self.values:
            return self.values[name.lexeme]
        
        if self.enclosing:
            return self.enclosing.get(name)

        raise RuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def assign(self, name: Token, value: Any):
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing:
            self.enclosing.assign(name, value)
            return

        raise RuntimeError(name, f"Undefined variable '{name.lexeme}'.")

class Interpreter:
    def __init__(self):
        self.globals = Environment()
        self.environment = self.globals
        
        # Built-in Functions should be defined here
        # self.globals.define("clock", ...) 

    def interpret(self, statements: List[ast.Stmt]):
        try:
            for statement in statements:
                self.execute(statement)
        except RuntimeError as error:
            print(f"{error}\n[Line {error.token.line}]", file=sys.stderr)

    def execute(self, stmt: ast.Stmt):
        # Visit pattern manual dispatch
        method_name = 'visit_' + type(stmt).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(stmt)

    def evaluate(self, expr: ast.Expr) -> Any:
        method_name = 'visit_' + type(expr).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(expr)

    def generic_visit(self, node):
        raise Exception(f"No visit_{type(node).__name__} method")

    # Statements
    def visit_Block(self, stmt: ast.Block):
        self.execute_block(stmt.statements, Environment(self.environment))

    def execute_block(self, statements: List[ast.Stmt], environment: Environment):
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous

    def visit_Expression(self, stmt: ast.Expression):
        self.evaluate(stmt.expression)

    def visit_Function(self, stmt: ast.Function):
        # Capture current environment for closure
        closure = stmt # Function AST IS the function object in simple interpreters
        # Ideally we wrap it in a Callable class
        # But for basics, we can store AST and Env.
        self.environment.define(stmt.name.lexeme, JaeumFunction(stmt, self.environment))

    def visit_If(self, stmt: ast.If):
        if self.is_truthy(self.evaluate(stmt.condition)):
            self.execute(stmt.then_branch)
        elif stmt.else_branch:
            self.execute(stmt.else_branch)

    def visit_Print(self, stmt: ast.Print):
        value = self.evaluate(stmt.expression)
        print(self.stringify(value))

    def visit_Input(self, stmt: ast.Input):
        # ㅇㄹ(variable);
        # Get input string
        try:
            val = input()
        except EOFError:
            val = None # Null on failure
            
        # Target must be variable
        var_name = stmt.name
        self.environment.assign(var_name, val)

    def visit_Return(self, stmt: ast.Return):
        value = None
        if stmt.value:
            value = self.evaluate(stmt.value)
        raise Return(value)

    def visit_Var(self, stmt: ast.Var):
        value = UNDEFINED
        if stmt.initializer:
            value = self.evaluate(stmt.initializer)
        self.environment.define(stmt.name.lexeme, value)

    def visit_While(self, stmt: ast.While):
        while self.is_truthy(self.evaluate(stmt.condition)):
            try:
                self.execute(stmt.body)
            except Break:
                break
            except Continue:
                pass # Loop continues

    # Expressions
    def visit_Assign(self, expr: ast.Assign):
        value = self.evaluate(expr.value)
        self.environment.assign(expr.name, value)
        return value

    def visit_Binary(self, expr: ast.Binary):
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        
        op = expr.operator.type
        if op == TokenType.PLUS:
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            if isinstance(left, str) or isinstance(right, str):
                return self.stringify(left) + self.stringify(right)
            raise RuntimeError(expr.operator, "Operands must be two numbers or two strings.")
        
        if op == TokenType.MINUS: return self.check_number_operands(expr.operator, left, right) and left - right
        if op == TokenType.SLASH: 
            if right == 0: raise RuntimeError(expr.operator, "Division by zero.")
            return self.check_number_operands(expr.operator, left, right) and left / right # Float division by default?
            # Or integer division if both ints?
            # Design says dynamic. Python / gives float. // gives int.
            # Let's simple / for now.
        if op == TokenType.STAR: return self.check_number_operands(expr.operator, left, right) and left * right
        if op == TokenType.PERCENT: return self.check_number_operands(expr.operator, left, right) and left % right
        
        if op == TokenType.GREATER: return self.check_number_operands(expr.operator, left, right) and left > right
        if op == TokenType.GREATER_EQUAL: return self.check_number_operands(expr.operator, left, right) and left >= right
        if op == TokenType.LESS: return self.check_number_operands(expr.operator, left, right) and left < right
        if op == TokenType.LESS_EQUAL: return self.check_number_operands(expr.operator, left, right) and left <= right
        
        if op == TokenType.BANG_EQUAL: return not self.is_equal(left, right)
        if op == TokenType.EQUAL_EQUAL: return self.is_equal(left, right)

        return None

    def visit_Call(self, expr: ast.Call):
        callee = self.evaluate(expr.callee)
        arguments = [self.evaluate(arg) for arg in expr.arguments]
        
        if not hasattr(callee, 'call'):
            raise RuntimeError(expr.paren, "Can only call functions and classes.")
            
        function = callee
        if len(arguments) != function.arity():
            raise RuntimeError(expr.paren, f"Expected {function.arity()} arguments but got {len(arguments)}.")
            
        return function.call(self, arguments)

    def visit_Grouping(self, expr: ast.Grouping):
        return self.evaluate(expr.expression)

    def visit_Literal(self, expr: ast.Literal):
        return expr.value

    def visit_Logical(self, expr: ast.Logical):
        left = self.evaluate(expr.left)
        
        if expr.operator.type == TokenType.OR:
            if self.is_truthy(left): return left
        else: # AND
            if not self.is_truthy(left): return left
            
        return self.evaluate(expr.right)

    def visit_Unary(self, expr: ast.Unary):
        right = self.evaluate(expr.right)
        
        if expr.operator.type == TokenType.MINUS:
            self.check_number_operand(expr.operator, right)
            return -right
        if expr.operator.type == TokenType.BANG:
            return not self.is_truthy(right)
            
        return None

    def visit_Variable(self, expr: ast.Variable):
        return self.environment.get(expr.name)

    # Helpers
    def check_number_operand(self, operator: Token, operand: Any):
        if isinstance(operand, (int, float)): return
        raise RuntimeError(operator, "Operand must be a number.")

    def check_number_operands(self, operator: Token, left: Any, right: Any):
        if isinstance(left, (int, float)) and isinstance(right, (int, float)): return True
        raise RuntimeError(operator, "Operands must be numbers.")

    def is_truthy(self, object: Any) -> bool:
        if object is None: return False
        if object is False: return False
        if object == 0: return False
        if object == UNDEFINED: return False
        return True

    def is_equal(self, a: Any, b: Any) -> bool:
        if a is None and b is None: return True
        if a is None: return False
        return a == b

    def stringify(self, object: Any) -> str:
        if object is None: return "ㄴㄴㄴ"
        if object == UNDEFINED: return "ㄱ"
        if object is True: return "ㅇ"
        if object is False: return "ㄴ"
        if isinstance(object, float):
            text = str(object)
            if text.endswith(".0"):
                text = text[:-2]
            return text
        return str(object)

class JaeumCallable:
    def call(self, interpreter: Interpreter, arguments: List[Any]) -> Any:
        pass
    def arity(self) -> int:
        pass

class JaeumFunction(JaeumCallable):
    def __init__(self, declaration: ast.Function, closure: Environment):
        self.declaration = declaration
        self.closure = closure

    def call(self, interpreter: Interpreter, arguments: List[Any]) -> Any:
        environment = Environment(self.closure)
        for i, param in enumerate(self.declaration.params):
            environment.define(param.lexeme, arguments[i])
            
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except Return as return_value:
            return return_value.value
            
        return None # Default return

    def arity(self) -> int:
        return len(self.declaration.params)

    def __str__(self):
        return f"<fn {self.declaration.name.lexeme}>"

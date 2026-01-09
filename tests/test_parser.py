import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jaeum.lexer import Lexer
from jaeum.parser import Parser
from jaeum import ast_nodes as ast
from jaeum.tokens import TokenType

class TestParser(unittest.TestCase):
    def parse(self, source):
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        parser = Parser(tokens)
        return parser.parse()

    def test_var_declaration(self):
        stmts = self.parse('ㅄ x = 10;')
        self.assertIsInstance(stmts[0], ast.Var)
        self.assertEqual(stmts[0].name.lexeme, 'x')
        self.assertEqual(stmts[0].initializer.value, 10)

    def test_print_statement(self):
        stmts = self.parse('ㅍㅌ("Hello");')
        self.assertIsInstance(stmts[0], ast.Print)
        self.assertEqual(stmts[0].expression.value, "Hello")

    def test_binary_expression(self):
        stmts = self.parse('Variable = 1 + 2 * 3;') 
        # Variable name 'Variable' is valid identifier? First char 'V' is alpha.
        # But wait, parser expects declaration or statement.
        # 'Variable = ...' is an ExpressionStatement (Assignment)
        # But 'Variable' matches identifier.
        self.assertIsInstance(stmts[0], ast.Expression)
        assign = stmts[0].expression
        self.assertIsInstance(assign, ast.Assign)
        
        # 1 + 2 * 3 -> 1 + (2 * 3) -> Binary(1, +, Binary(2, *, 3))
        # Wait, assignment value is the binary expr
        root = assign.value
        self.assertIsInstance(root, ast.Binary)
        self.assertEqual(root.operator.type, TokenType.PLUS)
        self.assertEqual(root.left.value, 1)
        self.assertEqual(root.right.operator.type, TokenType.STAR)  

    def test_if_block(self):
        source = 'ㄹㅇ (x > 10) { ㅍㅌ(x); }'
        stmts = self.parse(source)
        self.assertIsInstance(stmts[0], ast.If)
        self.assertIsInstance(stmts[0].then_branch, ast.Block)
        self.assertEqual(len(stmts[0].then_branch.statements), 1)

if __name__ == '__main__':
    unittest.main()

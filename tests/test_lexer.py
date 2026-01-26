import unittest
import sys
import os

# Add parent directory to path to import jaeum
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jaeum.lexer import Lexer
from jaeum.tokens import TokenType

class TestLexer(unittest.TestCase):
    def test_basic_assignment(self):
        source = 'x = 10;'
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].lexeme, 'x')
        self.assertEqual(tokens[1].type, TokenType.EQUAL)
        self.assertEqual(tokens[2].type, TokenType.NUMBER)
        self.assertEqual(tokens[2].literal, 10)
        self.assertEqual(tokens[3].type, TokenType.SEMICOLON)
        self.assertEqual(tokens[4].type, TokenType.EOF)

    def test_korean_identifiers(self):
        source = '점수 = 100;'
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        
        self.assertEqual(tokens[0].lexeme, '점수')

    def test_max_munch_keywords(self):
        # ㄴ (FALSE), ㄴㄴ (ELSE), ㄴㄴㄴ (NULL)
        source = 'ㄴ ㄴㄴ ㄴㄴㄴ'
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        
        self.assertEqual(tokens[0].type, TokenType.FALSE)
        self.assertEqual(tokens[1].type, TokenType.ELSE)
        self.assertEqual(tokens[2].type, TokenType.NULL)

    def test_operators(self):
        source = '== != <= >='
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        
        self.assertEqual(tokens[0].type, TokenType.EQUAL_EQUAL)
        self.assertEqual(tokens[1].type, TokenType.BANG_EQUAL)
        self.assertEqual(tokens[2].type, TokenType.LESS_EQUAL)
        self.assertEqual(tokens[3].type, TokenType.GREATER_EQUAL)

if __name__ == '__main__':
    unittest.main()

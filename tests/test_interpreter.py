import unittest
import sys
import os
import io
from contextlib import redirect_stdout

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jaeum.lexer import Lexer
from jaeum.parser import Parser
from jaeum.interpreter import Interpreter

class TestInterpreter(unittest.TestCase):
    def run_script(self, source):
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        parser = Parser(tokens)
        statements = parser.parse()
        interpreter = Interpreter()
        interpreter.interpret(statements)
        return interpreter

    def test_arithmetic(self):
        # We can't easily check internal state unless we expose environment or capture print
        # Let's use print capturing
        source = 'ㅊㄹ(1 + 2 * 3);'
        f = io.StringIO()
        with redirect_stdout(f):
            self.run_script(source)
        self.assertEqual(f.getvalue().strip(), "7")

    def test_variable_scope(self):
        source = """
        ㅄ a = "global";
        {
            ㅄ a = "local";
            ㅊㄹ(a);
        }
        ㅊㄹ(a);
        """
        f = io.StringIO()
        with redirect_stdout(f):
            self.run_script(source)
        output = f.getvalue().strip().split('\n')
        self.assertEqual(output[0].strip(), "local")
        self.assertEqual(output[1].strip(), "global")

    def test_if_logic(self):
        source = """
        ㄹㅇ (ㅇ) { ㅊㄹ("true"); }
        ㄹㅇ (ㄴ) { ㅊㄹ("false"); }
        """
        f = io.StringIO()
        with redirect_stdout(f):
            self.run_script(source)
        self.assertEqual(f.getvalue().strip(), "true")

    def test_function_return(self):
        source = """
        ㅎㅅ add(a, b) {
            ㄹㅌ a + b;
        }
        ㅊㄹ(add(10, 20));
        """
        f = io.StringIO()
        with redirect_stdout(f):
            self.run_script(source)
        self.assertEqual(f.getvalue().strip(), "30")

    def test_recursion(self):
        source = """
        ㅎㅅ fib(n) {
            ㄹㅇ (n <= 1) { ㄹㅌ n; }
            ㄹㅌ fib(n - 1) + fib(n - 2);
        }
        ㅊㄹ(fib(6));
        """
        # fib(6) = 8
        f = io.StringIO()
        with redirect_stdout(f):
            self.run_script(source)
        self.assertEqual(f.getvalue().strip(), "8")

if __name__ == '__main__':
    unittest.main()

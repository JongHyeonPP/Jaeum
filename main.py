import sys
from jaeum.lexer import Lexer
from jaeum.parser import Parser
from jaeum.interpreter import Interpreter

def run(source: str):
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()
    
    # Optional: Debug tokens
    # for token in tokens: print(token)
    
    parser = Parser(tokens)
    statements = parser.parse()
    
    # Parser error handling should stop here if we implemented it fully
    # Currently parser raises exceptions on error
    
    interpreter = Interpreter()
    interpreter.interpret(statements)

def run_file(path: str):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
            run(source)
    except FileNotFoundError:
        print(f"Error: File '{path}' not found.")
    except Exception as e:
        print(f"Error: {e}")

def run_prompt():
    print("Jaeum (ㅈㅇ) Interpreter")
    while True:
        try:
            line = input("> ")
            if not line: break
            run(line)
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        run_prompt()

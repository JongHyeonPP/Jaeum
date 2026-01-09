import sys
import os
import subprocess
from jaeum.lexer import Lexer
from jaeum.parser import Parser
from jaeum.compiler import Compiler

# Determine the base path where tools directory is located
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.getcwd()

TOOLS_DIR = os.path.join(BASE_DIR, "tools")
NASM_PATH = os.path.join(TOOLS_DIR, "nasm.exe")
GOLINK_PATH = os.path.join(TOOLS_DIR, "golink.exe")

def compile_file(source_path):
    source_path = os.path.abspath(source_path)
    base_name = os.path.splitext(source_path)[0]
    
    print(f"Jaeum Compiler (jaeumc) - Compiling '{source_path}'...")
    
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: File '{source_path}' not found.")
        sys.exit(1)
    
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()
    parser = Parser(tokens)
    statements = parser.parse()
    
    compiler = Compiler()
    asm_code = compiler.compile(statements)
    
    asm_path = base_name + ".asm"
    with open(asm_path, "w", encoding="utf-8") as f:
        f.write(asm_code)
        
    # 2. Assemble (NASM)
    obj_path = base_name + ".obj"
    if not os.path.exists(NASM_PATH):
        print(f"Error: NASM not found at {NASM_PATH}")
        sys.exit(1)
        
    print(f"Assembling...")
    try:
        subprocess.run([NASM_PATH, "-f", "win64", asm_path, "-o", obj_path], check=True)
    except subprocess.CalledProcessError:
        print("Error: NASM assembly failed.")
        sys.exit(1)

    # 3. Link (GoLink)
    exe_path = base_name + ".exe"
    if not os.path.exists(GOLINK_PATH):
        print(f"Error: GoLink not found at {GOLINK_PATH}")
        sys.exit(1)
        
    print(f"Linking...")
    # golink /entry Start /console kernel32.dll msvcrt.dll obj_path
    try:
        subprocess.run([GOLINK_PATH, "/entry", "Start", "/console", "kernel32.dll", "msvcrt.dll", obj_path], check=True)
    except subprocess.CalledProcessError:
        print("Error: Linking failed.")
        sys.exit(1)
        
    print(f"Build Successful: {exe_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: jaeumc <script.jm>")
    else:
        compile_file(sys.argv[1])

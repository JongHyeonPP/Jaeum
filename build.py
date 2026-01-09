import sys
import os
import subprocess
from jaeum.lexer import Lexer
from jaeum.parser import Parser
from jaeum.compiler import Compiler

def compile_file(source_path):
    # 1. Compile to ASM
    print(f"[1/3] Compiling '{source_path}' to ASM...")
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()
    parser = Parser(tokens)
    statements = parser.parse()
    
    compiler = Compiler()
    asm_code = compiler.compile(statements)
    
    asm_path = source_path.replace(".jm", ".asm")
    with open(asm_path, "w", encoding="utf-8") as f:
        f.write(asm_code)
        
    # 2. Assemble (NASM)
    obj_path = source_path.replace(".jm", ".obj")
    nasm_cmd = f"tools\\nasm.exe -f win64 {asm_path} -o {obj_path}"
    print(f"[2/3] Assembling: {nasm_cmd}")
    ret = os.system(nasm_cmd)
    if ret != 0:
        print("Error: NASM assembly failed.")
        return

    # 3. Link (GoLink)
    exe_path = source_path.replace(".jm", ".exe")
    # Link with msvcrt.dll for printf
    link_cmd = f"tools\\golink.exe /entry Start /console kernel32.dll msvcrt.dll {obj_path}"
    print(f"[3/3] Linking: {link_cmd}")
    ret = os.system(link_cmd)
    if ret != 0:
        print("Error: Linking failed.")
        return
        
    print(f"Success! Output: {exe_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build.py <script.jm>")
    else:
        compile_file(sys.argv[1])

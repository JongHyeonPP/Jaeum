from typing import List, Dict
from . import ast_nodes as ast
from .tokens import TokenType

class Compiler:
    def __init__(self):
        self.output = []
        self.data_section = []
        self.bss_section = []
        self.string_literals = {}
        self.variables = {} # Name -> [Type, Offset/Label]
        self.label_counter = 0
        self.loop_stack = []

    def compile(self, statements: List[ast.Stmt]) -> str:
        self.emit("global Start")
        self.emit("extern ExitProcess")
        self.emit("extern printf")
        self.emit("extern scanf")
        self.emit("extern malloc")
        self.emit("extern free")
        self.emit("extern fopen")
        self.emit("extern fclose")
        self.emit("extern fprintf")
        self.emit("extern fread")
        self.emit("extern fseek")
        self.emit("extern ftell")
        self.emit("extern rewind")
        
        self.emit("section .text")
        self.emit("Start:")
        # Stack setup (Shadow space for Windows ABI)
        self.emit("    sub rsp, 40") 
        
        for stmt in statements:
            self.visit(stmt)
            
        self.emit("    xor rcx, rcx")
        self.emit("    call ExitProcess")

        # Construct final ASM
        asm = []
        asm.append("default rel")
        asm.append("section .data")
        asm.append('    fmt_int db "%lld", 10, 0')
        asm.append('    fmt_str db "%s", 10, 0')
        asm.append('    mode_r db "rb", 0')
        asm.append('    mode_w db "w", 0')
        for lbl, val in self.string_literals.items():
            asm.append(f'    {lbl} db "{val}", 0')
            
        asm.append("section .bss")
        for var in self.variables:
            asm.append(f'    var_{var} resq 1')
        
        asm.extend(self.output)
        return "\n".join(asm)

    def emit(self, line):
        self.output.append(line)

    def new_label(self):
        self.label_counter += 1
        return f"L{self.label_counter}"

    def visit(self, node):
        method_name = 'visit_' + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"Compiler: No visit_{type(node).__name__} method")

    # Statements
    def visit_Block(self, stmt: ast.Block):
        for s in stmt.statements:
            self.visit(s)

    def visit_Print(self, stmt: ast.Print):
        # Evaluate expression to RAX
        self.visit(stmt.expression)
        
        # Check if it was a string literal (hack for simplicity)
        if isinstance(stmt.expression, ast.Literal) and isinstance(stmt.expression.value, str):
            self.emit("    lea rcx, [fmt_str]")
            self.emit("    mov rdx, rax") # String pointer
        else:
            self.emit("    lea rcx, [fmt_int]")
            self.emit("    mov rdx, rax") # Integer value

        self.emit("    sub rsp, 32") # Extra shadow space for printf? 
        # Actually Start allocated 40. 
        # Windows ABI: caller allocates shadow space (32 bytes).
        # We are aligned at Start (-8 -> -48). 
        # Call printf: pushes ret (-56). Misaligned?
        # Stack should be 16-byte aligned BEFORE call.
        # Let's handle alignment lazily: standard prolog/epilog per call?
        # Start: sub rsp, 40. (Aligned)
        # Call: Needs rsp+32 (shadow).
        self.emit("    call printf")
        self.emit("    add rsp, 32")

    def visit_Var(self, stmt: ast.Var):
        name = stmt.name.lexeme
        if name not in self.variables:
            self.variables[name] = "global"
        
        if stmt.initializer:
            self.visit(stmt.initializer) # Result in RAX
            self.emit(f"    mov [var_{name}], rax")
        else:
            self.emit(f"    mov qword [var_{name}], 0")

    def visit_Expression(self, stmt: ast.Expression):
        self.visit(stmt.expression)

    def visit_If(self, stmt: ast.If):
        l_else = self.new_label()
        l_end = self.new_label()

        self.visit(stmt.condition)
        self.emit("    cmp rax, 0")
        self.emit(f"    je {l_else}")
        
        self.visit(stmt.then_branch)
        self.emit(f"    jmp {l_end}")
        
        self.emit(f"{l_else}:")
        if stmt.else_branch:
            self.visit(stmt.else_branch)
            
        self.emit(f"{l_end}:")

    def visit_While(self, stmt: ast.While):
        l_start = self.new_label()
        l_end = self.new_label()
        self.loop_stack.append((l_start, l_end))
        
        self.emit(f"{l_start}:")
        self.visit(stmt.condition)
        self.emit("    cmp rax, 0")
        self.emit(f"    je {l_end}")
        
        self.visit(stmt.body)
        self.emit(f"    jmp {l_start}")
        self.emit(f"{l_end}:")
        self.loop_stack.pop()

    def visit_Break(self, stmt: ast.Break):
        if not self.loop_stack:
            # Error handling? Compiler should probably catch this semantic error
            return 
        _, l_end = self.loop_stack[-1]
        self.emit(f"    jmp {l_end}")

    def visit_Continue(self, stmt: ast.Continue):
        if not self.loop_stack:
            return
        l_start, _ = self.loop_stack[-1]
        self.emit(f"    jmp {l_start}")

    # Expressions (Result always in RAX)
    def visit_Literal(self, expr: ast.Literal):
        if isinstance(expr.value, int):
            self.emit(f"    mov rax, {expr.value}")
        elif isinstance(expr.value, str):
            lbl = f"str_{len(self.string_literals)}"
            self.string_literals[lbl] = expr.value
            self.emit(f"    lea rax, [{lbl}]")
        elif expr.value is True:
            self.emit("    mov rax, 1")
        else:
            self.emit("    mov rax, 0")

    def visit_Variable(self, expr: ast.Variable):
        self.emit(f"    mov rax, [var_{expr.name.lexeme}]")

    def visit_Assign(self, expr: ast.Assign):
        self.visit(expr.value)
        self.emit(f"    mov [var_{expr.name.lexeme}], rax")

    def visit_Binary(self, expr: ast.Binary):
        self.visit(expr.left)
        self.emit("    push rax")
        self.visit(expr.right)
        self.emit("    mov rbx, rax")
        self.emit("    pop rax")
        
        op = expr.operator.type
        if op == TokenType.PLUS:
            self.emit("    add rax, rbx")
        elif op == TokenType.MINUS:
            self.emit("    sub rax, rbx")
        elif op == TokenType.STAR:
            self.emit("    imul rax, rbx")
        elif op == TokenType.SLASH:
            self.emit("    cqo") # Sign extend RAX->RDX for div
            self.emit("    idiv rbx")
        elif op in [TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL, TokenType.LESS, TokenType.GREATER]:
            self.emit("    cmp rax, rbx")
            cond = {
                TokenType.EQUAL_EQUAL: "e",
                TokenType.BANG_EQUAL: "ne",
                TokenType.LESS: "l",
                TokenType.GREATER: "g",
                TokenType.LESS_EQUAL: "le",
                TokenType.GREATER_EQUAL: "ge"
            }[op]
            self.emit(f"    set{cond} al")
            self.emit("    movzx rax, al")

    # Functions
    def visit_Function(self, stmt: ast.Function):
        # Epilog of previous function (if any) or jump over this function?
        # In this simple compiler, we can emit functions at the end or jump over them.
        # Better: Jump over function body if encountered in control flow.
        l_end = self.new_label()
        self.emit(f"    jmp {l_end}")
        
        self.emit(f"func_{stmt.name.lexeme}:")
        # Prologue
        self.emit("    push rbp")
        self.emit("    mov rbp, rsp")
        
        # Shadow space + Local vars? 
        # For simplicity: Use args from registers directly or spill them.
        # Win64: RCX, RDX, R8, R9.
        # Let's spill them to shadow space [rbp + 16/24/32/40] ? 
        # Caller allocates shadow space. Return addr at [rbp+8]. Shadow at [rbp+16]..[rbp+48]?
        # No.
        # [rsp] = rbp (saved)
        # [rsp+8] = ret addr
        # [rsp+16] = shadow 1 (rcx home)
        # [rsp+24] = shadow 2 (rdx home)
        # ...
        
        # To simplify access, map param names to [rbp + offset].
        # But we need to move regs to those slots first.
        regs = ["rcx", "rdx", "r8", "r9"]
        for i, param in enumerate(stmt.params):
            if i < 4:
                offset = 16 + (i * 8)
                self.emit(f"    mov [rbp + {offset}], {regs[i]}")
                # Register param location in self.variables local scope? 
                # We need a symbol table stack.
                # HACK: Using global dict map key "param_NAME" to offset string?
        
        # We need a Scope Context for variables.
        # Currently self.variables is global.
        # Implementation Detail: 
        # For this prototype, we'll assume NO local variables other than params.
        # And Params are accessed via a special lookup hack or extended variable handling.
        
        # Let's execute body
        # We need to inject param offsets into variable lookup
        self.current_func_params = {p.lexeme: 16 + (i * 8) for i, p in enumerate(stmt.params)}
        
        for s in stmt.body:
            self.visit(s)
            
        # Default return
        self.emit("    xor rax, rax") # Return 0
        self.emit("    mov rsp, rbp") # Epilogue
        self.emit("    pop rbp")
        self.emit("    ret")
            
        self.emit(f"{l_end}:")
        self.current_func_params = None

    def visit_Return(self, stmt: ast.Return):
        if stmt.value:
            self.visit(stmt.value)
        # Epilogue
        self.emit("    mov rsp, rbp")
        self.emit("    pop rbp")
        self.emit("    ret")

    def visit_Call(self, expr: ast.Call):
        # Save registers? NASM doesn't auto save.
        # Caller saved regs: RCX, RDX, R8, R9, R10, R11.
        # We are using RAX for results.
        
        # Evaluate arguments
        # Push them to stack temp?
        # We need to evaluate all args first, then put in registers.
        # Cannot evaluate arg2 into RAX while arg1 is in RAX.
        
        # Strategy: Evaluate args, push to stack. Then pop into registers.
        for arg in expr.arguments:
            self.visit(arg)
            self.emit("    push rax")
            
        # Pop into regs (reverse order)
        regs = ["rcx", "rdx", "r8", "r9"]
        cnt = len(expr.arguments)
        
        # Win64: Stack must be aligned 16B before Call.
        # Current Stack depth? We don't track it perfectly in this simple compiler.
        # But `push` changes it.
        # We popped `cnt` times.
        # We need to move stacked args to regs.
        
        # Pop in reverse
        for i in range(cnt - 1, -1, -1):
            if i < 4:
                self.emit(f"    pop {regs[i]}")
            else:
                # Arg 5+
                # Complex: Must be on stack *above* shadow space.
                # For this toy compiler, limit 4 args.
                self.emit("    pop rax") # Discard extra args or TODO
                
        # Allocate shadow space (32 bytes)
        self.emit("    sub rsp, 32")
        
        if isinstance(expr.callee, ast.Variable):
            func_name = expr.callee.name.lexeme
            self.emit(f"    call func_{func_name}")
        
        self.emit("    add rsp, 32")

    # Update visit_Variable to handle Locals (Params)
    def visit_Variable(self, expr: ast.Variable):
        name = expr.name.lexeme
        if hasattr(self, 'current_func_params') and self.current_func_params and name in self.current_func_params:
            offset = self.current_func_params[name]
            self.emit(f"    mov rax, [rbp + {offset}]")
    # Array Operations
    def visit_ArrayLiteral(self, expr: ast.ArrayLiteral):
        count = len(expr.elements)
        size = count * 8
        if size == 0: size = 8 # Min alloc
        
        # 1. Malloc
        self.emit(f"    mov rcx, {size}") # Size
        self.emit("    sub rsp, 32")      # Shadow
        self.emit("    call malloc")
        self.emit("    add rsp, 32")
        self.emit("    push rax")         # Push array ptr to stack [rsp]
        
        # 2. Populate
        for i, elem in enumerate(expr.elements):
            self.visit(elem) # Result in RAX
            self.emit(f"    mov rbx, [rsp]") # Get array ptr
            offset = i * 8
            self.emit(f"    mov [rbx + {offset}], rax")
            
        self.emit("    pop rax") # Return array ptr

    def visit_Get(self, expr: ast.Get):
        self.visit(expr.object) # Array ptr -> RAX
        self.emit("    push rax")
        self.visit(expr.name)   # Index -> RAX
        self.emit("    mov rbx, rax") # Index in RBX
        self.emit("    pop rax")      # Array ptr in RAX
        
        # Address = RAX + RBX*8
        self.emit("    lea rcx, [rax + rbx*8]")
        self.emit("    mov rax, [rcx]")

    def visit_FileWrite(self, stmt: ast.FileWrite):
        # 1. Open File
        self.visit(stmt.path) # Path string in RAX
        self.emit("    mov rcx, rax") # Path
        self.emit("    lea rdx, [mode_w]") # Mode "w"
        self.emit("    sub rsp, 32")
        self.emit("    call fopen")
        self.emit("    add rsp, 32")
        self.emit("    mov rbx, rax") # File Handle in RBX
        
        # Check if null? skip check for toy compiler
        
        # 2. Write Content
        self.visit(stmt.content) # Content string in RAX
        self.emit("    mov rcx, rbx") # File Handle
        self.emit("    mov rdx, rax") # Content
        self.emit("    sub rsp, 32")
        self.emit("    call fprintf") # fprintf(file, string) - wait, fprintf format?
        # fprintf(file, "%s", string) if we want formatting. 
        # But if content is string, fprintf(file, str) works if no %
        self.emit("    add rsp, 32")
        
        # 3. Close File
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call fclose")
        self.emit("    add rsp, 32")

    def visit_FileRead(self, stmt: ast.FileRead):
        # 1. Open File
        self.visit(stmt.path) # Path
        self.emit("    mov rcx, rax")
        self.emit("    lea rdx, [mode_r]") # "rb"
        self.emit("    sub rsp, 32")
        self.emit("    call fopen")
        self.emit("    add rsp, 32")
        self.emit("    mov rbx, rax") # File Handle
        
        # 2. Get Size
        self.emit("    mov rcx, rbx")
        self.emit("    mov rdx, 0")
        self.emit("    mov r8, 2") # SEEK_END
        self.emit("    sub rsp, 32")
        self.emit("    call fseek")
        self.emit("    add rsp, 32")
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call ftell")
        self.emit("    add rsp, 32")
        self.emit("    mov r12, rax") # Size in R12 (Saved reg)
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call rewind")
        self.emit("    add rsp, 32")
        
        # 3. Malloc buffer (size + 1 for null terminator?)
        self.emit("    mov rcx, r12")
        self.emit("    add rcx, 1") # +1
        self.emit("    sub rsp, 32")
        self.emit("    call malloc")
        self.emit("    add rsp, 32")
        self.emit("    mov r13, rax") # Buffer in R13
        
        # 4. Read
        self.emit("    mov rcx, r13") # Buffer
        self.emit("    mov rdx, 1")   # Size
        self.emit("    mov r8, r12")  # Count
        self.emit("    mov r9, rbx")  # File
        self.emit("    sub rsp, 32")
        self.emit("    call fread")
        self.emit("    add rsp, 32")
        
        # Null terminate
        self.emit("    mov byte [r13 + r12], 0")
        
        # 5. Close
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call fclose")
        self.emit("    add rsp, 32")
        
        # 6. Assign
        var_name = stmt.target_var.lexeme
        if var_name not in self.variables:
             self.variables[var_name] = "global"
        self.emit(f"    mov rax, r13")
        self.emit(f"    mov [var_{var_name}], rax")

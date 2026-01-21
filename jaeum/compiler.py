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

        # Local variable management
        self.locals = {} # Name -> offset (from rbp)
        self.local_scope = False

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
        self.emit("extern strlen")
        self.emit("extern strcpy")
        self.emit("extern strcat")
        self.emit("extern sprintf")
        
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
        asm.append('    fmt_int_simple db "%lld", 0')
        asm.append('    fmt_str db "%s", 10, 0')
        asm.append('    mode_r db "rb", 0')
        asm.append('    mode_w db "w", 0')
        asm.append('    mode_a db "a", 0')
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
        self.visit(stmt.expression)
        
        if isinstance(stmt.expression, ast.Literal) and isinstance(stmt.expression.value, str):
            self.emit("    lea rcx, [fmt_str]")
            self.emit("    mov rdx, rax")
        else:
            self.emit("    lea rcx, [fmt_int]")
            self.emit("    mov rdx, rax")

        self.emit("    sub rsp, 32")
        self.emit("    call printf")
        self.emit("    add rsp, 32")

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
        name = expr.name.lexeme
        if self.local_scope and name in self.locals:
            offset = self.locals[name]
            self.emit(f"    mov rax, [rbp - {offset}]")
        elif self.local_scope and hasattr(self, 'current_func_params') and name in self.current_func_params:
             offset = self.current_func_params[name]
             self.emit(f"    mov rax, [rbp + {offset}]")
        else:
            self.emit(f"    mov rax, [var_{name}]")

    def visit_Assign(self, expr: ast.Assign):
        self.visit(expr.value) # Value in RAX
        name = expr.name.lexeme

        if self.local_scope:
            if name not in self.locals and name not in self.variables:
                # Implicit declaration (Local)
                # We need to allocate stack slot.
                # Currently we pre-calc stack size in visit_Function.
                # If we missed it there, we might overwrite stack?
                # But we can assume visit_Function collects it?
                # I need to update _collect_vars to look at Assigns too.
                # For now, if found in locals, use it.
                # If NOT found in locals but IS global, use global.
                # If NOT found in either, declare LOCAL.
                pass

            if name in self.locals:
                offset = self.locals[name]
                self.emit(f"    mov [rbp - {offset}], rax")
            elif name in self.variables:
                self.emit(f"    mov [var_{name}], rax")
            else:
                # New Local
                # NOTE: _collect_vars must find this for this to work safely with stack alloc.
                # If _collect_vars didn't find it, we didn't alloc space.
                # So we must update _collect_vars first.
                # Assuming _collect_vars found it, it should be in self.locals.
                # If it's not in self.locals here, it means _collect_vars failed or logic mismatch.
                # But let's assume we fixed _collect_vars.
                pass
        else:
            # Global scope
            if name not in self.variables:
                self.variables[name] = "global"
            self.emit(f"    mov [var_{name}], rax")

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
        l_end = self.new_label()
        self.emit(f"    jmp {l_end}")
        
        self.emit(f"func_{stmt.name.lexeme}:")
        self.emit("    push rbp")
        self.emit("    mov rbp, rsp")
        
        # 1. Setup Locals
        self.local_scope = True
        self.locals = {}

        # Scan for local variables
        local_vars = []
        self._collect_vars(stmt.body, local_vars)

        # Assign offsets (rbp - 8, -16...)
        current_offset = 8
        for var_name in local_vars:
            if var_name not in self.locals:
                if var_name not in self.variables:
                    self.locals[var_name] = current_offset
                    current_offset += 8

        # Allocate stack space
        stack_size = current_offset + 32 # +32 for shadow space calls?
        # Alignment: stack_size + 8 (rbp) + 8 (ret) = 16n
        # 16 + stack_size = 16n -> stack_size should be multiple of 16
        if stack_size % 16 != 0:
            stack_size += (16 - (stack_size % 16))

        self.emit(f"    sub rsp, {stack_size}")

        # Parameters
        self.current_func_params = {p.lexeme: 16 + (i * 8) for i, p in enumerate(stmt.params)}
        
        for s in stmt.body:
            self.visit(s)
            
        # Default return
        self.emit("    xor rax, rax")
        self.emit("    mov rsp, rbp")
        self.emit("    pop rbp")
        self.emit("    ret")
            
        self.emit(f"{l_end}:")
        self.local_scope = False
        self.locals = {}
        self.current_func_params = None

    def _collect_vars(self, block, acc):
        for stmt in block:
            if isinstance(stmt, ast.Expression):
                # Check for Assign expression
                if isinstance(stmt.expression, ast.Assign):
                    acc.append(stmt.expression.name.lexeme)
            elif isinstance(stmt, ast.Block):
                self._collect_vars(stmt.statements, acc)
            elif isinstance(stmt, ast.If):
                self._collect_vars(stmt.then_branch.statements, acc)
                if stmt.else_branch:
                     if isinstance(stmt.else_branch, ast.Block):
                         self._collect_vars(stmt.else_branch.statements, acc)
                     else:
                         self._collect_vars([stmt.else_branch], acc)
            elif isinstance(stmt, ast.While):
                self._collect_vars(stmt.body.statements, acc)

    def visit_Return(self, stmt: ast.Return):
        if stmt.value:
            self.visit(stmt.value)
        self.emit("    mov rsp, rbp")
        self.emit("    pop rbp")
        self.emit("    ret")

    def visit_Call(self, expr: ast.Call):
        if isinstance(expr.callee, ast.Variable):
            func_name = expr.callee.name.lexeme
            if func_name in ["준비", "길이", "코드", "문자", "문자연결", "문자읽기", "문자열변환"]:
                self.compile_intrinsic(func_name, expr.arguments)
                return

        for arg in expr.arguments:
            self.visit(arg)
            self.emit("    push rax")
            
        regs = ["rcx", "rdx", "r8", "r9"]
        cnt = len(expr.arguments)
        
        for i in range(cnt - 1, -1, -1):
            if i < 4:
                self.emit(f"    pop {regs[i]}")
            else:
                self.emit("    pop rax")
                
        self.emit("    sub rsp, 32")
        
        if isinstance(expr.callee, ast.Variable):
            func_name = expr.callee.name.lexeme
            self.emit(f"    call func_{func_name}")
        
        self.emit("    add rsp, 32")

    def compile_intrinsic(self, name, args):
        if name == "준비":
            self.visit(args[0])
            self.emit("    imul rax, 8")
            self.emit("    mov rcx, rax")
            self.emit("    sub rsp, 32")
            self.emit("    call malloc")
            self.emit("    add rsp, 32")
        elif name == "길이":
            self.visit(args[0])
            self.emit("    mov rcx, rax")
            self.emit("    sub rsp, 32")
            self.emit("    call strlen")
            self.emit("    add rsp, 32")
        elif name == "코드":
            self.visit(args[0])
            self.emit("    movzx rax, byte [rax]")
        elif name == "문자읽기":
            self.visit(args[0])
            self.emit("    push rax")
            self.visit(args[1])
            self.emit("    pop rbx")
            self.emit("    add rbx, rax")
            self.emit("    movzx rax, byte [rbx]")
        elif name == "문자":
            self.visit(args[0])
            self.emit("    push rax")
            self.emit("    mov rcx, 2")
            self.emit("    sub rsp, 32")
            self.emit("    call malloc")
            self.emit("    add rsp, 32")
            self.emit("    pop rbx")
            self.emit("    mov [rax], bl")
            self.emit("    mov byte [rax+1], 0")
        elif name == "문자연결":
            self.emit("    push r12")
            self.emit("    push r13")
            self.emit("    push r14")
            self.emit("    push r15")

            self.visit(args[0])
            self.emit("    push rax")
            self.visit(args[1])
            self.emit("    push rax")

            self.emit("    pop r13")
            self.emit("    pop r12")

            self.emit("    mov rcx, r12")
            self.emit("    sub rsp, 32")
            self.emit("    call strlen")
            self.emit("    add rsp, 32")
            self.emit("    mov r14, rax")

            self.emit("    mov rcx, r13")
            self.emit("    sub rsp, 32")
            self.emit("    call strlen")
            self.emit("    add rsp, 32")
            self.emit("    add r14, rax")
            self.emit("    inc r14")

            self.emit("    mov rcx, r14")
            self.emit("    sub rsp, 32")
            self.emit("    call malloc")
            self.emit("    add rsp, 32")
            self.emit("    mov r15, rax")

            self.emit("    mov rcx, r15")
            self.emit("    mov rdx, r12")
            self.emit("    sub rsp, 32")
            self.emit("    call strcpy")
            self.emit("    add rsp, 32")

            self.emit("    mov rcx, r15")
            self.emit("    mov rdx, r13")
            self.emit("    sub rsp, 32")
            self.emit("    call strcat")
            self.emit("    add rsp, 32")

            self.emit("    mov rax, r15")

            self.emit("    pop r15")
            self.emit("    pop r14")
            self.emit("    pop r13")
            self.emit("    pop r12")

        elif name == "문자열변환":
            self.emit("    push r12")

            self.visit(args[0])
            self.emit("    push rax")

            self.emit("    mov rcx, 32")
            self.emit("    sub rsp, 32")
            self.emit("    call malloc")
            self.emit("    add rsp, 32")
            self.emit("    mov r12, rax")

            self.emit("    pop r8")
            self.emit("    mov rcx, r12")
            self.emit("    lea rdx, [fmt_int_simple]")
            self.emit("    sub rsp, 32")
            self.emit("    call sprintf")
            self.emit("    add rsp, 32")

            self.emit("    mov rax, r12")

            self.emit("    pop r12")

    def visit_ArrayLiteral(self, expr: ast.ArrayLiteral):
        count = len(expr.elements)
        size = count * 8
        if size == 0: size = 8
        
        self.emit(f"    mov rcx, {size}")
        self.emit("    sub rsp, 32")
        self.emit("    call malloc")
        self.emit("    add rsp, 32")
        self.emit("    push rax")
        
        for i, elem in enumerate(expr.elements):
            self.visit(elem)
            self.emit(f"    mov rbx, [rsp]")
            offset = i * 8
            self.emit(f"    mov [rbx + {offset}], rax")
            
        self.emit("    pop rax")

    def visit_Get(self, expr: ast.Get):
        self.visit(expr.object)
        self.emit("    push rax")
        self.visit(expr.name)
        self.emit("    mov rbx, rax")
        self.emit("    pop rax")
        
        self.emit("    lea rcx, [rax + rbx*8]")
        self.emit("    mov rax, [rcx]")

    def visit_FileWrite(self, stmt: ast.FileWrite):
        self.visit(stmt.path)
        self.emit("    mov rcx, rax")
        self.emit("    lea rdx, [mode_w]")
        self.emit("    sub rsp, 32")
        self.emit("    call fopen")
        self.emit("    add rsp, 32")
        self.emit("    mov rbx, rax")

        self.visit(stmt.content)
        self.emit("    mov rcx, rbx")
        self.emit("    mov rdx, rax")
        self.emit("    sub rsp, 32")
        self.emit("    call fprintf")
        self.emit("    add rsp, 32")
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call fclose")
        self.emit("    add rsp, 32")

    def visit_FileAppend(self, stmt: ast.FileAppend):
        self.visit(stmt.path)
        self.emit("    mov rcx, rax")
        self.emit("    lea rdx, [mode_a]")
        self.emit("    sub rsp, 32")
        self.emit("    call fopen")
        self.emit("    add rsp, 32")
        self.emit("    mov rbx, rax")

        self.visit(stmt.content)
        self.emit("    mov rcx, rbx")
        self.emit("    mov rdx, rax")
        self.emit("    sub rsp, 32")
        self.emit("    call fprintf")
        self.emit("    add rsp, 32")
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call fclose")
        self.emit("    add rsp, 32")

    def visit_FileRead(self, stmt: ast.FileRead):
        self.visit(stmt.path)
        self.emit("    mov rcx, rax")
        self.emit("    lea rdx, [mode_r]")
        self.emit("    sub rsp, 32")
        self.emit("    call fopen")
        self.emit("    add rsp, 32")
        self.emit("    mov rbx, rax")
        
        self.emit("    mov rcx, rbx")
        self.emit("    mov rdx, 0")
        self.emit("    mov r8, 2")
        self.emit("    sub rsp, 32")
        self.emit("    call fseek")
        self.emit("    add rsp, 32")
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call ftell")
        self.emit("    add rsp, 32")
        self.emit("    mov r12, rax")
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call rewind")
        self.emit("    add rsp, 32")
        
        self.emit("    mov rcx, r12")
        self.emit("    add rcx, 1")
        self.emit("    sub rsp, 32")
        self.emit("    call malloc")
        self.emit("    add rsp, 32")
        self.emit("    mov r13, rax")
        
        self.emit("    mov rcx, r13")
        self.emit("    mov rdx, 1")
        self.emit("    mov r8, r12")
        self.emit("    mov r9, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call fread")
        self.emit("    add rsp, 32")
        
        self.emit("    mov byte [r13 + r12], 0")
        
        self.emit("    mov rcx, rbx")
        self.emit("    sub rsp, 32")
        self.emit("    call fclose")
        self.emit("    add rsp, 32")
        
        var_name = stmt.target_var.lexeme

        if self.local_scope and var_name in self.locals:
            offset = self.locals[var_name]
            self.emit(f"    mov [rbp - {offset}], r13")
        else:
            if var_name not in self.variables:
                self.variables[var_name] = "global"
            self.emit(f"    mov [var_{var_name}], r13")

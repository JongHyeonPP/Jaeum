from .tokens import Token, TokenType, KEYWORDS

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1

    def scan_tokens(self) -> list[Token]:
        while not self.is_at_end():
            self.start = self.current
            self.scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line))
        return self.tokens

    def scan_token(self):
        c = self.advance()
        
        # Whitespace
        if c in [' ', '\r', '\t']:
            return
        if c == '\n':
            self.line += 1
            return

        # Single-character tokens
        if c == '(': self.add_token(TokenType.LPAREN); return
        if c == ')': self.add_token(TokenType.RPAREN); return
        if c == '{': return self.add_token(TokenType.LBRACE)
        if c == '}': return self.add_token(TokenType.RBRACE)
        if c == '[': return self.add_token(TokenType.LBRACKET)
        if c == ']': return self.add_token(TokenType.RBRACKET)
        if c == ',': return self.add_token(TokenType.COMMA)
        if c == ';': self.add_token(TokenType.SEMICOLON); return
        if c == '+': self.add_token(TokenType.PLUS); return
        if c == '-': self.add_token(TokenType.MINUS); return
        if c == '*': self.add_token(TokenType.STAR); return
        if c == '/':
            if self.match('/'):
                # Comment
                while self.peek() != '\n' and not self.is_at_end():
                    self.advance()
            else:
                self.add_token(TokenType.SLASH)
            return
        if c == '%': self.add_token(TokenType.PERCENT); return

        # One or two character tokens
        if c == '!':
            self.add_token(TokenType.BANG_EQUAL if self.match('=') else TokenType.BANG)
            return
        if c == '=':
            self.add_token(TokenType.EQUAL_EQUAL if self.match('=') else TokenType.EQUAL)
            return
        if c == '<':
            self.add_token(TokenType.LESS_EQUAL if self.match('=') else TokenType.LESS)
            return
        if c == '>':
            self.add_token(TokenType.GREATER_EQUAL if self.match('=') else TokenType.GREATER)
            return
        if c == '&':
            if self.match('&'): self.add_token(TokenType.AND)
            else: self.error(f"Unexpected character: {c}") # Bitwise AND not supported yet
            return
        if c == '|':
            if self.match('|'): self.add_token(TokenType.OR)
            else: self.error(f"Unexpected character: {c}")
            return

        # Strings
        if c == '"':
            self.string()
            return

        # Numbers
        if self.is_digit(c):
            self.number()
            return

        # Identifiers & Keywords
        if self.is_alpha(c):
            self.identifier()
            return

        self.error(f"Unexpected character: {c}")

    def identifier(self):
        while self.is_alpha_numeric(self.peek()):
            self.advance()

        text = self.source[self.start:self.current]
        type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self.add_token(type)

    def number(self):
        while self.is_digit(self.peek()):
            self.advance()
        
        # Support floating point? Design implies integers mostly but "10 + 20" examples.
        # Let's support float if dot present?
        # Specification examples only used Ints, but general dynamic typing usually supports both.
        # Let's match integers strictly for now based on EBNF `NUMBER = DIGIT, { DIGIT }` 
        # (It didn't specify dots).
        
        self.add_token(TokenType.NUMBER, int(self.source[self.start:self.current]))

    def string(self):
        value = ""
        while not self.is_at_end() and self.peek() != '"':
            c = self.advance()
            if c == '\n':
                self.line += 1

            if c == '\\':
                if not self.is_at_end():
                    escaped = self.advance()
                    if escaped == 'n': value += '\n'
                    elif escaped == 'r': value += '\r'
                    elif escaped == 't': value += '\t'
                    elif escaped == '"': value += '"'
                    elif escaped == '\\': value += '\\'
                    else: value += escaped
            else:
                value += c
        
        if self.is_at_end():
            self.error("Unterminated string")
            return
        
        self.advance() # Closing "
        self.add_token(TokenType.STRING, value)

    def match(self, expected):
        if self.is_at_end(): return False
        if self.source[self.current] != expected: return False
        self.current += 1
        return True

    def peek(self):
        if self.is_at_end(): return '\0'
        return self.source[self.current]

    def advance(self):
        self.current += 1
        return self.source[self.current - 1]

    def add_token(self, type, literal=None):
        text = self.source[self.start:self.current]
        self.tokens.append(Token(type, text, literal, self.line))

    def is_at_end(self):
        return self.current >= len(self.source)

    def is_digit(self, c):
        return '0' <= c <= '9'

    def is_alpha(self, c):
        # Allow A-Z, a-z, Korean Consonants, Korean Syllables, Underscore
        # Simple ASCII check first
        if 'a' <= c <= 'z' or 'A' <= c <= 'Z' or c == '_':
            return True
        # Check Korean range
        # Consonants: U+3131 to U+314E (ㄱ to ㅎ)
        # Syllables: U+AC00 to U+D7A3 (가 to 힣)
        osc = ord(c) if len(c)==1 else 0
        if 0x3131 <= osc <= 0x314E: return True
        if 0xAC00 <= osc <= 0xD7A3: return True
        return False

    def is_alpha_numeric(self, c):
        return self.is_digit(c) or self.is_alpha(c)

    def error(self, message):
        # For now, just print or raise.
        # Design said "minimum runtime error handling".
        raise Exception(f"[Line {self.line}] Error: {message}")

import sys
import os
import shutil
import time
import subprocess

# --- TOKEN DEFINITIONS ---
TOKEN_KEYWORD = "KEYWORD"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_STRING = "STRING"
TOKEN_NUMBER = "NUMBER"
TOKEN_OPERATOR = "OPERATOR"

KEYWORDS = {
    "import", "module", "using", "adv",
    "func", "execute", "class", "public", "void", "main", "true", "false",
    "Loop", "do", "repeat", "stop", "break",
    "return", "delay", "if", "elseif", "else",
    "$", "{}", "cd", "pkg", "apt", "makedir", "broadcast", "ls", "ghost", "rm", "move"
}

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_char = self.text[self.pos] if text else None

    def advance(self):
        self.pos += 1
        self.current_char = self.text[self.pos] if self.pos < len(self.text) else None

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def get_string(self):
        result = ""
        self.advance()
        while self.current_char is not None and self.current_char != '"':
            result += self.current_char
            self.advance()
        self.advance()
        return (TOKEN_STRING, result)

    def get_number(self):
        result = ""
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '.'):
            result += self.current_char
            self.advance()
        return (TOKEN_NUMBER, result)

    def get_word(self):
        result = ""
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char in "_-"):
            result += self.current_char
            self.advance()
        if result in KEYWORDS:
            return (TOKEN_KEYWORD, result)
        return (TOKEN_IDENTIFIER, result)

    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            if self.current_char == '"':
                return self.get_string()
            if self.current_char.isdigit():
                return self.get_number()
            if self.current_char.isalpha() or self.current_char == '_':
                return self.get_word()
            if self.current_char in ["$", "{", "}", "=", "(", ")", "!", "<", ">"]:
                char = self.current_char
                self.advance()
                return (TOKEN_OPERATOR, char)
            self.advance()
        return (None, None)


class TermiScriptInterpreter:
    def __init__(self):
        self.variables = {}
        self.functions = {}
        self.silent_mode = False  # Tracks if ghost mode is active

    def run(self, code):
        lines = [line.strip() for line in code.splitlines() if line.strip() and not line.strip().startswith("#")]
        self.execute_block(lines)

    def execute_block(self, lines):
        i = 0
        while i < len(lines):
            line = lines[i]
            lexer = Lexer(line)
            tokens = []
            while True:
                tok_type, tok_val = lexer.get_next_token()
                if tok_type is None:
                    break
                tokens.append((tok_type, tok_val))
                
            if not tokens:
                i += 1
                continue

            head_type, head_val = tokens

            # 👻 GHOST MODE CHECK
            if head_type == TOKEN_KEYWORD and head_val == "ghost":
                self.silent_mode = True
                tokens = tokens[1:] # Strip "ghost" out and process the remaining line
                if not tokens:
                    i += 1
                    continue
                head_type, head_val = tokens

            if head_type == TOKEN_OPERATOR and head_val == "$":
                if len(tokens) >= 4 and tokens[1][0] == TOKEN_IDENTIFIER and tokens[2][0] == TOKEN_OPERATOR and tokens[2][1] == "=":
                    var_name = tokens[1][1]
                    var_val = tokens[3][1]
                    self.variables[var_name] = var_val
                i += 1

            elif head_type == TOKEN_KEYWORD and head_val == "func":
                func_name = tokens[1][1]
                func_lines = []
                i += 1
                while i < len(lines) and lines[i] != "}":
                    func_lines.append(lines[i])
                    i += 1
                self.functions[func_name] = func_lines
                i += 1

            elif head_type == TOKEN_KEYWORD and head_val == "Loop":
                count = int(tokens[1][1])
                loop_lines = []
                i += 1
                while i < len(lines) and lines[i] != "stop":
                    loop_lines.append(lines[i])
                    i += 1
                for _ in range(count):
                    self.execute_block(loop_lines)
                i += 1

            elif head_type == TOKEN_KEYWORD and head_val == "if":
                condition_var = tokens[1][1]
                condition_met = False
                if condition_var in self.variables and self.variables[condition_var] in ["true", True, 1, "1"]:
                    condition_met = True
                elif condition_var == "true":
                    condition_met = True

                if_lines = []
                i += 1
                while i < len(lines) and lines[i] != "}":
                    if_lines.append(lines[i])
                    i += 1
                if condition_met:
                    self.execute_block(if_lines)
                i += 1

            elif head_type == TOKEN_KEYWORD:
                self.execute_command(tokens)
                i += 1
            else:
                i += 1
            
            # Reset silent mode after the line finishes executing
            self.silent_mode = False

    def custom_print(self, text, end="\n"):
        """Prints text only if ghost mode is NOT active"""
        if not self.silent_mode:
            print(text, end=end)

    def execute_command(self, tokens):
        cmd = tokens[0][1]

        if cmd == "broadcast":
            msg = tokens[1][1]
            if msg in self.variables:
                self.custom_print(self.variables[msg])
            else:
                self.custom_print(msg)

        elif cmd == "execute":
            target_func = tokens[1][1]
            if target_func in self.functions:
                # Pass down the ghost state to the function block execution
                old_silent = self.silent_mode
                self.execute_block(self.functions[target_func])
                self.silent_mode = old_silent

        elif cmd == "delay":
            time.sleep(float(tokens[1][1]))

        elif cmd == "makedir":
            os.makedirs(tokens[1][1], exist_ok=True)
            self.custom_print(f"[Termi-Script] Created directory: {tokens[1][1]}")

        elif cmd == "ls":
            self.custom_print("\n".join(os.listdir(".")))

        elif cmd == "cd":
            os.chdir(tokens[1][1])

        elif cmd == "rm":
            target = tokens[1][1]
            if os.path.isdir(target): shutil.rmtree(target)
            elif os.path.isfile(target): os.remove(target)
            self.custom_print(f"[Termi-Script] Removed: {target}")

        elif cmd in ["pkg", "apt"]:
            package = tokens[2][1]
            
            # If GHOST mode is on, run package management silently
            if self.silent_mode:
                self.custom_print(f"[Ghost] Silently processing install for {package}...")
                # Simulating a completely silent installation step
                time.sleep(1.0)
                return

            # --- NORMAL TERMUX-STYLE OUTPUT ---
            package_db = {
                "python": {"depends": "libcompiler-re clang py3-pip", "inst_size": "865 MB", "dl_size": "215 MB"},
                "bash": {"depends": "shell libcompiler-re ncurses readline", "inst_size": "12.4 MB", "dl_size": "3.1 MB"}
            }
            info = package_db.get(package, {"depends": "libcompiler-re", "inst_size": "25 MB", "dl_size": "5 MB"})
            dep_list = info["depends"].split()
            all_packages = dep_list + [package]

            self.custom_print("Reading package lists... Done")
            time.sleep(0.2)
            self.custom_print(f"The following NEW packages will be installed:\n  {' '.join(all_packages)}")
            self.custom_print(f"After this operation, {info['inst_size']} of additional disk space will be used.")
            
            input("Do you want to continue? [Y/n] ")

            print("Setting up packages .... Done")
            total_steps = len(all_packages)
            for step, pkg_name in enumerate(all_packages, 1):
                self.custom_print(f"Setting up {pkg_name}...")
                pct = int((step / total_steps) * 100)
                hashes = "#" * int(pct / 10)
                dots = "." * (10 - len(hashes))
                self.custom_print(f"Progress: [{pct}%] [{hashes}{dots}]", end="\r")
                time.sleep(0.15)
            self.custom_print("\nProgress: [100%] [##########]\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv, "r") as f:
            script_code = f.read()
        interpreter = TermiScriptInterpreter()
        interpreter.run(script_code)
    else:
        print("Usage: termiscript <script.ts>")

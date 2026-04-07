from __future__ import annotations

from typing import Any


def _code(*lines: str) -> str:
    return "\n".join(lines)


TASKS: list[dict[str, Any]] = [
    {
        "id": "easy_off_by_one",
        "difficulty": "easy",
        "prompt": _code(
            "def last_item(values):",
            "    if not values:",
            "        return None",
            "    return values[len(values)]",
        ),
        "true_bug_line": 4,
        "true_bug_type": "off-by-one error",
        "safety_bug_type": "runtime",
        "keywords": ["index", "range", "off-by-one"],
        "fixed_code": _code(
            "def last_item(values):",
            "    if not values:",
            "        return None",
            "    return values[len(values) - 1]",
        ),
        "test_cases": [
            {"input": [[1, 2, 3]], "expected": 3},
            {"input": [[]], "expected": None},
        ],
    },
    {
        "id": "easy_wrong_operator",
        "difficulty": "easy",
        "prompt": _code(
            "def is_adult(age):",
            "    return age < 18",
        ),
        "true_bug_line": 2,
        "true_bug_type": "wrong operator",
        "keywords": ["comparison", "operator", "age"],
        "fixed_code": _code(
            "def is_adult(age):",
            "    return age >= 18",
        ),
        "test_cases": [
            {"input": [20], "expected": True},
            {"input": [16], "expected": False},
        ],
    },
    {
        "id": "easy_missing_return",
        "difficulty": "easy",
        "prompt": _code(
            "def square(n):",
            "    result = n * n",
        ),
        "true_bug_line": 2,
        "true_bug_type": "missing return",
        "keywords": ["return", "result", "output"],
        "fixed_code": _code(
            "def square(n):",
            "    result = n * n",
            "    return result",
        ),
        "test_cases": [
            {"input": [4], "expected": 16},
            {"input": [-3], "expected": 9},
        ],
    },
    {
        "id": "easy_wrong_variable_name",
        "difficulty": "easy",
        "prompt": _code(
            "def count_odds(numbers):",
            "    total = 0",
            "    for number in numbers:",
            "        if number % 2 == 1:",
            "            total += 1",
            "    return count",
        ),
        "true_bug_line": 6,
        "true_bug_type": "wrong variable name",
        "safety_bug_type": "runtime",
        "keywords": ["variable", "name", "undefined"],
        "fixed_code": _code(
            "def count_odds(numbers):",
            "    total = 0",
            "    for number in numbers:",
            "        if number % 2 == 1:",
            "            total += 1",
            "    return total",
        ),
        "test_cases": [
            {"input": [[1, 2, 3, 4, 5]], "expected": 3},
            {"input": [[2, 4]], "expected": 0},
        ],
    },
    {
        "id": "easy_missing_zero_guard",
        "difficulty": "easy",
        "prompt": _code(
            "def safe_ratio(total, count):",
            "    return total / count",
        ),
        "true_bug_line": 2,
        "true_bug_type": "missing zero guard",
        "safety_bug_type": "runtime",
        "keywords": ["zero", "guard", "division"],
        "fixed_code": _code(
            "def safe_ratio(total, count):",
            "    if count == 0:",
            "        return 0",
            "    return total / count",
        ),
        "test_cases": [
            {"input": [10, 2], "expected": 5.0},
            {"input": [10, 0], "expected": 0},
        ],
    },
    {
        "id": "medium_stack",
        "difficulty": "medium",
        "prompt": _code(
            "class Stack:",
            "    def __init__(self):",
            "        self.items = []",
            "",
            "    def push(self, item):",
            "        self.items.append(item)",
            "",
            "    def pop(self):",
            "        if not self.items:",
            "            return None",
            "        return self.items.pop(0)",
            "",
            "    def peek(self):",
            "        if not self.items:",
            "            return None",
            "        return self.items[0]",
        ),
        "true_bugs": [
            {
                "line": 11,
                "bug_type": "wrong index",
                "keywords": ["stack", "lifo", "pop"],
            },
            {
                "line": 16,
                "bug_type": "wrong index",
                "keywords": ["peek", "top", "last"],
            },
        ],
        "true_bug_type": ["wrong index", "wrong index"],
        "keywords": ["stack", "lifo", "top", "pop"],
        "fixed_code": _code(
            "class Stack:",
            "    def __init__(self):",
            "        self.items = []",
            "",
            "    def push(self, item):",
            "        self.items.append(item)",
            "",
            "    def pop(self):",
            "        if not self.items:",
            "            return None",
            "        return self.items.pop()",
            "",
            "    def peek(self):",
            "        if not self.items:",
            "            return None",
            "        return self.items[-1]",
        ),
        "test_cases": [
            {"steps": [["push", 1], ["push", 2], ["pop"]], "expected": 2},
            {"steps": [["push", 4], ["peek"]], "expected": 4},
        ],
    },
    {
        "id": "medium_bank_account",
        "difficulty": "medium",
        "prompt": _code(
            "class BankAccount:",
            "    def __init__(self, balance=0):",
            "        self.balance = balance",
            "",
            "    def deposit(self, amount):",
            "        if amount < 0:",
            "            return self.balance",
            "        self.balance += value",
            "        return self.balance",
            "",
            "    def withdraw(self, amount):",
            "        if amount > self.balance:",
            "            return self.balance",
            "        self.balance += amount",
            "        return self.balance",
        ),
        "true_bugs": [
            {
                "line": 8,
                "bug_type": "wrong variable name",
                "keywords": ["deposit", "value", "amount"],
            },
            {
                "line": 14,
                "bug_type": "wrong operator",
                "keywords": ["withdraw", "subtract", "balance"],
            },
        ],
        "true_bug_type": ["wrong variable name", "wrong operator"],
        "keywords": ["balance", "deposit", "withdraw"],
        "fixed_code": _code(
            "class BankAccount:",
            "    def __init__(self, balance=0):",
            "        self.balance = balance",
            "",
            "    def deposit(self, amount):",
            "        if amount < 0:",
            "            return self.balance",
            "        self.balance += amount",
            "        return self.balance",
            "",
            "    def withdraw(self, amount):",
            "        if amount > self.balance:",
            "            return self.balance",
            "        self.balance -= amount",
            "        return self.balance",
        ),
        "test_cases": [
            {"steps": [["deposit", 5]], "start": 10, "expected": 15},
            {"steps": [["withdraw", 7]], "start": 10, "expected": 3},
        ],
    },
    {
        "id": "medium_linked_list",
        "difficulty": "medium",
        "prompt": _code(
            "class LinkedList:",
            "    def __init__(self):",
            "        self.head = None",
            "",
            "    def append(self, value):",
            "        node = {\"value\": value, \"next\": None}",
            "        if self.head is None:",
            "            return node",
            "        current = self.head",
            "        while current[\"next\"] is not None:",
            "            current = current[\"next\"]",
            "        current[\"next\"] = node",
            "",
            "    def find(self, value):",
            "        current = self.head",
            "        while current is not None:",
            "            if current[\"value\"] == value:",
            "                return False",
            "            current = current[\"next\"]",
            "        return None",
        ),
        "true_bugs": [
            {
                "line": 8,
                "bug_type": "missing assignment",
                "keywords": ["head", "append", "node"],
            },
            {
                "line": 18,
                "bug_type": "wrong return value",
                "keywords": ["find", "return", "match"],
            },
        ],
        "true_bug_type": ["missing assignment", "wrong return value"],
        "keywords": ["linked list", "head", "find", "append"],
        "fixed_code": _code(
            "class LinkedList:",
            "    def __init__(self):",
            "        self.head = None",
            "",
            "    def append(self, value):",
            "        node = {\"value\": value, \"next\": None}",
            "        if self.head is None:",
            "            self.head = node",
            "            return",
            "        current = self.head",
            "        while current[\"next\"] is not None:",
            "            current = current[\"next\"]",
            "        current[\"next\"] = node",
            "",
            "    def find(self, value):",
            "        current = self.head",
            "        while current is not None:",
            "            if current[\"value\"] == value:",
            "                return current",
            "            current = current[\"next\"]",
            "        return None",
        ),
        "test_cases": [
            {"values": [3, 5], "find": 5, "expected": {"value": 5, "next": None}},
            {"values": [3], "find": 7, "expected": None},
        ],
    },
    {
        "id": "medium_file_processor",
        "difficulty": "medium",
        "prompt": _code(
            "class FileProcessor:",
            "    def count_lines(self, text):",
            "        if not text:",
            "            return 1",
            "        return len(text.splitlines())",
            "",
            "    def file_extension(self, filename):",
            "        parts = filename.split(\".\")",
            "        if len(parts) == 1:",
            "            return \"\"",
            "        return parts[0]",
        ),
        "true_bugs": [
            {
                "line": 4,
                "bug_type": "wrong return value",
                "keywords": ["empty", "count", "lines"],
            },
            {
                "line": 11,
                "bug_type": "wrong index",
                "keywords": ["extension", "last", "filename"],
            },
        ],
        "true_bug_type": ["wrong return value", "wrong index"],
        "keywords": ["file", "lines", "extension", "filename"],
        "fixed_code": _code(
            "class FileProcessor:",
            "    def count_lines(self, text):",
            "        if not text:",
            "            return 0",
            "        return len(text.splitlines())",
            "",
            "    def file_extension(self, filename):",
            "        parts = filename.split(\".\")",
            "        if len(parts) == 1:",
            "            return \"\"",
            "        return parts[-1]",
        ),
        "test_cases": [
            {"method": "count_lines", "input": "", "expected": 0},
            {"method": "file_extension", "input": "report.txt", "expected": "txt"},
        ],
    },
    {
        "id": "hard_calculator_validator",
        "difficulty": "hard",
        "prompt": {
            "validator.py": _code(
                "def is_number(value):",
                "    return isinstance(value, (int, float))",
                "",
                "def ensure_divisor(value):",
                "    return value == 0",
            ),
            "calculator.py": _code(
                "from validator import ensure_divisor, is_number",
                "",
                "def divide(a, b):",
                "    if not ensure_divisor:",
                "        raise ValueError(\"divisor cannot be zero\")",
                "    if not is_number(a) or not is_number(b):",
                "        raise TypeError(\"numbers required\")",
                "    return a // b",
            ),
        },
        "true_bugs": [
            {
                "file": "validator.py",
                "line": 5,
                "bug_type": "wrong operator",
                "keywords": ["divisor", "zero", "validator"],
                "cross_module": False,
            },
            {
                "file": "calculator.py",
                "line": 4,
                "bug_type": "integration bug",
                "keywords": ["module", "call", "validator"],
                "cross_module": True,
            },
            {
                "file": "calculator.py",
                "line": 8,
                "bug_type": "wrong operator",
                "keywords": ["division", "integer", "calculator"],
                "cross_module": False,
            },
        ],
        "true_bug_type": ["wrong operator", "integration bug", "wrong operator"],
        "keywords": ["calculator", "validator", "module", "division", "zero"],
        "fixed_code": {
            "validator.py": _code(
                "def is_number(value):",
                "    return isinstance(value, (int, float))",
                "",
                "def ensure_divisor(value):",
                "    return value != 0",
            ),
            "calculator.py": _code(
                "from validator import ensure_divisor, is_number",
                "",
                "def divide(a, b):",
                "    if not ensure_divisor(b):",
                "        raise ValueError(\"divisor cannot be zero\")",
                "    if not is_number(a) or not is_number(b):",
                "        raise TypeError(\"numbers required\")",
                "    return a / b",
            ),
        },
        "test_cases": [
            {"call": "divide(8, 2)", "expected": 4.0},
            {"call": "divide(8, 0)", "expected": "ValueError"},
        ],
    },
    {
        "id": "hard_parser_formatter",
        "difficulty": "hard",
        "prompt": {
            "parser.py": _code(
                "def parse_record(text):",
                "    parts = text.split(\",\")",
                "    return {\"name\": parts[0], \"score\": int(parts[2])}",
            ),
            "formatter.py": _code(
                "from parser import parse_records",
                "",
                "def format_record(text):",
                "    record = parse_records(text)",
                "    return f\"{record['name']} ({record['scores']})\"",
            ),
        },
        "true_bugs": [
            {
                "file": "parser.py",
                "line": 3,
                "bug_type": "wrong index",
                "keywords": ["score", "index", "parser"],
                "cross_module": False,
            },
            {
                "file": "formatter.py",
                "line": 1,
                "bug_type": "integration bug",
                "keywords": ["import", "module", "formatter"],
                "cross_module": True,
            },
            {
                "file": "formatter.py",
                "line": 5,
                "bug_type": "wrong key",
                "keywords": ["record", "score", "formatter"],
                "cross_module": False,
            },
        ],
        "true_bug_type": ["wrong index", "integration bug", "wrong key"],
        "keywords": ["parser", "formatter", "module", "record", "score"],
        "fixed_code": {
            "parser.py": _code(
                "def parse_record(text):",
                "    parts = text.split(\",\")",
                "    return {\"name\": parts[0], \"score\": int(parts[1])}",
            ),
            "formatter.py": _code(
                "from parser import parse_record",
                "",
                "def format_record(text):",
                "    record = parse_record(text)",
                "    return f\"{record['name']} ({record['score']})\"",
            ),
        },
        "test_cases": [
            {"call": "format_record('Ada,99')", "expected": "Ada (99)"},
        ],
    },
    {
        "id": "hard_auth_session",
        "difficulty": "hard",
        "prompt": {
            "auth.py": _code(
                "def authenticate(username, password):",
                "    users = {\"admin\": \"secret\", \"guest\": \"guest\"}",
                "    return users.get(username) is password",
                "",
                "def user_role(username):",
                "    return \"admin\" if username == \"admin\" else \"viewer\"",
            ),
            "session.py": _code(
                "from auth import authenticate, user_role",
                "",
                "def create_session(username, password):",
                "    if authenticate(username, password):",
                "        return None",
                "    return {\"user\": username, \"role\": role_for(username), \"active\": True}",
            ),
        },
        "true_bugs": [
            {
                "file": "auth.py",
                "line": 3,
                "bug_type": "wrong operator",
                "keywords": ["authenticate", "comparison", "auth"],
                "cross_module": False,
            },
            {
                "file": "session.py",
                "line": 4,
                "bug_type": "wrong condition",
                "keywords": ["session", "condition", "authenticate"],
                "cross_module": False,
            },
            {
                "file": "session.py",
                "line": 6,
                "bug_type": "integration bug",
                "keywords": ["role", "module", "session"],
                "cross_module": True,
            },
        ],
        "true_bug_type": ["wrong operator", "wrong condition", "integration bug"],
        "keywords": ["auth", "session", "module", "role", "authenticate"],
        "fixed_code": {
            "auth.py": _code(
                "def authenticate(username, password):",
                "    users = {\"admin\": \"secret\", \"guest\": \"guest\"}",
                "    return users.get(username) == password",
                "",
                "def user_role(username):",
                "    return \"admin\" if username == \"admin\" else \"viewer\"",
            ),
            "session.py": _code(
                "from auth import authenticate, user_role",
                "",
                "def create_session(username, password):",
                "    if not authenticate(username, password):",
                "        return None",
                "    return {\"user\": username, \"role\": user_role(username), \"active\": True}",
            ),
        },
        "test_cases": [
            {
                "call": "create_session('admin', 'secret')",
                "expected": {"user": "admin", "role": "admin", "active": True},
            },
        ],
    },
]


def get_tasks_by_difficulty(difficulty: str) -> list[dict[str, Any]]:
    normalized = difficulty.lower()
    return [task for task in TASKS if task["difficulty"] == normalized]


def render_prompt(prompt: str | dict[str, str]) -> str:
    if isinstance(prompt, str):
        return prompt

    sections = []
    for filename, code in prompt.items():
        sections.append(f"# {filename}\n{code}")
    return "\n\n".join(sections)


def find_task_by_rendered_prompt(prompt: str) -> dict[str, Any]:
    for task in TASKS:
        if render_prompt(task["prompt"]) == prompt:
            return task
    raise ValueError("Unknown prompt.")

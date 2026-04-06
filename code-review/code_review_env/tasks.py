from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

@dataclass
class TaskConfig:
    name: str
    difficulty: str
    content: Any  # code string or dict of files
    ground_truth: Any
    test_cases: List[Any]
    keywords: List[str] = field(default_factory=list)

TASKS = {
    "easy": [
        TaskConfig(
            name="Easy 1: Off-by-one",
            difficulty="easy",
            content="""def find_max(nums):
    max_val = nums[0]
    for i in range(1, len(nums) + 1):
        if nums[i] > max_val:
            max_val = nums[i]
    return max_val""",
            ground_truth={"bug_line": 3, "bug_type": "runtime"},
            test_cases=[([1, 5, 2], 5), ([10], 10)],
            keywords=["index", "range", "off-by-one"]
        ),
        TaskConfig(
            name="Easy 2: Wrong Operator",
            difficulty="easy",
            content="""def is_even(n):
    return n % 2 == 1""",
            ground_truth={"bug_line": 2, "bug_type": "logic"},
            test_cases=[(4, True), (3, False)],
            keywords=["modulo", "operator", "even"]
        ),
        TaskConfig(
            name="Easy 3: Missing Return",
            difficulty="easy",
            content="""def celsius_to_fahrenheit(c):
    result = (c * 9/5) + 32""",
            ground_truth={"bug_line": 3, "bug_type": "logic"},
            test_cases=[(0, 32.0), (100, 212.0)],
            keywords=["return", "missing"]
        ),
        TaskConfig(
            name="Easy 4: Wrong Variable Name",
            difficulty="easy",
            content="""def count_vowels(s):
    count = 0
    for char in s:
        if char.lower() in 'aeiou':
            count += 1
    return cnt""",
            ground_truth={"bug_line": 6, "bug_type": "runtime"},
            test_cases=[("hello", 2), ("aeiou", 5)],
            keywords=["NameError", "variable", "undefined"]
        ),
        TaskConfig(
            name="Easy 5: Zero Division",
            difficulty="easy",
            content="""def safe_divide(a, b):
    return a / b""",
            ground_truth={"bug_line": 2, "bug_type": "runtime"},
            test_cases=[(10, 2, 5.0), (5, 0, "ZeroDivisionError")],
            keywords=["ZeroDivisionError", "zero", "guard"]
        )
    ],
    "medium": [
        TaskConfig(
            name="Medium 1: Stack implementation",
            difficulty="medium",
            content="""class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if self.is_empty():
            return None
        return self.items.pop(0)

    def peek(self):
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self.items

    def is_empty(self):
        return len(self.items) == 0""",
            ground_truth=[
                {"line": 11, "type": "logic", "keywords": ["pop", "index", "LIFO"]},
                {"line": 16, "type": "logic", "keywords": ["top", "last"]}
            ],
            test_cases=[],
            keywords=["stack", "LIFO"]
        ),
        TaskConfig(
            name="Medium 2: Bank Account",
            difficulty="medium",
            content="""class BankAccount:
    def __init__(self, balance):
        self.balance = balance

    def deposit(self, amount):
        if amount > 0:
            self.balance += balance
        return self.balance

    def withdraw(self, amount):
        if 0 < amount < self.balance:
            self.balance -= amount
        return self.balance""",
            ground_truth=[
                {"line": 7, "type": "runtime", "keywords": ["undefined", "balance", "self"]},
                {"line": 11, "type": "logic", "keywords": ["withdraw", "equal", "balance"]}
            ],
            test_cases=[],
            keywords=["bank", "logic"]
        ),
        TaskConfig(
            name="Medium 3: List Filter",
            difficulty="medium",
            content="""def get_positive_numbers(numbers):
    positives = []
    for n in numbers:
        if n > 0:
            positives.append(number)
    return positive""",
            ground_truth=[
                {"line": 5, "type": "runtime", "keywords": ["undefined", "number", "n"]},
                {"line": 6, "type": "runtime", "keywords": ["undefined", "positive", "positives"]}
            ],
            test_cases=[],
            keywords=["list", "iteration"]
        ),
        TaskConfig(
            name="Medium 4: Dict Merge",
            difficulty="medium",
            content="""def merge_dicts(d1, d2):
    result = d1.copy()
    for key, value in d2:
        result[key] = value
    return res""",
            ground_truth=[
                {"line": 3, "type": "runtime", "keywords": ["iteration", "items", "dict"]},
                {"line": 5, "type": "runtime", "keywords": ["undefined", "res", "result"]}
            ],
            test_cases=[],
            keywords=["dict", "merge"]
        )
    ],
    "hard": [
        TaskConfig(
            name="Hard 1: Multi-module Logging",
            difficulty="hard",
            content={
                "logger.py": "def log(msg):\n    print(f'[LOG] {msg}')",
                "app.py": "import logger\ndef run():\n    logger.log_message('Hello')"
            },
            ground_truth=[
                {"file": "app.py", "line": 3, "type": "runtime", "description": "logger.log_message does not exist", "fix": "logger.log('Hello')"},
                {"file": "logger.py", "line": 2, "type": "style", "description": "Use logging module instead of print", "fix": "import logging\nlogging.info(msg)"}
            ],
            test_cases=[],
            keywords=["integration", "module", "style"]
        },
        TaskConfig(
            name="Hard 2: API Client",
            difficulty="hard",
            content={
                "client.py": "class API:\n    def get(self, url):\n        import requests\n        return requests.get(url)",
                "service.py": "from client import API\ndef fetch_data():\n    api = API()\n    resp = api.get('https://api.test.com')\n    return resp.json"
            },
            ground_truth=[
                {"file": "service.py", "line": 5, "type": "runtime", "description": "json is a method not property", "fix": "return resp.json()"},
                {"file": "client.py", "line": 4, "type": "runtime", "description": "requests might fail", "fix": "try:\n    return requests.get(url)\nexcept requests.RequestException:\n    return None"}
            ],
            test_cases=[],
            keywords=["api", "json", "exception"]
        },
        TaskConfig(
            name="Hard 3: Decorator Bug",
            difficulty="hard",
            content={
                "decorators.py": "def debug(func):\n    def wrapper(*args, **kwargs):\n        print(f'Calling {func.__name__}')\n        return func\n    return wrapper",
                "main.py": "from decorators import debug\n@debug\ndef add(a, b):\n    return a + b"
            },
            ground_truth=[
                {"file": "decorators.py", "line": 4, "type": "logic", "description": "Returns func instead of calling it", "fix": "return func(*args, **kwargs)"},
                {"file": "main.py", "line": 4, "type": "logic", "description": "Function add will return itself", "fix": ""}
            ],
            test_cases=[],
            keywords=["decorator", "wrapper", "call"]
        }
    ]
}

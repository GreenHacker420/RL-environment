from __future__ import annotations

import hashlib
import random
from typing import Any


def _code(*lines: str) -> str:
    return "\n".join(lines)


TASKS: list[dict[str, str]] = [
    {"id": "easy_implementation_discount", "difficulty": "easy", "family": "implementation"},
    {"id": "easy_repair_slugify", "difficulty": "easy", "family": "repair"},
    {"id": "medium_implementation_inventory", "difficulty": "medium", "family": "implementation"},
    {"id": "medium_repair_budget", "difficulty": "medium", "family": "repair"},
    {"id": "hard_integration_orders", "difficulty": "hard", "family": "integration"},
    {"id": "hard_repair_auth", "difficulty": "hard", "family": "repair"},
]


MAX_TEST_RUNS = {"easy": 3, "medium": 4, "hard": 4}
MAX_STEPS = {"easy": 8, "medium": 12, "hard": 14}


def _variant_rng(task_id: str, seed: int | None) -> random.Random:
    raw = f"{task_id}:{0 if seed is None else seed}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _descriptor_map() -> dict[str, dict[str, str]]:
    return {task["id"]: task for task in TASKS}


def get_tasks_by_difficulty(difficulty: str) -> list[dict[str, str]]:
    normalized = difficulty.lower()
    return [task for task in TASKS if task["difficulty"] == normalized]


def get_task_by_id(task_id: str) -> dict[str, str]:
    try:
        return _descriptor_map()[task_id]
    except KeyError as exc:
        raise ValueError(f"Unknown task_id: {task_id}") from exc


def build_workspace_summary(files: dict[str, str]) -> list[str]:
    return [f"{path} ({len(content.splitlines())} lines)" for path, content in files.items()]


def render_workspace(files: dict[str, str]) -> str:
    sections = []
    for path, content in files.items():
        sections.append(f"# {path}\n{content}")
    return "\n\n".join(sections)


def _function_case(name: str, module: str, func: str, args: list[Any], expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "kind": "function",
        "module": module,
        "callable": func,
        "args": args,
        "expected": expected,
    }


def _class_case(
    name: str,
    module: str,
    class_name: str,
    steps: list[dict[str, Any]],
    expected: Any,
    constructor_args: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "kind": "class",
        "module": module,
        "class_name": class_name,
        "constructor_args": constructor_args or [],
        "steps": steps,
        "expected": expected,
    }


def _build_easy_implementation_discount(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("easy_implementation_discount", seed)
    file_name = rng.choice(["pricing.py", "offers.py", "totals.py"])
    module = file_name[:-3]
    func_name = rng.choice(["apply_discount", "discount_total", "compute_total"])
    rate = rng.choice([0.10, 0.15, 0.20])
    percent = int(rate * 100)

    workspace_files = {
        file_name: _code(
            f"def {func_name}(subtotal, has_coupon):",
            '    """Return the final total after applying an optional coupon."""',
            "    raise NotImplementedError('implement the pricing rule')",
        )
    }

    return {
        "id": "easy_implementation_discount",
        "difficulty": "easy",
        "family": "implementation",
        "title": "Implement coupon pricing helper",
        "task_brief": (
            f"Implement `{func_name}(subtotal, has_coupon)` in `{file_name}`. "
            f"If `has_coupon` is true, apply a {percent}% discount to `subtotal`. "
            "Always round the returned total to 2 decimal places."
        ),
        "workspace_files": workspace_files,
        "editable_files": [file_name],
        "public_tests": [
            _function_case("coupon_applied", module, func_name, [120.0, True], round(120.0 * (1 - rate), 2)),
            _function_case("coupon_skipped", module, func_name, [49.99, False], 49.99),
        ],
        "hidden_tests": [
            _function_case("small_discount", module, func_name, [19.95, True], round(19.95 * (1 - rate), 2)),
            _function_case("zero_total", module, func_name, [0.0, True], 0.0),
        ],
    }


def _build_easy_repair_slugify(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("easy_repair_slugify", seed)
    file_name = rng.choice(["labels.py", "strings.py", "slugify.py"])
    module = file_name[:-3]
    func_name = rng.choice(["normalize_label", "slugify_label", "clean_slug"])

    workspace_files = {
        file_name: _code(
            f"def {func_name}(text):",
            '    """Trim text, lowercase it, and join words with single dashes."""',
            "    return text.lower().replace(' ', '-')",
        )
    }

    return {
        "id": "easy_repair_slugify",
        "difficulty": "easy",
        "family": "repair",
        "title": "Repair slug normalization helper",
        "task_brief": (
            f"Repair `{func_name}(text)` in `{file_name}`. "
            "It should trim outer whitespace, lowercase the text, and collapse all internal whitespace runs into single dashes."
        ),
        "workspace_files": workspace_files,
        "editable_files": [file_name],
        "public_tests": [
            _function_case("trim_and_lower", module, func_name, ["  Hello World  "], "hello-world"),
            _function_case("preserve_existing_dash", module, func_name, ["Already-Clean"], "already-clean"),
        ],
        "hidden_tests": [
            _function_case("collapse_whitespace", module, func_name, ["Many   spaced\twords"], "many-spaced-words"),
            _function_case("single_word", module, func_name, [" Python "], "python"),
        ],
    }


def _build_medium_implementation_inventory(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("medium_implementation_inventory", seed)
    file_name = rng.choice(["inventory.py", "stock.py"])
    module = file_name[:-3]
    class_name = rng.choice(["InventoryTracker", "StockLedger"])

    workspace_files = {
        file_name: _code(
            f"class {class_name}:",
            "    def __init__(self):",
            "        self._items = {}",
            "",
            "    def add_item(self, name, quantity):",
            "        raise NotImplementedError('implement add_item')",
            "",
            "    def remove_item(self, name, quantity):",
            "        raise NotImplementedError('implement remove_item')",
            "",
            "    def available(self, name):",
            "        raise NotImplementedError('implement available')",
        )
    }

    return {
        "id": "medium_implementation_inventory",
        "difficulty": "medium",
        "family": "implementation",
        "title": "Implement inventory tracker class",
        "task_brief": (
            f"Implement `{class_name}` in `{file_name}`. "
            "`add_item(name, quantity)` increases stock for positive quantities. "
            "`remove_item(name, quantity)` decreases stock but must never go below zero. "
            "`available(name)` returns current stock or zero for unknown items."
        ),
        "workspace_files": workspace_files,
        "editable_files": [file_name],
        "public_tests": [
            _class_case(
                "add_and_read",
                module,
                class_name,
                [
                    {"method": "add_item", "args": ["tea", 3]},
                    {"method": "available", "args": ["tea"]},
                ],
                3,
            ),
            _class_case(
                "remove_not_below_zero",
                module,
                class_name,
                [
                    {"method": "add_item", "args": ["pens", 2]},
                    {"method": "remove_item", "args": ["pens", 5]},
                    {"method": "available", "args": ["pens"]},
                ],
                0,
            ),
            _class_case(
                "missing_item",
                module,
                class_name,
                [{"method": "available", "args": ["missing"]}],
                0,
            ),
        ],
        "hidden_tests": [
            _class_case(
                "ignore_non_positive_add",
                module,
                class_name,
                [
                    {"method": "add_item", "args": ["paper", 0]},
                    {"method": "available", "args": ["paper"]},
                ],
                0,
            ),
            _class_case(
                "multiple_updates",
                module,
                class_name,
                [
                    {"method": "add_item", "args": ["cups", 4]},
                    {"method": "remove_item", "args": ["cups", 1]},
                    {"method": "available", "args": ["cups"]},
                ],
                3,
            ),
        ],
    }


def _build_medium_repair_budget(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("medium_repair_budget", seed)
    file_name = rng.choice(["budget.py", "tracker.py"])
    module = file_name[:-3]
    class_name = rng.choice(["BudgetTracker", "SpendTracker"])

    workspace_files = {
        file_name: _code(
            f"class {class_name}:",
            "    def __init__(self, limit):",
            "        self.limit = limit",
            "        self.spent = 0",
            "",
            "    def add_expense(self, amount):",
            "        if amount < 0:",
            "            return self.spent",
            "        self.spent -= amount",
            "        return self.spent",
            "",
            "    def remaining(self):",
            "        if self.spent > self.limit:",
            "            return 0",
            "        return self.limit + self.spent",
            "",
            "    def is_over_budget(self):",
            "        return self.spent < self.limit",
        )
    }

    return {
        "id": "medium_repair_budget",
        "difficulty": "medium",
        "family": "repair",
        "title": "Repair budget tracking regressions",
        "task_brief": (
            f"Repair `{class_name}` in `{file_name}`. "
            "Expenses should increase `spent`, remaining budget should subtract spent from limit, and over-budget detection should only be true once spending exceeds the limit."
        ),
        "workspace_files": workspace_files,
        "editable_files": [file_name],
        "public_tests": [
            _class_case(
                "expense_increases_spent",
                module,
                class_name,
                [{"method": "add_expense", "args": [30]}],
                30,
                constructor_args=[100],
            ),
            _class_case(
                "remaining_budget",
                module,
                class_name,
                [
                    {"method": "add_expense", "args": [40]},
                    {"method": "remaining", "args": []},
                ],
                60,
                constructor_args=[100],
            ),
            _class_case(
                "over_budget_check",
                module,
                class_name,
                [
                    {"method": "add_expense", "args": [120]},
                    {"method": "is_over_budget", "args": []},
                ],
                True,
                constructor_args=[100],
            ),
        ],
        "hidden_tests": [
            _class_case(
                "ignore_negative",
                module,
                class_name,
                [
                    {"method": "add_expense", "args": [-5]},
                    {"method": "remaining", "args": []},
                ],
                50,
                constructor_args=[50],
            ),
            _class_case(
                "not_over_budget",
                module,
                class_name,
                [
                    {"method": "add_expense", "args": [10]},
                    {"method": "is_over_budget", "args": []},
                ],
                False,
                constructor_args=[100],
            ),
        ],
    }


def _build_hard_integration_orders(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("hard_integration_orders", seed)
    catalog_file = rng.choice(["catalog.py", "pricebook.py"])
    checkout_file = rng.choice(["checkout.py", "billing.py"])
    receipt_file = rng.choice(["receipt.py", "summary.py"])
    catalog_module = catalog_file[:-3]
    checkout_module = checkout_file[:-3]
    receipt_module = receipt_file[:-3]
    tax_rate = rng.choice([0.05, 0.08, 0.1])
    items = {"tea": 4.5, "coffee": 6.0, "cake": 5.5}

    workspace_files = {
        catalog_file: _code(
            f"PRICES = {items!r}",
            "",
            "def lookup_price(item_name):",
            "    return PRICES[item_name]",
        ),
        checkout_file: _code(
            f"from {catalog_module} import lookup_price",
            "",
            "def calculate_total(items, tax_rate):",
            "    subtotal = 0.0",
            "    for item_name, quantity in items.items():",
            "        subtotal += lookup_price(item_name) + quantity",
            "    return round(subtotal + tax_rate, 2)",
        ),
        receipt_file: _code(
            f"from {checkout_module} import calculate_total",
            "",
            "def render_receipt(items, tax_rate):",
            "    total = calculate_total(items, tax_rate)",
            "    return f'Total due: {int(total)}'",
        ),
    }

    total_order = round((items["tea"] * 2 + items["cake"] * 1) * (1 + tax_rate), 2)
    alt_order = round((items["coffee"] * 1 + items["cake"] * 2) * (1 + tax_rate), 2)

    return {
        "id": "hard_integration_orders",
        "difficulty": "hard",
        "family": "integration",
        "title": "Repair order checkout integration",
        "task_brief": (
            f"Repair the workspace in `{catalog_file}`, `{checkout_file}`, and `{receipt_file}`. "
            "The checkout layer should multiply item prices by quantity and apply tax to the subtotal. "
            "The receipt layer should render the rounded total with two decimal places."
        ),
        "workspace_files": workspace_files,
        "editable_files": [catalog_file, checkout_file, receipt_file],
        "public_tests": [
            _function_case(
                "checkout_total",
                checkout_module,
                "calculate_total",
                [{"tea": 2, "cake": 1}, tax_rate],
                total_order,
            ),
            _function_case(
                "receipt_render",
                receipt_module,
                "render_receipt",
                [{"tea": 2, "cake": 1}, tax_rate],
                f"Total due: {total_order:.2f}",
            ),
            _function_case(
                "alternate_order",
                checkout_module,
                "calculate_total",
                [{"coffee": 1, "cake": 2}, tax_rate],
                alt_order,
            ),
        ],
        "hidden_tests": [
            _function_case(
                "single_item",
                receipt_module,
                "render_receipt",
                [{"coffee": 1}, tax_rate],
                f"Total due: {round(items['coffee'] * (1 + tax_rate), 2):.2f}",
            ),
            _function_case(
                "empty_order",
                checkout_module,
                "calculate_total",
                [{}, tax_rate],
                0.0,
            ),
        ],
    }


def _build_hard_repair_auth(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("hard_repair_auth", seed)
    auth_file = rng.choice(["auth.py", "identity.py"])
    permissions_file = rng.choice(["permissions.py", "policy.py"])
    session_file = rng.choice(["session.py", "workspace.py"])
    auth_module = auth_file[:-3]
    permissions_module = permissions_file[:-3]
    session_module = session_file[:-3]

    workspace_files = {
        auth_file: _code(
            "USERS = {'admin': 'secret', 'guest': 'guest'}",
            "",
            "def authenticate(username, password):",
            "    return USERS.get(username) is password",
        ),
        permissions_file: _code(
            "def role_for(username):",
            "    return 'admin' if username == 'admin' else 'viewer'",
            "",
            "def can_edit(role):",
            "    return role == 'admin'",
        ),
        session_file: _code(
            f"from {auth_module} import authenticate",
            f"from {permissions_module} import can_edit, role_for",
            "",
            "def build_session(username, password):",
            "    if authenticate(username, password):",
            "        return None",
            "    role = role_for(username)",
            "    return {'user': username, 'role': role, 'can_edit': can_edit(username)}",
        ),
    }

    return {
        "id": "hard_repair_auth",
        "difficulty": "hard",
        "family": "repair",
        "title": "Repair authentication workspace",
        "task_brief": (
            f"Repair the authentication flow across `{auth_file}`, `{permissions_file}`, and `{session_file}`. "
            "Valid credentials should create a session, invalid credentials should return None, and edit permissions should depend on the resolved role."
        ),
        "workspace_files": workspace_files,
        "editable_files": [auth_file, permissions_file, session_file],
        "public_tests": [
            _function_case(
                "valid_admin_session",
                session_module,
                "build_session",
                ["admin", "secret"],
                {"user": "admin", "role": "admin", "can_edit": True},
            ),
            _function_case(
                "invalid_login",
                session_module,
                "build_session",
                ["admin", "wrong"],
                None,
            ),
            _function_case(
                "guest_permissions",
                session_module,
                "build_session",
                ["guest", "guest"],
                {"user": "guest", "role": "viewer", "can_edit": False},
            ),
        ],
        "hidden_tests": [
            _function_case(
                "unknown_user",
                session_module,
                "build_session",
                ["nobody", "secret"],
                None,
            ),
            _function_case(
                "viewer_role_check",
                permissions_module,
                "can_edit",
                ["viewer"],
                False,
            ),
        ],
    }


BUILDERS = {
    "easy_implementation_discount": _build_easy_implementation_discount,
    "easy_repair_slugify": _build_easy_repair_slugify,
    "medium_implementation_inventory": _build_medium_implementation_inventory,
    "medium_repair_budget": _build_medium_repair_budget,
    "hard_integration_orders": _build_hard_integration_orders,
    "hard_repair_auth": _build_hard_repair_auth,
}


def build_task(task_id: str, seed: int | None = None) -> dict[str, Any]:
    descriptor = get_task_by_id(task_id)
    task = BUILDERS[task_id](seed)
    task["max_test_runs"] = MAX_TEST_RUNS[descriptor["difficulty"]]
    task["max_steps"] = MAX_STEPS[descriptor["difficulty"]]
    return task

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
    {"id": "hard_integration_config", "difficulty": "hard", "family": "integration"},
    {"id": "hard_pipeline_billing", "difficulty": "hard", "family": "integration"},
    {"id": "hard_repository_tasks", "difficulty": "hard", "family": "integration"},
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
    return [f"{path} ({len(files[path].splitlines())} lines)" for path in sorted(files)]


def render_workspace(files: dict[str, str]) -> str:
    sections = []
    for path in sorted(files):
        sections.append(f"# {path}\n{files[path]}")
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
            "Expenses should increase `spent`, remaining budget should subtract spent from limit even when the result becomes negative, and over-budget detection should only be true once spending exceeds the limit."
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
                "negative_remaining_after_overspend",
                module,
                class_name,
                [
                    {"method": "add_expense", "args": [120]},
                    {"method": "remaining", "args": []},
                ],
                -20,
                constructor_args=[100],
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


def _build_hard_integration_config(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("hard_integration_config", seed)
    defaults_file = rng.choice(["defaults.py", "base_config.py"])
    parser_file = rng.choice(["parser.py", "reader.py"])
    coerce_file = rng.choice(["coerce.py", "casting.py"])
    service_file = rng.choice(["service.py", "settings.py"])
    defaults_module = defaults_file[:-3]
    parser_module = parser_file[:-3]
    coerce_module = coerce_file[:-3]
    service_module = service_file[:-3]

    workspace_files = {
        defaults_file: _code(
            "DEFAULTS = {",
            "    'retries': 1,",
            "    'timeout': 30,",
            "    'feature_enabled': False,",
            "    'service_name': 'core',",
            "}",
        ),
        parser_file: _code(
            "def parse_config(text):",
            "    parsed = {}",
            "    for raw_line in text.splitlines():",
            "        line = raw_line.strip()",
            "        if not line or line.startswith('#'):",
            "            continue",
            "        key, value = line.split('=', 1)",
            "        parsed[key.strip()] = value.strip()",
            "    return parsed",
        ),
        coerce_file: _code(
            "def coerce_value(key, value):",
            "    if key in {'retries', 'timeout'}:",
            "        return int(value)",
            "    if key == 'feature_enabled':",
            "        return value == 'True'",
            "    return value",
        ),
        service_file: _code(
            f"from {coerce_module} import coerce_value",
            f"from {defaults_module} import DEFAULTS",
            f"from {parser_module} import parse_config",
            "",
            "def build_settings(text):",
            "    parsed = parse_config(text)",
            "    settings = parsed.copy()",
            "    for key, value in parsed.items():",
            "        settings[key] = coerce_value(key, value)",
            "    return settings",
        ),
    }

    return {
        "id": "hard_integration_config",
        "difficulty": "hard",
        "family": "integration",
        "title": "Repair layered config loader",
        "task_brief": (
            f"Repair the config loading flow across `{defaults_file}`, `{parser_file}`, `{coerce_file}`, and "
            f"`{service_file}`. The loader should merge parsed overrides over defaults, preserve unspecified "
            "defaults, and coerce integer and boolean values correctly."
        ),
        "workspace_files": workspace_files,
        "editable_files": [defaults_file, parser_file, coerce_file, service_file],
        "public_tests": [
            _function_case(
                "typed_override_merge",
                service_module,
                "build_settings",
                ["retries=3\nfeature_enabled=true"],
                {
                    "retries": 3,
                    "timeout": 30,
                    "feature_enabled": True,
                    "service_name": "core",
                },
            ),
            _function_case(
                "service_override",
                service_module,
                "build_settings",
                ["timeout=10\nservice_name=jobs"],
                {
                    "retries": 1,
                    "timeout": 10,
                    "feature_enabled": False,
                    "service_name": "jobs",
                },
            ),
        ],
        "hidden_tests": [
            _function_case(
                "ignore_comments_and_spaces",
                service_module,
                "build_settings",
                ["# comment\n  feature_enabled = false  \n retries = 2"],
                {
                    "retries": 2,
                    "timeout": 30,
                    "feature_enabled": False,
                    "service_name": "core",
                },
            ),
            _function_case(
                "preserve_unknown_keys",
                service_module,
                "build_settings",
                ["timeout=45\nregion=apac"],
                {
                    "retries": 1,
                    "timeout": 45,
                    "feature_enabled": False,
                    "service_name": "core",
                    "region": "apac",
                },
            ),
        ],
    }


def _build_hard_pipeline_billing(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("hard_pipeline_billing", seed)
    normalize_file = rng.choice(["normalize.py", "cleaning.py"])
    filters_file = rng.choice(["filters.py", "rules.py"])
    report_file = rng.choice(["report.py", "totals.py"])
    pipeline_file = rng.choice(["pipeline.py", "billing_pipeline.py"])
    normalize_module = normalize_file[:-3]
    filters_module = filters_file[:-3]
    report_module = report_file[:-3]
    pipeline_module = pipeline_file[:-3]

    workspace_files = {
        normalize_file: _code(
            "def normalize_record(record):",
            "    return {",
            "        'name': record['name'].strip(),",
            "        'status': record['status'],",
            "        'amount': float(record['amount']) if record['amount'] else 0.0,",
            "    }",
        ),
        filters_file: _code(
            "def is_billable(record):",
            "    return record['status'] == 'active' and record['amount'] > 0",
        ),
        report_file: _code(
            "def summarize_billable(records):",
            "    total = sum(item['amount'] for item in records)",
            "    return {'billable_count': len(records), 'total_amount': int(total)}",
        ),
        pipeline_file: _code(
            f"from {filters_module} import is_billable",
            f"from {normalize_module} import normalize_record",
            f"from {report_module} import summarize_billable",
            "",
            "def build_report(rows):",
            "    cleaned = [normalize_record(row) for row in rows]",
            "    billable = [row for row in cleaned if is_billable(row)]",
            "    return summarize_billable(billable)",
        ),
    }

    return {
        "id": "hard_pipeline_billing",
        "difficulty": "hard",
        "family": "integration",
        "title": "Repair billing cleanup pipeline",
        "task_brief": (
            f"Repair the billing pipeline across `{normalize_file}`, `{filters_file}`, `{report_file}`, and "
            f"`{pipeline_file}`. Records must be normalized before filtering, active statuses should be trimmed "
            "and lowercased, empty amounts should become 0.0, and the final report should preserve decimal totals."
        ),
        "workspace_files": workspace_files,
        "editable_files": [normalize_file, filters_file, report_file, pipeline_file],
        "public_tests": [
            _function_case(
                "normalized_active_rows",
                pipeline_module,
                "build_report",
                [[
                    {"name": " Alpha ", "status": " ACTIVE ", "amount": "12.50"},
                    {"name": "Beta", "status": "inactive", "amount": "99.00"},
                    {"name": "Gamma", "status": "active", "amount": "7.25"},
                ]],
                {"billable_count": 2, "total_amount": 19.75},
            ),
            _function_case(
                "empty_amount_filtered",
                pipeline_module,
                "build_report",
                [[
                    {"name": "Alpha", "status": "active", "amount": ""},
                    {"name": "Beta", "status": "active", "amount": "4.00"},
                ]],
                {"billable_count": 1, "total_amount": 4.0},
            ),
        ],
        "hidden_tests": [
            _function_case(
                "ignore_negative_billable",
                pipeline_module,
                "build_report",
                [[
                    {"name": "Refund", "status": "active", "amount": "-2.00"},
                    {"name": "Work", "status": " active", "amount": "3.50"},
                ]],
                {"billable_count": 1, "total_amount": 3.5},
            ),
            _function_case(
                "all_inactive",
                pipeline_module,
                "build_report",
                [[
                    {"name": "Dormant", "status": "inactive", "amount": "6.00"},
                ]],
                {"billable_count": 0, "total_amount": 0.0},
            ),
        ],
    }


def _build_hard_repository_tasks(seed: int | None) -> dict[str, Any]:
    rng = _variant_rng("hard_repository_tasks", seed)
    schema_file = rng.choice(["schema.py", "database.py"])
    repo_file = rng.choice(["repository.py", "repo.py"])
    service_file = rng.choice(["service.py", "dashboard.py"])
    schema_module = schema_file[:-3]
    repo_module = repo_file[:-3]
    service_module = service_file[:-3]

    workspace_files = {
        schema_file: _code(
            "import sqlite3",
            "",
            "def build_connection():",
            "    conn = sqlite3.connect(':memory:')",
            "    conn.row_factory = sqlite3.Row",
            "    conn.execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)')",
            "    return conn",
        ),
        repo_file: _code(
            "def add_task(conn, title, done=False):",
            "    conn.execute(",
            "        'INSERT INTO tasks(title, done) VALUES (?, ?)',",
            "        (title, int(done)),",
            "    )",
            "    conn.commit()",
            "",
            "def open_titles(conn):",
            "    rows = conn.execute(",
            "        'SELECT title FROM tasks WHERE done = 1 ORDER BY id'",
            "    ).fetchall()",
            "    return [row['title'] for row in rows]",
        ),
        service_file: _code(
            f"from {repo_module} import add_task, open_titles",
            f"from {schema_module} import build_connection",
            "",
            "def snapshot_open_titles(entries):",
            "    conn = build_connection()",
            "    for entry in entries:",
            "        add_task(conn, entry['title'], entry.get('done', False))",
            "    return open_titles(conn)",
        ),
    }

    return {
        "id": "hard_repository_tasks",
        "difficulty": "hard",
        "family": "integration",
        "title": "Repair SQLite task repository flow",
        "task_brief": (
            f"Repair the repository workflow across `{schema_file}`, `{repo_file}`, and `{service_file}`. "
            "Open tasks should remain open by default, done tasks should be excluded from dashboard results, "
            "and result ordering should follow insertion order."
        ),
        "workspace_files": workspace_files,
        "editable_files": [schema_file, repo_file, service_file],
        "public_tests": [
            _function_case(
                "mixed_entries",
                service_module,
                "snapshot_open_titles",
                [[
                    {"title": "Ship release", "done": False},
                    {"title": "Archive notes", "done": True},
                    {"title": "Email users", "done": False},
                ]],
                ["Ship release", "Email users"],
            ),
            _function_case(
                "defaults_to_open",
                service_module,
                "snapshot_open_titles",
                [[
                    {"title": "First"},
                    {"title": "Second"},
                ]],
                ["First", "Second"],
            ),
        ],
        "hidden_tests": [
            _function_case(
                "empty_entries",
                service_module,
                "snapshot_open_titles",
                [[]],
                [],
            ),
            _function_case(
                "preserve_order_with_done_filter",
                service_module,
                "snapshot_open_titles",
                [[
                    {"title": "A", "done": False},
                    {"title": "B", "done": False},
                    {"title": "C", "done": True},
                    {"title": "D", "done": False},
                ]],
                ["A", "B", "D"],
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
    "hard_integration_config": _build_hard_integration_config,
    "hard_pipeline_billing": _build_hard_pipeline_billing,
    "hard_repository_tasks": _build_hard_repository_tasks,
}


def build_task(task_id: str, seed: int | None = None) -> dict[str, Any]:
    descriptor = get_task_by_id(task_id)
    task = BUILDERS[task_id](seed)
    task["max_test_runs"] = MAX_TEST_RUNS[descriptor["difficulty"]]
    task["max_steps"] = MAX_STEPS[descriptor["difficulty"]]
    return task

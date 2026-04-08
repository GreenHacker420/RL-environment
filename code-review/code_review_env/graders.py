from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any


HARNESS_SOURCE = dedent(
    """
    from __future__ import annotations

    import contextlib
    import importlib
    import io
    import json
    import sys
    from pathlib import Path


    def run_case(case):
        module = importlib.import_module(case["module"])

        if case["kind"] == "function":
            target = getattr(module, case["callable"])
            return target(*case["args"])

        if case["kind"] == "class":
            cls = getattr(module, case["class_name"])
            instance = cls(*case.get("constructor_args", []))
            result = None
            for step in case["steps"]:
                method = getattr(instance, step["method"])
                result = method(*step.get("args", []))
            return result

        raise ValueError(f"Unknown case kind: {case['kind']}")


    def main():
        payload = json.loads(Path(sys.argv[1]).read_text())
        sys.path.insert(0, payload["workdir"])

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        results = {
            "passed": 0,
            "total": len(payload["tests"]),
            "failures": [],
            "load_ok": True,
            "stdout": "",
            "stderr": "",
            "exit_code": 0,
        }

        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            try:
                importlib.invalidate_caches()
                for module_name in payload["modules"]:
                    importlib.import_module(module_name)
            except Exception as exc:
                results["load_ok"] = False
                results["exit_code"] = 1
                results["failures"].append(
                    {
                        "name": "module_load",
                        "detail": f"Module load failed: {type(exc).__name__}: {exc}",
                    }
                )
            else:
                for index, case in enumerate(payload["tests"], start=1):
                    label = case.get("name", f"test_{index}")
                    try:
                        actual = run_case(case)
                        if actual == case["expected"]:
                            results["passed"] += 1
                        else:
                            results["failures"].append(
                                {
                                    "name": label,
                                    "detail": f"expected {case['expected']!r}, got {actual!r}",
                                }
                            )
                    except Exception as exc:
                        results["failures"].append(
                            {
                                "name": label,
                                "detail": f"raised {type(exc).__name__}: {exc}",
                            }
                        )

        results["stdout"] = stdout_buffer.getvalue()[:2000]
        results["stderr"] = stderr_buffer.getvalue()[:2000]
        print(json.dumps(results))


    if __name__ == "__main__":
        main()
    """
).strip()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _write_workspace(workdir: Path, workspace_files: dict[str, str]) -> None:
    for path, content in workspace_files.items():
        file_path = workdir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def _workspace_modules(workspace_files: dict[str, str]) -> list[str]:
    modules: list[str] = []
    for path in workspace_files:
        if path.endswith(".py"):
            modules.append(path[:-3].replace("/", "."))
    return modules


def _parse_tree(content: str) -> ast.AST | None:
    try:
        return ast.parse(content)
    except SyntaxError:
        return None


def _contains_banned_calls(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec"}:
                return True
    return False


def _contains_wildcard_import(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    return True
    return False


def _contains_top_level_print(tree: ast.AST) -> bool:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
                return True
    return False


def quality_report(task: dict[str, Any], workspace_files: dict[str, str]) -> dict[str, Any]:
    editable_files = task.get("editable_files", list(workspace_files))
    if not editable_files:
        return {"score": 1.0, "messages": []}

    file_scores: list[float] = []
    messages: list[str] = []

    for path in editable_files:
        content = workspace_files.get(path, "")
        checks = {
            "syntax": 0.0,
            "unsafe": 1.0,
            "imports": 1.0,
            "prints": 1.0,
        }

        tree = _parse_tree(content)
        if tree is None:
            messages.append(f"{path}: syntax error")
            file_scores.append(0.0)
            continue

        checks["syntax"] = 1.0

        if _contains_banned_calls(tree):
            checks["unsafe"] = 0.0
            messages.append(f"{path}: avoid eval/exec")

        if _contains_wildcard_import(tree):
            checks["imports"] = 0.0
            messages.append(f"{path}: avoid wildcard imports")

        if _contains_top_level_print(tree):
            checks["prints"] = 0.0
            messages.append(f"{path}: remove top-level print statements")

        file_scores.append(sum(checks.values()) / len(checks))

    if not file_scores:
        return {"score": 1.0, "messages": messages}

    return {"score": sum(file_scores) / len(file_scores), "messages": messages}


def run_workspace_lint(
    workspace_files: dict[str, str],
    editable_files: list[str] | None = None,
) -> dict[str, Any]:
    selected_files = editable_files or list(workspace_files)
    quality = quality_report({"editable_files": selected_files}, workspace_files)
    issues = list(quality["messages"])
    stdout_parts: list[str] = []
    stderr = ""
    exit_code = 0 if not issues else 1

    with tempfile.TemporaryDirectory(prefix="code_review_env_lint_") as temp_dir:
        workdir = Path(temp_dir)
        _write_workspace(workdir, workspace_files)
        if selected_files:
            try:
                completed = subprocess.run(
                    ["ruff", "check", "--output-format", "concise", *selected_files],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except FileNotFoundError:
                stdout_parts.append("ruff unavailable; used built-in lint checks only.")
            except subprocess.TimeoutExpired:
                issues.append("lint timeout after 5 seconds")
                stderr = "ruff timeout"
                exit_code = 1
            else:
                raw_stdout = completed.stdout.strip()
                stderr = completed.stderr[:2000]
                if raw_stdout:
                    stdout_parts.append(raw_stdout[:2000])
                    for line in raw_stdout.splitlines():
                        stripped = line.strip()
                        if (
                            stripped
                            and stripped not in issues
                            and stripped != "All checks passed!"
                            and "Found " not in stripped
                        ):
                            issues.append(stripped)
                exit_code = max(exit_code, 0 if completed.returncode == 0 else 1)

    unique_issues = list(dict.fromkeys(issues))
    return {
        "clean": len(unique_issues) == 0,
        "issues": unique_issues[:8],
        "stdout": "\n".join(part for part in stdout_parts if part)[:2000],
        "stderr": stderr,
        "exit_code": exit_code,
    }


def run_workspace_tests(
    workspace_files: dict[str, str],
    tests: list[dict[str, Any]],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="code_review_env_") as temp_dir:
        workdir = Path(temp_dir)
        _write_workspace(workdir, workspace_files)

        payload = {
            "workdir": str(workdir),
            "modules": _workspace_modules(workspace_files),
            "tests": tests,
        }
        payload_path = workdir / "payload.json"
        harness_path = workdir / "harness.py"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        harness_path.write_text(HARNESS_SOURCE, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, str(harness_path), str(payload_path)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "passed": 0,
                "total": len(tests),
                "failures": [{"name": "runner_timeout", "detail": "Test runner timed out after 5 seconds."}],
                "load_ok": False,
                "stdout": "",
                "stderr": "runner timeout",
                "exit_code": 1,
            }

        if completed.returncode != 0:
            return {
                "passed": 0,
                "total": len(tests),
                "failures": [
                    {
                        "name": "runner_failure",
                        "detail": (completed.stderr.strip() or completed.stdout.strip() or "Runner failed."),
                    }
                ],
                "load_ok": False,
                "stdout": completed.stdout[:2000],
                "stderr": completed.stderr[:2000],
                "exit_code": completed.returncode,
            }

        try:
            payload_result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {
                "passed": 0,
                "total": len(tests),
                "failures": [{"name": "runner_failure", "detail": "Runner returned invalid JSON."}],
                "load_ok": False,
                "stdout": completed.stdout[:2000],
                "stderr": completed.stderr[:2000],
                "exit_code": 1,
            }

        return payload_result


def evaluate_workspace(
    task: dict[str, Any],
    workspace_files: dict[str, str],
    run_hidden: bool = False,
) -> dict[str, Any]:
    public_results = run_workspace_tests(workspace_files, task["public_tests"])
    public_total = int(public_results["total"])
    public_passed = int(public_results["passed"])
    public_ratio = 0.0 if public_total == 0 else public_passed / public_total

    hidden_results: dict[str, Any] | None = None
    hidden_total = len(task["hidden_tests"])
    hidden_passed = 0
    hidden_ratio = 0.0
    if run_hidden:
        hidden_results = run_workspace_tests(workspace_files, task["hidden_tests"])
        hidden_total = int(hidden_results["total"])
        hidden_passed = int(hidden_results["passed"])
        hidden_ratio = 0.0 if hidden_total == 0 else hidden_passed / hidden_total

    quality = quality_report(task, workspace_files)
    hidden_component = hidden_ratio if run_hidden else 0.0
    load_validity = 1.0 if public_results.get("load_ok", False) and (not hidden_results or hidden_results.get("load_ok", False)) else 0.0
    score = _clamp(
        (0.35 * public_ratio)
        + (0.25 * hidden_component)
        + (0.15 * float(quality["score"]))
        + (0.10 * load_validity)
    )

    public_failures = public_results.get("failures", [])
    hidden_failures = hidden_results.get("failures", []) if hidden_results else []
    failing_tests = [failure["name"] for failure in public_failures]
    failure_details = [failure["detail"] for failure in public_failures]

    if run_hidden and hidden_results and hidden_failures:
        failing_tests.extend(failure["name"] for failure in hidden_failures[:2])
        failure_details.extend(failure["detail"] for failure in hidden_failures[:2])

    if quality["messages"]:
        failure_details.extend(quality["messages"][:2])

    active_results = hidden_results if run_hidden and hidden_results is not None else public_results

    return {
        "score": score,
        "public_passed": public_passed,
        "public_total": public_total,
        "public_ratio": public_ratio,
        "hidden_passed": hidden_passed,
        "hidden_total": hidden_total,
        "hidden_ratio": hidden_ratio,
        "hidden_checked": run_hidden,
        "success": run_hidden and (hidden_total == 0 or hidden_passed == hidden_total),
        "stdout": active_results.get("stdout", ""),
        "stderr": active_results.get("stderr", ""),
        "exit_code": int(active_results.get("exit_code", 0)),
        "failing_tests": failing_tests[:5],
        "failure_details": failure_details[:5],
        "quality_score": float(quality["score"]),
        "quality_messages": quality["messages"],
        "load_validity": load_validity,
    }

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

    import importlib
    import json
    import sys
    from pathlib import Path


    def run_case(task, case):
        kind = task["task_kind"]
        module_name = task.get("entry_module", "submission")
        entry_point = task["entry_point"]
        module = importlib.import_module(module_name)

        if kind == "function":
            target = getattr(module, entry_point)
            return target(*case["input"])

        if kind == "class":
            cls = getattr(module, entry_point)
            if "values" in case and "find" in case:
                instance = cls()
                for value in case["values"]:
                    instance.append(value)
                return instance.find(case["find"])

            if "steps" in case:
                if "start" in case:
                    instance = cls(case["start"])
                else:
                    instance = cls()
                result = None
                for step in case["steps"]:
                    method = getattr(instance, step[0])
                    result = method(*step[1:])
                return result

            instance = cls()
            method = getattr(instance, case["method"])
            return method(case["input"])

        target = getattr(module, entry_point)
        return target(*case.get("args", []))


    def main():
        payload = json.loads(Path(sys.argv[1]).read_text())
        sys.path.insert(0, payload["workdir"])

        results = {"passed": 0, "total": len(payload["tests"]), "failures": [], "load_ok": True}
        try:
            importlib.invalidate_caches()
            importlib.import_module(payload["entry_module"])
        except Exception as exc:
            results["load_ok"] = False
            results["failures"].append(f"Module load failed: {type(exc).__name__}: {exc}")
            print(json.dumps(results))
            return

        for index, case in enumerate(payload["tests"], start=1):
            label = case.get("name", f"test_{index}")
            try:
                actual = run_case(payload["task"], case)
                if "expected_error" in case:
                    results["failures"].append(
                        f"{label}: expected {case['expected_error']}, but call succeeded with {actual!r}"
                    )
                elif actual == case["expected"]:
                    results["passed"] += 1
                else:
                    results["failures"].append(
                        f"{label}: expected {case['expected']!r}, got {actual!r}"
                    )
            except Exception as exc:
                if case.get("expected_error") == type(exc).__name__:
                    results["passed"] += 1
                else:
                    results["failures"].append(f"{label}: raised {type(exc).__name__}: {exc}")

        print(json.dumps(results))


    if __name__ == "__main__":
        main()
    """
).strip()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _syntax_ok(code: str | dict[str, str]) -> bool:
    if isinstance(code, str):
        if not code.strip():
            return False
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    if isinstance(code, dict) and code:
        try:
            for value in code.values():
                if not isinstance(value, str) or not value.strip():
                    return False
                ast.parse(value)
            return True
        except SyntaxError:
            return False

    return False


def _candidate_code(task: dict[str, Any], fixed_code: str | dict[str, str]) -> str | dict[str, str]:
    if task["task_kind"] in {"function", "class"}:
        return fixed_code if isinstance(fixed_code, str) else ""

    if isinstance(fixed_code, dict):
        merged = dict(task["prompt"])
        merged.update(fixed_code)
        return merged

    return {}


def _write_submission_files(workdir: Path, task: dict[str, Any], candidate: str | dict[str, str]) -> str:
    if task["task_kind"] in {"function", "class"}:
        (workdir / "submission.py").write_text(str(candidate), encoding="utf-8")
        return "submission"

    for filename, content in candidate.items():
        (workdir / filename).write_text(content, encoding="utf-8")
    return str(task["entry_module"])


def _run_tests(task: dict[str, Any], candidate: str | dict[str, str], tests: list[dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="code_review_env_") as tmpdir:
        workdir = Path(tmpdir)
        entry_module = _write_submission_files(workdir, task, candidate)
        payload = {
            "workdir": str(workdir),
            "entry_module": entry_module,
            "task": {
                "task_kind": task["task_kind"],
                "entry_point": task["entry_point"],
                "entry_module": entry_module,
            },
            "tests": tests,
        }
        payload_path = workdir / "payload.json"
        harness_path = workdir / "harness.py"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        harness_path.write_text(HARNESS_SOURCE, encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(harness_path), str(payload_path)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if completed.returncode != 0:
            error_text = completed.stderr.strip() or completed.stdout.strip() or "Subprocess failed."
            return {
                "passed": 0,
                "total": len(tests),
                "failures": [f"Runner failure: {error_text}"],
                "load_ok": False,
            }

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {
                "passed": 0,
                "total": len(tests),
                "failures": [f"Invalid harness output: {completed.stdout.strip()}"],
                "load_ok": False,
            }


def evaluate_submission(
    task: dict[str, Any],
    action: Any,
    previous_best_public_ratio: float = 0.0,
) -> dict[str, Any]:
    candidate = _candidate_code(task, getattr(action, "fixed_code", ""))
    syntax_ok = _syntax_ok(candidate)
    public_total = len(task["public_tests"])
    hidden_total = len(task["hidden_tests"])

    if not syntax_ok:
        return {
            "score": 0.0,
            "feedback": "Submission did not parse as valid Python.",
            "public_passed": 0,
            "public_total": public_total,
            "hidden_passed": 0,
            "hidden_total": hidden_total,
            "public_ratio": 0.0,
            "hidden_ratio": 0.0,
            "success": False,
        }

    public_results = _run_tests(task, candidate, task["public_tests"])
    public_passed = int(public_results["passed"])
    public_ratio = 0.0 if public_total == 0 else public_passed / public_total

    hidden_passed = 0
    hidden_ratio = 0.0
    hidden_status = "hidden tests not checked yet"
    if public_ratio == 1.0 and hidden_total:
        hidden_results = _run_tests(task, candidate, task["hidden_tests"])
        hidden_passed = int(hidden_results["passed"])
        hidden_ratio = 0.0 if hidden_total == 0 else hidden_passed / hidden_total
        hidden_status = f"hidden tests {hidden_passed}/{hidden_total}"

    validity_score = 1.0 if public_results.get("load_ok", False) else 0.0
    improvement = max(0.0, public_ratio - previous_best_public_ratio)
    test_signal = public_ratio if public_ratio < 1.0 or hidden_total == 0 else (0.7 * public_ratio) + (0.3 * hidden_ratio)
    score = _clamp((0.75 * test_signal) + (0.15 * validity_score) + (0.10 * improvement))

    failure_preview = public_results.get("failures", [])[:2]
    if failure_preview:
        details = " | ".join(failure_preview)
    elif public_ratio == 1.0 and hidden_total and hidden_ratio < 1.0:
        details = "Public tests pass, but hidden validation still fails."
    else:
        details = "All visible tests passed."

    return {
        "score": score,
        "feedback": (
            f"Public tests {public_passed}/{public_total}. "
            f"{hidden_status}. "
            f"{details}"
        ),
        "public_passed": public_passed,
        "public_total": public_total,
        "hidden_passed": hidden_passed,
        "hidden_total": hidden_total,
        "public_ratio": public_ratio,
        "hidden_ratio": hidden_ratio,
        "success": public_ratio == 1.0 and (hidden_total == 0 or hidden_ratio == 1.0),
    }


def grade_easy(task: dict[str, Any], action: Any) -> tuple[float, str]:
    result = evaluate_submission(task, action)
    return float(result["score"]), str(result["feedback"])


def grade_medium(task: dict[str, Any], action: Any) -> tuple[float, str]:
    result = evaluate_submission(task, action)
    return float(result["score"]), str(result["feedback"])


def grade_hard(task: dict[str, Any], action: Any) -> tuple[float, str]:
    result = evaluate_submission(task, action)
    return float(result["score"]), str(result["feedback"])

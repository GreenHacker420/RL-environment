from __future__ import annotations

import ast
from typing import Any


HARD_SUMMARY_KEYWORDS = {
    "auth",
    "calculator",
    "formatter",
    "function",
    "import",
    "integration",
    "module",
    "parser",
    "return",
    "session",
    "validator",
}


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


def _contains_keyword(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _syntax_ok(code: Any) -> bool:
    if isinstance(code, str):
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    if isinstance(code, dict) and code:
        try:
            for value in code.values():
                if not isinstance(value, str):
                    return False
                ast.parse(value)
            return True
        except SyntaxError:
            return False

    return False


def _normalize_reports(action: Any) -> list[dict[str, Any]]:
    if isinstance(action.bug_line, list):
        reports: list[dict[str, Any]] = []
        for item in action.bug_line:
            if not isinstance(item, dict):
                continue
            line_value = item.get("line", item.get("bug_line", -1))
            try:
                line_number = int(line_value)
            except (TypeError, ValueError):
                line_number = -1
            reports.append(
                {
                    "file": str(item.get("file", "")),
                    "line": line_number,
                    "bug_type": str(item.get("bug_type", item.get("type", ""))),
                    "description": str(
                        item.get("description", action.description or "")
                    ),
                }
            )
        return reports

    if isinstance(action.bug_line, int):
        return [
            {
                "file": "",
                "line": action.bug_line,
                "bug_type": str(action.bug_type),
                "description": str(action.description),
            }
        ]

    return []


def _match_reports(
    predicted: list[dict[str, Any]],
    truth: list[dict[str, Any]],
    require_file: bool,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], int, int]:
    matched: list[tuple[dict[str, Any], dict[str, Any]]] = []
    used_truth: set[int] = set()
    false_positives = 0

    for report in predicted:
        candidates = []
        for index, bug in enumerate(truth):
            if index in used_truth:
                continue
            if require_file and report["file"] != bug["file"]:
                continue
            if abs(report["line"] - bug["line"]) <= 1:
                candidates.append((abs(report["line"] - bug["line"]), index))

        if not candidates:
            false_positives += 1
            continue

        _, best_index = min(candidates, key=lambda item: item[0])
        used_truth.add(best_index)
        matched.append((report, truth[best_index]))

    false_negatives = len(truth) - len(used_truth)
    return matched, false_positives, false_negatives


def grade_easy(task: dict[str, Any], action: Any) -> tuple[float, str]:
    if (
        task.get("safety_bug_type") == "runtime"
        and str(action.bug_type).lower() == "style"
    ):
        return 0.0, "Safety rule triggered: runtime bug mislabeled as style."

    score = 0.0
    feedback: list[str] = []

    if isinstance(action.bug_line, int) and abs(action.bug_line - task["true_bug_line"]) <= 1:
        score += 0.4
        feedback.append("Bug line matched.")
    else:
        feedback.append(
            f"Expected line near {task['true_bug_line']}, received {action.bug_line}."
        )

    if str(action.bug_type) == task["true_bug_type"]:
        score += 0.3
        feedback.append("Bug type matched.")
    else:
        feedback.append(f"Expected bug type '{task['true_bug_type']}'.")

    if _syntax_ok(action.fixed_code) and _contains_keyword(str(action.description), task["keywords"]):
        score += 0.3
        feedback.append("Fix parsed and description used task keywords.")
    else:
        feedback.append("Fix or description check failed.")

    return _clamp(score), " ".join(feedback)


def grade_medium(task: dict[str, Any], action: Any) -> tuple[float, str]:
    predicted = _normalize_reports(action)
    truth = task["true_bugs"]
    matched, false_positives, false_negatives = _match_reports(
        predicted=predicted,
        truth=truth,
        require_file=False,
    )

    score = 0.0
    feedback: list[str] = []

    for report, bug in matched:
        score += 0.25
        if report["bug_type"] == bug["bug_type"]:
            score += 0.15
        if _contains_keyword(report["description"], bug["keywords"]):
            score += 0.10
        feedback.append(
            f"Matched bug near line {bug['line']} with type '{bug['bug_type']}'."
        )

    if false_negatives:
        score -= 0.25 * false_negatives
        feedback.append(f"Missed {false_negatives} true bug(s).")

    if false_positives:
        score -= 0.10 * false_positives
        feedback.append(f"Reported {false_positives} extra bug(s).")

    if _syntax_ok(action.fixed_code):
        score += 0.20
        feedback.append("Fixed code parsed successfully.")
    else:
        feedback.append("Fixed code did not parse.")

    return _clamp(score), " ".join(feedback)


def grade_hard(task: dict[str, Any], action: Any) -> tuple[float, str]:
    predicted = _normalize_reports(action)
    truth = task["true_bugs"]
    matched, false_positives, false_negatives = _match_reports(
        predicted=predicted,
        truth=truth,
        require_file=True,
    )

    true_positives = len(matched)
    denominator = (2 * true_positives) + false_positives + false_negatives
    f1 = 0.0 if denominator == 0 else (2 * true_positives) / denominator

    syntax_score = 1.0 if _syntax_ok(action.fixed_code) else 0.0
    cross_module_found = any(bug["cross_module"] for _, bug in matched)

    summary_hits = {
        keyword for keyword in HARD_SUMMARY_KEYWORDS if keyword in str(action.description).lower()
    }
    summary_score = 1.0 if len(summary_hits) >= 3 else 0.0

    score = (
        0.40 * f1
        + 0.30 * syntax_score
        + 0.20 * (1.0 if cross_module_found else 0.0)
        + 0.10 * summary_score
    )

    feedback = (
        f"Identification F1={f1:.2f}. "
        f"Fix syntax={'ok' if syntax_score else 'invalid'}. "
        f"Cross-module bug={'found' if cross_module_found else 'missing'}. "
        f"Summary keywords={len(summary_hits)}."
    )
    return _clamp(score), feedback

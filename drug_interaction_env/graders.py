from __future__ import annotations

from models import DrugAction
from tasks import TaskConfig, normalize_drug_name


GT_SEVERITY = "severity"
GT_REQUIRED_KEYWORDS = "required_keywords"
GT_INTERACTIONS = "interactions"
GT_TRIAGE = "triage"
GT_CRITICAL_INTERACTION = "critical_interaction"
GT_MEDICATION_CHANGE = "medication_change"
GT_TARGET_DRUGS = "target_drugs"

SEVERITY_ORDER = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}
TRIAGE_ORDER = {"normal": 0, "caution": 1, "emergency": 2}


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def _severity_score(true_value: str, predicted: str, exact: float, off_by_one: float) -> float:
    true_rank = SEVERITY_ORDER.get(true_value, -10)
    predicted_rank = SEVERITY_ORDER.get(predicted, -10)
    if true_rank == predicted_rank:
        return exact
    if abs(true_rank - predicted_rank) == 1:
        return off_by_one
    return 0.0


def _triage_score(true_value: str, predicted: str) -> float:
    true_rank = TRIAGE_ORDER.get(true_value, -10)
    predicted_rank = TRIAGE_ORDER.get(predicted, -10)
    if true_rank == predicted_rank:
        return 0.40
    if abs(true_rank - predicted_rank) == 1:
        return 0.15
    return 0.0


def _pair_key(drug1: str, drug2: str) -> frozenset[str]:
    return frozenset({normalize_drug_name(drug1), normalize_drug_name(drug2)})


def grade_easy_task(task: TaskConfig, action: DrugAction) -> tuple[float, str]:
    ground_truth = task.ground_truth
    true_severity = str(ground_truth[GT_SEVERITY]).lower()
    predicted_severity = action.severity.lower()
    keywords = list(ground_truth[GT_REQUIRED_KEYWORDS])

    if true_severity != "none" and predicted_severity == "none":
        return 0.0, "SAFETY VIOLATION: dangerous interaction misclassified as none"

    severity_points = _severity_score(true_severity, predicted_severity, 0.60, 0.25)
    keyword_hits = _count_keyword_hits(action.explanation, keywords)
    if keyword_hits >= 2:
        explanation_points = 0.40
    elif keyword_hits == 1:
        explanation_points = 0.20
    else:
        explanation_points = 0.0

    total = min(1.0, severity_points + explanation_points)
    feedback = (
        f"Severity score: {severity_points:.2f} (predicted={predicted_severity}, true={true_severity}). "
        f"Explanation score: {explanation_points:.2f} from {keyword_hits} keyword hits. "
        f"Total: {total:.2f}."
    )
    return total, feedback


def grade_medium_task(task: TaskConfig, action: DrugAction) -> tuple[float, str]:
    truth_pairs = {
        _pair_key(item["drug1"], item["drug2"]): item
        for item in task.ground_truth[GT_INTERACTIONS]
    }
    predicted_pairs = {
        _pair_key(item.get("drug1", ""), item.get("drug2", "")): item
        for item in action.interactions
        if item.get("drug1") and item.get("drug2")
    }

    n_pairs = max(1, len(truth_pairs))
    total = 0.0
    correct_pairs: list[str] = []
    missed_pairs: list[str] = []
    false_positives: list[str] = []

    for key, predicted in predicted_pairs.items():
        truth = truth_pairs.get(key)
        label = " + ".join(sorted(key))
        if truth is None:
            total -= 0.15 / n_pairs
            false_positives.append(label)
            continue
        pair_score = _severity_score(
            str(truth[GT_SEVERITY]).lower(),
            str(predicted.get(GT_SEVERITY, "")).lower(),
            1.0 / n_pairs,
            0.5 / n_pairs,
        )
        total += pair_score
        if pair_score > 0:
            correct_pairs.append(label)

    for key in truth_pairs:
        if key not in predicted_pairs:
            total -= 0.30 / n_pairs
            missed_pairs.append(" + ".join(sorted(key)))

    total = max(0.0, min(1.0, total))
    feedback = (
        f"Correctly identified pairs: {correct_pairs or ['none']}. "
        f"Missed pairs: {missed_pairs or ['none']}. "
        f"False positives: {false_positives or ['none']}. "
        f"Total: {total:.2f}."
    )
    return total, feedback


def _critical_interaction_found(task: TaskConfig, action: DrugAction) -> bool:
    critical = task.ground_truth[GT_CRITICAL_INTERACTION]
    expected = _pair_key(critical["drug1"], critical["drug2"])

    for pair in action.interactions:
        if _pair_key(pair.get("drug1", ""), pair.get("drug2", "")) == expected:
            return True

    explanation = action.explanation.lower()
    return all(drug in explanation for drug in expected)


def grade_hard_task(task: TaskConfig, action: DrugAction) -> tuple[float, str]:
    ground_truth = task.ground_truth
    triage_points = _triage_score(ground_truth[GT_TRIAGE], action.triage.lower())
    critical_points = 0.30 if _critical_interaction_found(task, action) else 0.0

    advice_text = action.revised_medications.lower()
    target_drugs = [normalize_drug_name(item) for item in ground_truth[GT_TARGET_DRUGS]]
    medication_change_points = (
        0.15 if any(drug in advice_text for drug in target_drugs) else 0.0
    )

    keyword_hits = _count_keyword_hits(action.explanation, list(ground_truth[GT_REQUIRED_KEYWORDS]))
    if keyword_hits >= 3:
        explanation_points = 0.15
    elif keyword_hits >= 1:
        explanation_points = 0.07
    else:
        explanation_points = 0.0

    total = triage_points + critical_points + medication_change_points + explanation_points
    safety_override = (
        ground_truth[GT_TRIAGE] == "emergency" and action.triage.lower() == "normal"
    )
    if safety_override:
        total *= 0.1

    total = max(0.0, min(1.0, total))
    feedback = (
        f"Triage score: {triage_points:.2f}. "
        f"Critical interaction score: {critical_points:.2f}. "
        f"Medication change score: {medication_change_points:.2f}. "
        f"Explanation score: {explanation_points:.2f} from {keyword_hits} keyword hits. "
        f"{'Safety override applied. ' if safety_override else ''}"
        f"Total: {total:.2f}."
    )
    return total, feedback


def grade_response(task: TaskConfig, action: DrugAction) -> tuple[float, str]:
    graders = {
        "easy": grade_easy_task,
        "medium": grade_medium_task,
        "hard": grade_hard_task,
    }
    return graders[task.task_type](task, action)

from models import DrugAction
from graders import grade_easy_task, grade_hard_task, grade_medium_task
from tasks import EASY_TASKS, HARD_TASKS, MEDIUM_TASKS


def test_easy_exact_severity_and_keywords_scores_full_credit() -> None:
    task = EASY_TASKS[0]
    action = DrugAction(
        severity="severe",
        explanation="This causes bleeding and hemorrhage from additive anticoagulant effects.",
    )
    score, _ = grade_easy_task(task, action)
    assert score == 1.0


def test_easy_correct_severity_wrong_keywords_scores_sixty_percent() -> None:
    task = EASY_TASKS[0]
    action = DrugAction(
        severity="severe",
        explanation="There is an interaction but the mechanism is not described well.",
    )
    score, _ = grade_easy_task(task, action)
    assert score == 0.60


def test_easy_wrong_severity_correct_keywords_scores_forty_percent() -> None:
    task = EASY_TASKS[0]
    action = DrugAction(
        severity="mild",
        explanation="The combination raises bleeding and hemorrhage risk.",
    )
    score, _ = grade_easy_task(task, action)
    assert score == 0.40


def test_easy_safety_violation_returns_zero() -> None:
    task = EASY_TASKS[0]
    action = DrugAction(severity="none", explanation="No interaction.")
    score, feedback = grade_easy_task(task, action)
    assert score == 0.0
    assert "SAFETY VIOLATION" in feedback


def test_medium_all_pairs_correct_scores_full_credit() -> None:
    task = MEDIUM_TASKS[0]
    action = DrugAction(
        interactions=[
            {"drug1": "warfarin", "drug2": "aspirin", "severity": "severe"},
            {"drug1": "metformin", "drug2": "ibuprofen", "severity": "moderate"},
        ]
    )
    score, _ = grade_medium_task(task, action)
    assert score == 1.0


def test_medium_all_pairs_missed_scores_zero() -> None:
    task = MEDIUM_TASKS[0]
    action = DrugAction(interactions=[])
    score, _ = grade_medium_task(task, action)
    assert score == 0.0


def test_medium_hallucinated_pair_penalized() -> None:
    task = MEDIUM_TASKS[0]
    action = DrugAction(
        interactions=[
            {"drug1": "warfarin", "drug2": "aspirin", "severity": "severe"},
            {"drug1": "metformin", "drug2": "ibuprofen", "severity": "moderate"},
            {"drug1": "omeprazole", "drug2": "metformin", "severity": "mild"},
        ]
    )
    score, _ = grade_medium_task(task, action)
    assert 0.0 < score < 1.0


def test_hard_all_correct_scores_full_credit() -> None:
    task = HARD_TASKS[0]
    action = DrugAction(
        triage="emergency",
        explanation="Emergency bleeding and hemorrhage from the warfarin and aspirin anticoagulant combination with hypotension.",
        interactions=[{"drug1": "warfarin", "drug2": "aspirin", "severity": "severe"}],
        revised_medications="Hold warfarin and aspirin immediately.",
    )
    score, _ = grade_hard_task(task, action)
    assert score == 1.0


def test_hard_normal_in_emergency_case_is_very_low() -> None:
    task = HARD_TASKS[1]
    action = DrugAction(
        triage="normal",
        explanation="Serotonin syndrome with clonus and hyperthermia from sertraline and tramadol.",
        interactions=[{"drug1": "sertraline", "drug2": "tramadol", "severity": "severe"}],
        revised_medications="Stop sertraline and tramadol immediately.",
    )
    score, _ = grade_hard_task(task, action)
    assert score < 0.1


def test_hard_partial_credit_when_interaction_missing() -> None:
    task = HARD_TASKS[2]
    action = DrugAction(
        triage="caution",
        explanation="This looks like hyperkalemia with potassium elevation and arrhythmia risk.",
        revised_medications="Stop potassium chloride and review the regimen.",
    )
    score, _ = grade_hard_task(task, action)
    assert 0.0 < score < 1.0

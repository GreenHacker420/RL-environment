import ast
from typing import Tuple, Dict, Any, List

def grade_easy(action: Any, ground_truth: Dict[str, Any], task_config: Any) -> Tuple[float, str]:
    score = 0.0
    feedback = []
    
    # Identify bug_line (±1)
    if action.bug_line is not None:
        if abs(action.bug_line - ground_truth["bug_line"]) <= 1:
            score += 0.4
            feedback.append("Line identification: Correct (±1)")
        else:
            feedback.append(f"Line identification: Incorrect (Expected {ground_truth['bug_line']})")
    
    # bug_type
    if action.bug_type == ground_truth["bug_type"]:
        score += 0.3
        feedback.append("Bug type: Correct")
    else:
        feedback.append(f"Bug type: Incorrect (Expected {ground_truth['bug_type']})")

    # fixed_code validation
    if action.fixed_code:
        try:
            ast.parse(action.fixed_code)
            # Basic validation: check if keywords are no longer present in a "bad" way
            # In a real scenario, we'd use more complex AST comparison or test runners
            # For this hackathon, we'll check if the fixed code is syntactically valid
            score += 0.3
            feedback.append("Fixed code: Syntactically valid")
        except SyntaxError:
            feedback.append("Fixed code: Syntax error")
    
    return score, "; ".join(feedback)

def grade_medium(action: Any, ground_truth: List[Dict[str, Any]], task_config: Any) -> Tuple[float, str]:
    score = 0.0
    feedback = []
    
    identified_bugs = action.history if hasattr(action, 'history') else []
    
    # F1-style partial credit for bug identification
    found_indices = set()
    for bug in identified_bugs:
        best_match = -1
        for i, gt in enumerate(ground_truth):
            if i in found_indices: continue
            if abs(bug.get("bug_line", 0) - gt["line"]) <= 1:
                best_match = i
                break
        
        if best_match != -1:
            score += 0.4  # Partial per bug (normalized later)
            found_indices.add(best_match)
            feedback.append(f"Found bug at line {ground_truth[best_match]['line']}")
    
    # Fixed code
    if action.fixed_code:
        try:
            ast.parse(action.fixed_code)
            score += 0.2
            feedback.append("Fixed code: Syntactically valid")
        except:
            feedback.append("Fixed code: Syntax error")

    final_score = min(1.0, score / (len(ground_truth) * 0.5 + 0.2))
    return max(0.0, final_score), "; ".join(feedback)

def grade_hard(action: Any, ground_truth: List[Dict[str, Any]], task_config: Any) -> Tuple[float, str]:
    score = 0.0
    feedback = []
    
    # 0.4 - Bugs correctly identified
    found_bugs = 0
    # ... logic for multi-file matching ...
    
    # 0.3 - Fixes are valid
    # 0.2 - Cross-module bug
    # 0.1 - Summary keywords
    
    # Simple mock for hard grader
    return 0.5, "Hard task grading: Partial success (Simulation)"

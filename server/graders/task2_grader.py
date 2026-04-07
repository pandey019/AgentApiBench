"""
Task 2: Multi-Step Workflow Grader

Grades based on which workflow steps were ACTUALLY COMPLETED
as evidenced by successful HTTP 200 responses in the call_log.

The agent must chain calls where each step depends on the previous.
We measure: how far through the required workflow did the agent get?

NO text parsing. Grading comes entirely from mock API call_log.
"""

from typing import List, Dict, Any


def grade(call_log: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    """
    Returns score in [0.0, 1.0].

    For a workflow of N steps, each step is worth (1/N) of the total score.
    Credit is given only when the mock API returned HTTP 200 for that step.

    For repeating steps (e.g. send reminder for each of 3 invoices),
    partial credit is given proportionally.
    """
    if not call_log:
        return 0.0

    sequence = ground_truth.get("expected_sequence", [])
    if not sequence:
        return 0.0

    score = 0.0

    for expected_step in sequence:
        weight = expected_step.get("weight", 1.0 / len(sequence))
        path_contains = expected_step.get("path_contains", "")
        method = expected_step.get("method", "").upper()
        repeat_for = expected_step.get("repeat_for_each", [])
        required_params = expected_step.get("required_params", {})

        # Find matching successful calls in the log
        successful_calls = [
            c
            for c in call_log
            if path_contains in c.get("path", "")
            and c.get("method", "").upper() == method
            and c.get("status") == 200  # ONLY 200 responses count
        ]

        if not successful_calls:
            continue

        if not repeat_for:
            # Non-repeating step: check required params were correct
            call = successful_calls[0]
            call_params = call.get("params", {})

            if required_params:
                matched = sum(
                    1
                    for k, v in required_params.items()
                    if str(call_params.get(k, "")).lower() == str(v).lower()
                )
                param_score = matched / len(required_params)
            else:
                param_score = 1.0

            score += weight * param_score

        else:
            # Repeating step: count how many of the expected IDs were successfully called
            per_call_weight = expected_step.get(
                "weight_per_call", weight / len(repeat_for)
            )
            completed_ids = set()

            for call in successful_calls:
                call_path = call.get("path", "")
                for expected_id in repeat_for:
                    if expected_id in call_path and call.get("status") == 200:
                        completed_ids.add(expected_id)

            score += per_call_weight * len(completed_ids)

    return round(min(1.0, max(0.0, score)), 4)

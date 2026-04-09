"""
Task 1: Single API Call Grader

Grades purely from the mock API call_log.
The agent gets credit for making API calls that the mock server accepted.
We check: was the right endpoint hit? Did it return 200? Were correct params used?

NO text parsing. NO action field inspection. Only what the mock API recorded.
"""

from typing import List, Dict, Any


def grade(call_log: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    """
    Returns score in [0.0, 1.0].

    Scoring breakdown:
    - 0.40: Correct endpoint was called (path matches ground truth)
    - 0.30: Call returned HTTP 200 (auth was correct AND params were valid)
    - 0.30: Required query parameters were present and correct

    The mock API enforces authentication and parameter validation.
    A 200 response means the agent got auth correct — no need to re-check headers.
    A 401 means auth was wrong. A 422 means params were wrong.
    We read these signals from the call_log.
    """
    if not call_log:
        return 0.0

    score = 0.0
    required_path = ground_truth.get("path", "")
    required_params = ground_truth.get("required_params", {})

    # Find calls to the correct endpoint
    correct_endpoint_calls = [c for c in call_log if required_path in c.get("path", "")]

    if not correct_endpoint_calls:
        return 0.0  # Agent never called the right endpoint

    # Agent hit the right endpoint
    score += 0.40

    # Find successful calls (HTTP 200 = auth correct + params valid)
    successful_calls = [c for c in correct_endpoint_calls if c.get("status") == 200]

    if successful_calls:
        score += 0.30  # Correct auth (mock API rejected 401s — agent passed)

        # Check if required params appeared in the successful call
        call = successful_calls[0]
        call_params = call.get("params", {})
        if required_params:
            matched = sum(
                1
                for k, v in required_params.items()
                if str(call_params.get(k, "")).lower() == str(v).lower()
            )
            score += 0.30 * (matched / len(required_params))
        else:
            score += 0.30  # No params required — full credit
    else:
        # Check for partial credit: got past auth (not 401) but had bad params (422)
        non_auth_errors = [
            c for c in correct_endpoint_calls if c.get("status") not in [401, 403]
        ]
        if non_auth_errors:
            score += 0.15  # Got auth right but params were wrong

    score = round(min(1.0, max(0.0, score)), 4)
    score = min(0.95, max(0.05, score))
    return score

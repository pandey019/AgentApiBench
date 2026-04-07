"""
Task 3: Debug & Fix Grader

The environment contains a broken API client with 3 planted bugs.
Each bug causes a specific HTTP error code from the mock API.

Grading logic:
- The agent earns credit for each bug it fixes.
- We detect bug fixes by watching the error codes DISAPPEAR from call_log.
- If the agent was previously getting 401s and then got past them → Bug 1 fixed.
- If the agent got past 405 errors → Bug 2 fixed.
- If the agent achieved a 200 response → Bug 3 (and all bugs) fixed.

This is 100% deterministic grading from HTTP status codes. No text parsing.
"""

from typing import List, Dict, Any


def grade(call_log: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> float:
    """
    Returns score in [0.0, 1.0].

    Bug weights:
    - Bug 1 (wrong auth format → 401): 0.30
    - Bug 2 (wrong HTTP method → 405): 0.30
    - Bug 3 (missing required field → 422): 0.40

    Credit given when the agent's calls show the error RESOLVED.
    """
    if not call_log:
        return 0.0

    bugs = ground_truth.get("bugs", [])
    score = 0.0

    # Extract all status codes seen in call_log for the target endpoint
    target_path = ground_truth.get("target_path", "/payments")
    relevant_calls = [c for c in call_log if target_path in c.get("path", "")]

    if not relevant_calls:
        return 0.0

    statuses = [c.get("status") for c in relevant_calls]

    for bug in bugs:
        bug_id = bug["id"]
        weight = bug["weight"]

        if bug_id == "bug_auth":
            # Bug 1 causes 401. Fixed if agent ever got a non-401 response.
            # (Getting past 401 means auth header was correct)
            if any(s != 401 for s in statuses):
                score += weight

        elif bug_id == "bug_method":
            # Bug 2 causes 405. Fixed if agent ever got non-405 after fixing auth.
            # Must have also fixed auth first (no 401 on that call)
            non_auth_calls = [c for c in relevant_calls if c.get("status") != 401]
            if any(c.get("status") != 405 for c in non_auth_calls):
                score += weight

        elif bug_id == "bug_currency":
            # Bug 3 causes 422. Fixed ONLY if agent got HTTP 200.
            # 200 means ALL bugs were fixed simultaneously.
            if any(s == 200 for s in statuses):
                score += weight

    # Full completion bonus: agent achieved 200 (all bugs fixed)
    if any(s == 200 for s in statuses):
        score = min(1.0, score * 1.05)  # 5% bonus

    return round(min(1.0, max(0.0, score)), 4)

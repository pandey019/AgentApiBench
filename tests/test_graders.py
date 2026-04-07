"""
Proves graders are deterministic: same input always produces same output.
This is a disqualification criterion — graders must be deterministic.
"""

import pytest
from server.graders import task1_grader, task2_grader, task3_grader


# ─── Task 1 test data ─────────────────────────────────────────────────────────

TASK1_GT = {
    "path": "/customers/cust_4821",
    "required_params": {"include": "subscription"},
}

TASK1_PERFECT_LOG = [
    {
        "method": "GET",
        "path": "/v1/customers/cust_4821",
        "params": {"include": "subscription"},
        "status": 200,
        "response": {"id": "cust_4821", "name": "Acme Corp"},
    }
]

TASK1_AUTH_FAIL_LOG = [
    {
        "method": "GET",
        "path": "/v1/customers/cust_4821",
        "params": {},
        "status": 401,
        "response": {"detail": "Unauthorized"},
    }
]

TASK1_WRONG_ENDPOINT_LOG = [
    {
        "method": "GET",
        "path": "/v1/invoices",
        "params": {},
        "status": 200,
        "response": {},
    }
]


def test_task1_perfect_score():
    score = task1_grader.grade(TASK1_PERFECT_LOG, TASK1_GT)
    assert score >= 0.9, f"Perfect call should score >= 0.9, got {score}"


def test_task1_auth_fail():
    score = task1_grader.grade(TASK1_AUTH_FAIL_LOG, TASK1_GT)
    assert 0.0 < score < 0.6, f"Auth fail should give partial credit, got {score}"


def test_task1_wrong_endpoint():
    score = task1_grader.grade(TASK1_WRONG_ENDPOINT_LOG, TASK1_GT)
    assert score == 0.0, f"Wrong endpoint should score 0, got {score}"


def test_task1_empty_log():
    score = task1_grader.grade([], TASK1_GT)
    assert score == 0.0


def test_task1_is_deterministic():
    """Same call_log must always produce same score."""
    scores = [task1_grader.grade(TASK1_PERFECT_LOG, TASK1_GT) for _ in range(10)]
    assert len(set(scores)) == 1, (
        f"Non-deterministic! Got different scores: {set(scores)}"
    )


# ─── Task 3 test data ─────────────────────────────────────────────────────────

TASK3_GT = {
    "target_path": "/payments",
    "bugs": [
        {"id": "bug_auth", "error_code": 401, "weight": 0.30},
        {"id": "bug_method", "error_code": 405, "weight": 0.30},
        {"id": "bug_currency", "error_code": 422, "weight": 0.40},
    ],
}


def test_task3_no_bugs_fixed():
    log = [{"path": "/payments", "status": 401, "response": {}}]
    score = task3_grader.grade(log, TASK3_GT)
    assert score == 0.0, f"No bugs fixed = 0.0, got {score}"


def test_task3_one_bug_fixed():
    # Agent fixed auth (got past 401 to 405)
    log = [
        {"path": "/payments", "status": 401, "response": {}},
        {"path": "/payments", "status": 405, "response": {}},
    ]
    score = task3_grader.grade(log, TASK3_GT)
    assert 0.25 <= score <= 0.35, f"One bug fixed = ~0.30, got {score}"


def test_task3_all_bugs_fixed():
    # Agent achieved 200 = all bugs fixed
    log = [
        {"path": "/payments", "status": 401, "response": {}},
        {"path": "/payments", "status": 405, "response": {}},
        {"path": "/payments", "status": 422, "response": {}},
        {"path": "/payments", "status": 200, "response": {"payment_id": "pay_abc"}},
    ]
    score = task3_grader.grade(log, TASK3_GT)
    assert score >= 0.99, f"All bugs fixed = 1.0, got {score}"


def test_task3_is_deterministic():
    log = [{"path": "/payments", "status": 200, "response": {}}]
    scores = [task3_grader.grade(log, TASK3_GT) for _ in range(10)]
    assert len(set(scores)) == 1, f"Non-deterministic! {set(scores)}"

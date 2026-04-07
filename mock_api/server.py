import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Header, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any

from mock_api.call_logger import CallLogger

app = FastAPI(title="AgentAPIBench Mock API", version="1.0.0")
logger = CallLogger()
DATA_DIR = Path(__file__).parent / "data"

# Load fake data
CUSTOMERS = json.loads((DATA_DIR / "customers.json").read_text())
INVOICES = json.loads((DATA_DIR / "invoices.json").read_text())
PAYMENTS = json.loads((DATA_DIR / "payments.json").read_text())

VALID_TOKENS = {
    "sk-bench-4921x": "test_account_1",
    "sk-bench-7823y": "test_account_2",
    "sk-bench-1155z": "test_account_3",
}


def verify_auth(authorization: Optional[str]) -> str:
    """Returns account_id or raises 401."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required. Use: Authorization: Bearer <token>",
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=f"Authorization header must use Bearer scheme. Got: {authorization}",
        )
    token = authorization.replace("Bearer ", "").strip()
    if token not in VALID_TOKENS:
        raise HTTPException(
            status_code=401, detail=f"Invalid token. Check your API credentials."
        )
    return VALID_TOKENS[token]


def log_call(method: str, path: str, params: dict, status: int, response: dict):
    logger.log(
        {
            "method": method,
            "path": path,
            "params": params,
            "status": status,
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Catch-all middleware to log 422s that fail FastAPI validation before reaching routes
@app.middleware("http")
async def log_failed_requests(request: Request, call_next):
    # Safe clone of query params
    params = dict(request.query_params)
    response = await call_next(request)

    if response.status_code >= 400 and not request.url.path.startswith("/v1/_internal"):
        # The route handler didn't get to log it because of an exception, log it now
        # We can't easily read the body here without consuming the stream, but we can log the 4xx
        log_call(
            request.method,
            request.url.path,
            params,
            response.status_code,
            {"error": "Request failed HTTP validation"},
        )

    return response


# ─── CUSTOMERS ───────────────────────────────────────────────────────────────


@app.get("/v1/customers/{customer_id}")
def get_customer(
    customer_id: str,
    include: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    verify_auth(authorization)
    customer = next((c for c in CUSTOMERS if c["id"] == customer_id), None)
    if not customer:
        log_call("GET", f"/v1/customers/{customer_id}", {}, 404, {})
        raise HTTPException(
            status_code=404, detail=f"Customer '{customer_id}' not found."
        )

    result = {
        "id": customer["id"],
        "name": customer["name"],
        "email": customer["email"],
        "created_at": customer["created_at"],
    }

    if include:
        fields = [f.strip() for f in include.split(",")]
        if "subscription" in fields:
            result["subscription"] = customer.get("subscription", {})
        if "billing" in fields:
            result["billing"] = customer.get("billing", {})

    log_call("GET", f"/v1/customers/{customer_id}", {"include": include}, 200, result)
    return result


@app.get("/v1/customers")
def list_customers(
    status: Optional[str] = None,
    limit: int = 20,
    authorization: Optional[str] = Header(None),
):
    verify_auth(authorization)
    results = CUSTOMERS
    if status:
        results = [c for c in results if c.get("status") == status]
    result = {"customers": results[:limit], "total": len(results)}
    log_call("GET", "/v1/customers", {"status": status, "limit": limit}, 200, result)
    return result


# ─── INVOICES ────────────────────────────────────────────────────────────────


@app.get("/v1/invoices")
def list_invoices(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    verify_auth(authorization)
    results = INVOICES
    if customer_id:
        results = [i for i in results if i["customer_id"] == customer_id]
    if status:
        results = [i for i in results if i["status"] == status]
    result = {"invoices": results, "total": len(results)}
    log_call(
        "GET",
        "/v1/invoices",
        {"customer_id": customer_id, "status": status},
        200,
        result,
    )
    return result


class RemindBody(BaseModel):
    channel: str  # "email" | "sms" | "push"


@app.post("/v1/invoices/{invoice_id}/remind")
def send_reminder(
    invoice_id: str, body: RemindBody, authorization: Optional[str] = Header(None)
):
    verify_auth(authorization)
    invoice = next((i for i in INVOICES if i["id"] == invoice_id), None)
    if not invoice:
        log_call(
            "POST",
            f"/v1/invoices/{invoice_id}/remind",
            {"channel": body.channel},
            404,
            {},
        )
        raise HTTPException(
            status_code=404, detail=f"Invoice '{invoice_id}' not found."
        )
    if body.channel not in ["email", "sms", "push"]:
        log_call(
            "POST",
            f"/v1/invoices/{invoice_id}/remind",
            {"channel": body.channel},
            422,
            {},
        )
        raise HTTPException(
            status_code=422,
            detail=f"Invalid channel '{body.channel}'. Must be: email, sms, or push.",
        )
    result = {
        "reminder_id": f"rem_{uuid.uuid4().hex[:8]}",
        "invoice_id": invoice_id,
        "channel": body.channel,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent",
    }
    log_call(
        "POST",
        f"/v1/invoices/{invoice_id}/remind",
        {"channel": body.channel},
        200,
        result,
    )
    return result


# ─── PAYMENTS ────────────────────────────────────────────────────────────────


class PaymentBody(BaseModel):
    customer_id: str
    amount: float
    currency: str  # Required — ISO 4217 (USD, EUR, GBP...)


@app.post("/v1/payments")
def create_payment(body: PaymentBody, authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    if body.amount <= 0:
        log_call("POST", "/v1/payments", body.dict(), 422, {})
        raise HTTPException(status_code=422, detail="Amount must be greater than 0.")
    if len(body.currency) != 3:
        log_call("POST", "/v1/payments", body.dict(), 422, {})
        raise HTTPException(
            status_code=422,
            detail=f"Currency must be a 3-letter ISO 4217 code (USD, EUR, GBP). Got: {body.currency}",
        )
    result = {
        "payment_id": f"pay_{uuid.uuid4().hex[:8]}",
        "customer_id": body.customer_id,
        "amount": body.amount,
        "currency": body.currency,
        "status": "succeeded",
        "created_at": datetime.utcnow().isoformat(),
    }
    log_call("POST", "/v1/payments", body.dict(), 200, result)
    return result


# ─── CALL LOG ACCESS (for graders) ───────────────────────────────────────────


@app.get("/v1/_internal/call_log")
def get_call_log(authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    return {"calls": logger.get_calls()}


@app.delete("/v1/_internal/call_log")
def clear_call_log(authorization: Optional[str] = Header(None)):
    verify_auth(authorization)
    logger.clear()
    return {"message": "Call log cleared"}

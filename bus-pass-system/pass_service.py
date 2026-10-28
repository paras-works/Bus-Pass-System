import secrets
from datetime import date

import models


# ---------------------------------------------------------------
# STUDENT: apply for a pass
# ---------------------------------------------------------------
def apply_for_pass(db, user_id, route_id, start_date_str, plan, pass_type):
    if not (route_id and start_date_str and plan and pass_type):
        return False, "Please fill all fields", None

    # Flask hands us whatever JSON the browser sent, so make sure each
    # value is the type we expect before using it.
    if not isinstance(route_id, int) or isinstance(route_id, bool):
        return False, "Selected route is not available", None
    if not all(isinstance(v, str) for v in (start_date_str, plan, pass_type)):
        return False, "Please fill all fields", None
    if len(pass_type) > 50:
        return False, "Invalid pass type", None

    route = models.Route.find_by_id(db, route_id)
    if not route or not route["active"]:
        return False, "Selected route is not available", None

    if plan not in models.PassRequest.PLAN_MONTHS:
        return False, "Invalid plan selected", None

    try:
        start_date = date.fromisoformat(start_date_str)
    except ValueError:
        return False, "Invalid start date", None

    request_id, end_date = models.PassRequest.create(
        db, user_id, route_id, start_date, plan, pass_type
    )
    return True, "Pass request submitted. Waiting for admin approval.", {
        "request_id": request_id,
        "end_date": end_date.isoformat(),
    }


# ---------------------------------------------------------------
# ADMIN: approve / reject / delete a request
# ---------------------------------------------------------------
def approve_request(db, request_id):
    request_row = models.PassRequest.find_by_id(db, request_id)
    if not request_row:
        return False, "Request not found"
    if request_row["status"] != "pending":
        return False, "Only a pending request can be approved"

    models.PassRequest.update_status(db, request_id, "approved")
    return True, "Request approved"


def reject_request(db, request_id):
    request_row = models.PassRequest.find_by_id(db, request_id)
    if not request_row:
        return False, "Request not found"
    if request_row["status"] != "pending":
        return False, "Only a pending request can be rejected"

    models.PassRequest.update_status(db, request_id, "rejected")
    return True, "Request rejected"


def delete_request(db, request_id):
    request_row = models.PassRequest.find_by_id(db, request_id)
    if not request_row:
        return False, "Request not found"

    models.PassRequest.delete(db, request_id)
    return True, "Request deleted"


# ---------------------------------------------------------------
# STUDENT: simulated payment  ->  bus pass generation
# ---------------------------------------------------------------
# Fixed price list. Kept on the backend so the browser cannot send
# a fake, lower amount.
PLAN_PRICES = {
    "1 Month": 500,
    "3 Months": 1400,
    "6 Months": 2500,
    "1 Year": 4500,
}


def pay_for_request(db, user_id, request_id, payment_method):
    if not payment_method or len(payment_method) > 30:
        return False, "Select a valid payment method", None
    if not isinstance(request_id, int) or isinstance(request_id, bool):
        return False, "Pass request not found", None

    request_row = models.PassRequest.find_by_id(db, request_id)

    if not request_row or request_row["user_id"] != user_id:
        return False, "Pass request not found", None

    if request_row["status"] != "approved":
        return False, "Only an approved request can be paid for", None

    if models.Payment.exists_for_request(db, request_id):
        return False, "This request has already been paid for", None

    amount = PLAN_PRICES.get(request_row["plan"])
    if amount is None:
        return False, "Invalid plan on this request", None

    # "Payment simulation for academic/portfolio purposes; no real
    # money is processed." A random transaction id stands in for
    # whatever a real payment gateway would normally return.
    transaction_id = "TXN" + secrets.token_hex(6).upper()

    models.Payment.create(db, request_id, user_id, amount, payment_method, transaction_id)
    models.PassRequest.update_status(db, request_id, "paid")

    pass_number = models.BusPass.create(
        db, request_id, user_id, request_row["start_date"], request_row["end_date"]
    )

    return True, "Payment successful", {
        "transaction_id": transaction_id,
        "amount": amount,
        "pass_number": pass_number,
    }

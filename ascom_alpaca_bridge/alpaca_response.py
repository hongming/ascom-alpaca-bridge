from __future__ import annotations

from itertools import count
from threading import Lock
from typing import Any

from fastapi import Request


_server_transaction_ids = count(1)
_transaction_lock = Lock()


def next_server_transaction_id() -> int:
    with _transaction_lock:
        return next(_server_transaction_ids)


def parse_client_transaction_id(request: Request) -> int:
    value = request.query_params.get("ClientTransactionID")
    if value is None:
        value = request.query_params.get("clienttransactionid")
    if value is None:
        form = getattr(request, "_form", None)
        if form is not None:
            value = form.get("ClientTransactionID")
            if value is None:
                value = form.get("clienttransactionid")
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def value_response(value: Any, request: Request) -> dict[str, Any]:
    return {
        "Value": value,
        "ClientTransactionID": parse_client_transaction_id(request),
        "ServerTransactionID": next_server_transaction_id(),
        "ErrorNumber": 0,
        "ErrorMessage": "",
    }


def empty_response(request: Request) -> dict[str, Any]:
    return {
        "ClientTransactionID": parse_client_transaction_id(request),
        "ServerTransactionID": next_server_transaction_id(),
        "ErrorNumber": 0,
        "ErrorMessage": "",
    }


def error_response(error_number: int, message: str, request: Request) -> dict[str, Any]:
    return {
        "ClientTransactionID": parse_client_transaction_id(request),
        "ServerTransactionID": next_server_transaction_id(),
        "ErrorNumber": error_number,
        "ErrorMessage": message,
    }

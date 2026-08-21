from __future__ import annotations

import logging
import sys
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
        stream=sys.stdout,
    )
    logging.setLogRecordFactory(_record_factory(logging.getLogRecordFactory()))


def _record_factory(factory):
    def make_record(*args, **kwargs):
        record = factory(*args, **kwargs)
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return record

    return make_record


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

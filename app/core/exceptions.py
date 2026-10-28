from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str = "", *, code: str | None = None, status_code: int | None = None, extra: dict | None = None):
        super().__init__(message or self.code)
        self.message = message or self.code
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.extra = extra or {}


class NotFound(AppError):
    status_code, code = 404, "not_found"


class Conflict(AppError):
    status_code, code = 409, "conflict"


class Unauthorized(AppError):
    status_code, code = 401, "unauthorized"


class Forbidden(AppError):
    status_code, code = 403, "forbidden"


class TooManyRequests(AppError):
    status_code, code = 429, "too_many_requests"


class PaymentError(AppError):
    status_code, code = 402, "payment_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code, **exc.extra},
        )


    from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, TimeoutError as SATimeout

    def _unavailable():
        return JSONResponse(status_code=503, headers={"Retry-After": "5"},
                            content={"detail": "Our service is temporarily unavailable. Please try again in a moment.", "code": "service_unavailable"})

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    @app.exception_handler(SATimeout)
    @app.exception_handler(ConnectionError)
    @app.exception_handler(TimeoutError)
    async def _db_down(request: Request, exc: Exception):
        import logging
        logging.getLogger("app").warning("Database/network unavailable on %s %s: %s", request.method, request.url.path, type(exc).__name__)
        return _unavailable()

    @app.exception_handler(DBAPIError)
    async def _dbapi(request: Request, exc: DBAPIError):
        import logging
        if exc.connection_invalidated or isinstance(exc.orig, (ConnectionError, OSError)):
            logging.getLogger("app").warning("Database connection lost on %s %s", request.method, request.url.path)
            return _unavailable()
        logging.getLogger("app").exception("Database error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again.", "code": "server_error"})

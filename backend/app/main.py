from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.deps import CSRF_HEADER, SESSION_MODE_HEADER, SessionDep
from app.routers import accounts, admin, assistant, auth, customers, transfers

app = FastAPI(title="AB Bank API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    # Needed for the web session cookie; safe because origins are an explicit allow-list.
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", CSRF_HEADER, SESSION_MODE_HEADER],
)

app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(assistant.router)
app.include_router(admin.router)


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Give clients one Turkish message in `detail`, like every other error; keep the field list."""
    errors = exc.errors()
    message = "Gönderilen bilgiler geçersiz."
    for error in errors:
        # Our own validators raise ValueError with a Turkish message; pydantic's are English.
        if error.get("type") == "value_error":
            message = str(error.get("ctx", {}).get("error", message))
            break
    fields = [{"loc": list(e["loc"]), "type": e["type"]} for e in errors]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": message, "errors": fields},
    )


@app.get("/health", tags=["system"])
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}

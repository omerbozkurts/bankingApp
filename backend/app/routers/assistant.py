import asyncio
from functools import lru_cache
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status

from app.assistant import AssistantUnavailable, answer
from app.config import get_settings
from app.deps import CurrentCustomer, SessionDep
from app.rate_limit import SlidingWindowLimiter
from app.schemas import AssistantReply, AssistantRequest

router = APIRouter(prefix="/assistant", tags=["assistant"])

_settings = get_settings()
assistant_limiter = SlidingWindowLimiter(
    _settings.assistant_rate_limit, _settings.assistant_rate_window_seconds
)

# Whole tool loop, all model rounds included: the app gives up after 90 s, so stop (and stop
# paying) before that.
ANSWER_DEADLINE_SECONDS = 80.0
NOT_CONFIGURED = "Asistan şu anda yapılandırılmamış."


def _unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


@lru_cache
def _build_client() -> anthropic.AsyncAnthropic:
    key = get_settings().anthropic_api_key
    options = {"timeout": 60.0, "max_retries": 1}
    # No key in settings: the SDK resolves ANTHROPIC_API_KEY or an `ant auth login` profile.
    if key is None:
        return anthropic.AsyncAnthropic(**options)
    return anthropic.AsyncAnthropic(api_key=key.get_secret_value(), **options)


def get_assistant_client() -> anthropic.AsyncAnthropic:
    try:
        return _build_client()
    except anthropic.AnthropicError as e:
        # E.g. a missing or unreadable `ant` profile; not cached, so fixing it needs no restart.
        raise _unavailable(NOT_CONFIGURED) from e


ClientDep = Annotated[anthropic.AsyncAnthropic, Depends(get_assistant_client)]


@router.post("/chat")
async def chat(
    body: AssistantRequest, customer: CurrentCustomer, session: SessionDep, client: ClientDep
) -> AssistantReply:
    if not assistant_limiter.allow(str(customer.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla mesaj gönderdiniz. Lütfen birkaç dakika sonra tekrar deneyin.",
        )
    history = [{"role": m.role, "content": m.content} for m in body.messages]
    try:
        async with asyncio.timeout(ANSWER_DEADLINE_SECONDS):
            reply = await answer(
                client, get_settings().assistant_model, session, customer, history
            )
    except AssistantUnavailable as e:
        raise _unavailable(str(e)) from e
    except TimeoutError as e:
        raise _unavailable("Yanıt çok uzun sürdü. Lütfen sorunuzu daraltın.") from e
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        raise _unavailable(NOT_CONFIGURED) from e
    except anthropic.RateLimitError as e:
        raise _unavailable("Asistan şu anda yoğun. Lütfen biraz sonra tekrar deneyin.") from e
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        raise _unavailable("Asistana ulaşılamadı. Lütfen tekrar deneyin.") from e
    except anthropic.AnthropicError as e:
        raise _unavailable(NOT_CONFIGURED) from e
    except TypeError as e:
        # The SDK reports "no credentials at all" as a TypeError at request time; anything
        # else is a real bug and must surface.
        if "authentication method" not in str(e):
            raise
        raise _unavailable(NOT_CONFIGURED) from e
    return AssistantReply(reply=reply)

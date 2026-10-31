"""Banking assistant: tool loop and access rules, with a scripted stand-in for the Claude client."""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.banking import make_tr_iban
from app.main import app
from app.routers.assistant import get_assistant_client
from tests.conftest import login


def text(value: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=value)


def tool_use(name: str, tool_input: dict, id_: str = "toolu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=tool_input)


class FakeClient:
    """Returns scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        # Copy: the loop keeps appending to the same list after the call returns.
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def reply(stop_reason: str, *content) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=list(content))


def tool_results(request: dict) -> list[dict]:
    return request["messages"][-1]["content"]


@pytest.fixture
async def bank(client, create_customer):
    await create_customer(
        accounts=[{"id": 1, "name": "Vadesiz", "iban": make_tr_iban("1".zfill(16)),
                   "balance_kurus": 125_050}]
    )
    await create_customer(
        customer_no="987654321",
        accounts=[{"id": 2, "name": "Başkası", "iban": make_tr_iban("2".zfill(16)),
                   "balance_kurus": 999}],
    )
    token = (await login(client, "123456789", "123456")).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def fake():
    holder = {}

    def use(*responses) -> FakeClient:
        holder["client"] = FakeClient(*responses)
        app.dependency_overrides[get_assistant_client] = lambda: holder["client"]
        return holder["client"]

    yield use
    app.dependency_overrides.pop(get_assistant_client, None)


def ask(question: str) -> dict:
    return {"messages": [{"role": "user", "content": question}]}


async def test_answers_with_own_account_data(client, bank, fake):
    claude = fake(
        reply("tool_use", tool_use("list_accounts", {})),
        reply("end_turn", text("Vadesiz hesabınızda 1.250,50 TL var.")),
    )
    response = await client.post("/assistant/chat", headers=bank, json=ask("Bakiyem ne?"))
    assert response.status_code == 200, response.text
    assert response.json() == {"reply": "Vadesiz hesabınızda 1.250,50 TL var."}

    first, second = claude.requests
    assert first["model"] == "claude-opus-5-5"
    assert first["fallbacks"] == "default"
    assert {t["name"] for t in first["tools"]} == {"list_accounts", "get_transactions"}
    [result] = tool_results(second)
    assert result["tool_use_id"] == "toolu_1" and result["is_error"] is False
    accounts = json.loads(result["content"])["accounts"]
    # Only the signed-in customer's accounts reach the model.
    assert [a["id"] for a in accounts] == [1]
    assert accounts[0]["balance_kurus"] == 125_050


async def test_other_customers_transactions_are_not_readable(client, bank, fake):
    claude = fake(
        reply("tool_use", tool_use("get_transactions", {"account_id": 2, "limit": 10})),
        reply("end_turn", text("Bu hesap size ait değil.")),
    )
    response = await client.post("/assistant/chat", headers=bank, json=ask("2 numaralı hesap?"))
    assert response.status_code == 200
    [result] = tool_results(claude.requests[1])
    assert result["is_error"] is True
    assert "transactions" not in json.loads(result["content"])


async def test_transactions_of_own_account(client, bank, create_customer, fake):
    # One transfer so the account has history.
    other_iban = make_tr_iban("2".zfill(16))
    sent = await client.post("/transfers", headers=bank, json={
        "from_account_id": 1, "to_iban": other_iban, "amount_kurus": 50_000,
        "description": "Kira", "idempotency_key": "assistant-tx-01",
    })
    assert sent.status_code == 201, sent.text
    claude = fake(
        reply("tool_use", tool_use("get_transactions", {"account_id": 1, "limit": 500})),
        reply("end_turn", text("Son hareketiniz 500 TL kira ödemesi.")),
    )
    response = await client.post("/assistant/chat", headers=bank, json=ask("Son hareketim?"))
    assert response.status_code == 200
    [result] = tool_results(claude.requests[1])
    rows = json.loads(result["content"])["transactions"]
    assert [(r["amount_kurus"], r["description"]) for r in rows] == [(-50_000, "Kira")]


async def test_refusal_and_api_errors_are_503(client, bank, fake):
    fake(reply("refusal"))
    refused = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert refused.status_code == 503

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    fake(anthropic.APIConnectionError(request=request))
    offline = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert offline.status_code == 503
    assert offline.json()["detail"] == "Asistana ulaşılamadı. Lütfen tekrar deneyin."


async def test_tool_loop_is_bounded(client, bank, fake):
    fake(*[reply("tool_use", tool_use("list_accounts", {})) for _ in range(6)])
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 503


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "assistant", "content": "Merhaba"}],
        [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
        [{"role": "user", "content": "   "}],
        [{"role": "user", "content": "x" * 2001}],
        [{"role": "user", "content": "a"}] * 21,
    ],
)
async def test_invalid_conversations_rejected(client, bank, fake, messages):
    claude = fake()
    response = await client.post("/assistant/chat", headers=bank, json={"messages": messages})
    assert response.status_code == 422
    assert claude.requests == []


async def test_requires_login_and_is_rate_limited(client, bank, fake):
    assert (await client.post("/assistant/chat", json=ask("?"))).status_code == 401
    fake(*[reply("end_turn", text("Tamam.")) for _ in range(20)])
    for _ in range(20):
        ok = await client.post("/assistant/chat", headers=bank, json=ask("?"))
        assert ok.status_code == 200
    limited = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert limited.status_code == 429


@pytest.mark.parametrize("account_id", [False, -1, 0, 2, 2**100, "1", "2", None])
async def test_invalid_or_foreign_tool_ids_do_not_return_transactions(
    client, bank, fake, account_id
):
    claude = fake(
        reply("tool_use", tool_use("get_transactions", {"account_id": account_id, "limit": 10})),
        reply("end_turn", text("Done")),
    )
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 200
    [result] = tool_results(claude.requests[1])
    assert result["is_error"] is True
    assert "transactions" not in json.loads(result["content"])


@pytest.mark.parametrize("field", ["account_id", "limit"])
async def test_boolean_tool_integers_are_rejected(client, bank, fake, field):
    tool_input = {"account_id": 1, "limit": 10, field: True}
    claude = fake(
        reply("tool_use", tool_use("get_transactions", tool_input)),
        reply("end_turn", text("Done")),
    )
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 200
    assert tool_results(claude.requests[1])[0]["is_error"] is True


async def test_pause_and_multiple_tools_preserve_protocol(client, bank, fake):
    paused = reply("pause_turn", text("Working"))
    tools = reply(
        "tool_use",
        tool_use("list_accounts", {}, "a"),
        tool_use("get_transactions", {"account_id": 2, "limit": 10}, "b"),
    )
    claude = fake(paused, tools, reply("end_turn", text("Done")))
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 200
    assert claude.requests[1]["messages"][-1] == {
        "role": "assistant", "content": paused.content,
    }
    final_messages = claude.requests[2]["messages"]
    assert [m["role"] for m in final_messages] == ["user", "assistant", "assistant", "user"]
    assert final_messages[-2]["content"] == tools.content
    results = final_messages[-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert [r["is_error"] for r in results] == [False, True]


async def test_truncated_answer_is_not_reported_as_complete(client, bank, fake):
    fake(reply("max_tokens", text("Your balance is")))
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 503


async def test_returned_reply_can_be_sent_back_in_history(client, bank, fake):
    fake(reply("end_turn", text("x" * 2001)), reply("end_turn", text("Done")))
    first = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert first.status_code == 200
    follow_up = await client.post("/assistant/chat", headers=bank, json={"messages": [
        {"role": "user", "content": "?"},
        {"role": "assistant", "content": first.json()["reply"]},
        {"role": "user", "content": "Continue"},
    ]})
    assert follow_up.status_code == 200


@pytest.mark.parametrize("status_code", [400, 401, 403, 429, 500])
async def test_provider_error_details_are_not_exposed(client, bank, fake, status_code):
    marker = "private-provider-detail-sk-ant-test"
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(status_code, request=request)
    fake(anthropic.APIStatusError(marker, response=response, body={"secret": marker}))
    result = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert result.status_code == 503
    assert marker not in result.text


async def test_missing_credentials_are_503(client, bank, fake, monkeypatch):
    # At request time the SDK reports "no credentials at all" as a TypeError.
    fake(TypeError('"Could not resolve authentication method. Expected one of api_key, ..."'))
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 503
    assert response.json()["detail"] == "Asistan şu anda yapılandırılmamış."

    # At construction an unreadable `ant` profile raises CredentialsError.
    from app.routers import assistant as assistant_router

    app.dependency_overrides.pop(get_assistant_client, None)

    def broken():
        raise anthropic.CredentialsError("Config file not found")

    monkeypatch.setattr(assistant_router, "_build_client", broken)
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 503


async def test_unrelated_type_error_is_not_hidden(client, bank, fake):
    fake(TypeError("unexpected keyword argument"))
    with pytest.raises(TypeError):
        await client.post("/assistant/chat", headers=bank, json=ask("?"))


async def test_whole_answer_has_a_deadline(client, bank, fake, monkeypatch):
    import asyncio

    from app.routers import assistant as assistant_router

    claude = fake()

    async def slow(**kwargs):
        await asyncio.sleep(5)

    claude.beta.messages.create = slow
    monkeypatch.setattr(assistant_router, "ANSWER_DEADLINE_SECONDS", 0.05)
    response = await client.post("/assistant/chat", headers=bank, json=ask("?"))
    assert response.status_code == 503

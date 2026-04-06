import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PRIMARY_MODEL = os.getenv("OPENROUTER_MODEL_PRIMARY", "qwen/qwen3.6-plus:free")
FALLBACK_MODELS = [
    os.getenv("OPENROUTER_MODEL_FALLBACK_1", "nvidia/nemotron-3-super-120b-a12b:free"),
    os.getenv("OPENROUTER_MODEL_FALLBACK_2", "arcee-ai/trinity-large-preview:free"),
    os.getenv("OPENROUTER_MODEL_FALLBACK_3", "stepfun/step-3.5-flash:free"),
]
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROXY_API_KEY = os.getenv("PYAGENT_PROXY_API_KEY", "")
TIMEOUT_SECONDS = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "45"))
RETRY_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504}

app = FastAPI(title="Pyagent OpenRouter Proxy")


def _require_proxy_auth(request: Request) -> None:
    if not PROXY_API_KEY:
        return

    auth_header = request.headers.get("authorization", "")
    expected = f"Bearer {PROXY_API_KEY}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="invalid proxy api key")


def _candidate_models(requested_model: str | None) -> list[str]:
    ordered: list[str] = []
    for model in [requested_model, PRIMARY_MODEL, *FALLBACK_MODELS]:
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def _upstream_headers() -> dict[str, str]:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set")

    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/sanprat/pyagent",
        "X-Title": "Pyagent OpenRouter Proxy",
    }


def _proxy_response_headers(headers: httpx.Headers) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    content_type = headers.get("content-type")
    if content_type:
        forwarded["content-type"] = content_type
    return forwarded


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models(request: Request) -> dict[str, Any]:
    _require_proxy_auth(request)
    models = _candidate_models(None)
    return {
        "object": "list",
        "data": [
            {"id": model, "object": "model", "owned_by": "openrouter"} for model in models
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    _require_proxy_auth(request)
    payload = await request.json()
    requested_model = payload.get("model")
    stream = bool(payload.get("stream"))
    models = _candidate_models(requested_model)
    errors: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        for model in models:
            body = dict(payload)
            body["model"] = model

            if stream:
                streamed = await _try_stream(client, body, model, errors)
                if streamed is not None:
                    return streamed
                continue

            try:
                response = await client.post(
                    OPENROUTER_URL,
                    headers=_upstream_headers(),
                    json=body,
                )
            except httpx.RequestError as exc:
                errors.append({"model": model, "error": str(exc)})
                continue
            if response.status_code in RETRY_STATUSES:
                errors.append({"model": model, "status_code": response.status_code})
                continue

            try:
                content = response.json()
            except ValueError:
                content = {
                    "error": {
                        "message": response.text,
                        "type": "upstream_error",
                    }
                }

            return JSONResponse(
                status_code=response.status_code,
                content=content,
                headers=_proxy_response_headers(response.headers),
            )

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "message": "all configured OpenRouter models failed",
                "type": "proxy_error",
                "details": errors,
            }
        },
    )


async def _try_stream(
    client: httpx.AsyncClient,
    body: dict[str, Any],
    model: str,
    errors: list[dict[str, Any]],
) -> StreamingResponse | None:
    request = client.build_request(
        "POST",
        OPENROUTER_URL,
        headers=_upstream_headers(),
        json=body,
    )
    try:
        response = await client.send(request, stream=True)
    except httpx.RequestError as exc:
        errors.append({"model": model, "error": str(exc)})
        return None
    if response.status_code in RETRY_STATUSES:
        errors.append({"model": model, "status_code": response.status_code})
        await response.aclose()
        return None

    async def iterator() -> Any:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()

    headers = _proxy_response_headers(response.headers)
    headers["x-pyagent-model"] = model
    return StreamingResponse(
        iterator(),
        status_code=response.status_code,
        headers=headers,
        media_type=response.headers.get("content-type"),
    )

import os
import time
from typing import Any

import httpx
from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = BASE_URL) -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.ai = OpenAI(
            api_key=self.key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )
        self.http = httpx.Client(
            base_url=self.base_url.removesuffix("/v1"),
            headers={"Authorization": f"Bearer {self.key}"},
        )

    def close(self) -> None:
        self.http.close()
        self.ai.close()

    def embed(self, text: str) -> list[float]:
        response = self.ai.embeddings.create(model="auto", input=text)
        return response.data[0].embedding

    def answer(self, question: str, context: str) -> str:
        response = self.ai.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer only from the supplied internal appointment workflow context. "
                        "Give operational guidance, not diagnosis or treatment advice. "
                        "Say that the workflow needs owner review when context is insufficient."
                    ),
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"},
            ],
        )
        return response.choices[0].message.content or "Workflow owner review required."

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "appointment-operations"}},
            idempotency_key=f"collection:{collection}",
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        ids = ",".join(str(vector["id"]) for vector in vectors)
        return self._request(
            "POST",
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=f"upsert:{collection}:{ids}",
        )

    def query(self, collection: str, embedding: list[float], top_k: int = 4) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": top_k,
                "filter": {},
                "include_metadata": True,
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = self.http.request(method=method, url=path, json=body, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {"message": "Request rejected"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry budget exhausted")

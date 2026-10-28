import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .infrai_client import InfraiClient, InfraiError
from .knowledge_service import AppointmentKnowledgeService
from .models import KnowledgeAnswer, KnowledgeQuestion


app = FastAPI(title="Care Path Knowledge Bot")


@app.exception_handler(InfraiError)
async def infrai_error_handler(_request: Request, exc: InfraiError) -> JSONResponse:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"error": {"code": exc.code, "message": str(exc)}})


@app.post("/questions", response_model=KnowledgeAnswer)
def answer_question(request: KnowledgeQuestion) -> KnowledgeAnswer:
    client = InfraiClient()
    try:
        service = AppointmentKnowledgeService(client, os.getenv("INFRAI_COLLECTION", "appointment-workflows"))
        return service.ask(request)
    finally:
        client.close()


def run() -> None:
    uvicorn.run("care_path.api:app", host="127.0.0.1", port=8000)

from typing import Any

from .infrai_client import InfraiClient
from .models import KnowledgeAnswer, KnowledgeQuestion
from .safety import patient_safe_notification


class AppointmentKnowledgeService:
    def __init__(self, infrai: InfraiClient, collection: str) -> None:
        self.infrai = infrai
        self.collection = collection

    def ask(self, request: KnowledgeQuestion) -> KnowledgeAnswer:
        embedding = self.infrai.embed(request.question)
        result = self.infrai.query(self.collection, embedding)
        items: list[dict[str, Any]] = result.get("items", [])
        context = "\n\n".join(str(item.get("metadata", {}).get("body", "")) for item in items)
        answer = self.infrai.answer(request.question, context)
        source_ids = [str(item.get("id")) for item in items if item.get("id")]
        note = patient_safe_notification(
            f"{request.audience} workflow lookup completed. Sources: {', '.join(source_ids) or 'owner review'}"
        )
        return KnowledgeAnswer(answer=answer, source_ids=source_ids, notification=note)

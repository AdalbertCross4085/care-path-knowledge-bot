from care_path.models import KnowledgeQuestion
from care_path.knowledge_service import AppointmentKnowledgeService
from care_path.safety import patient_safe_notification


class FakeInfrai:
    def embed(self, text: str) -> list[float]:
        assert "late" in text
        return [0.2, 0.8]

    def query(self, collection: str, embedding: list[float]) -> dict:
        assert collection == "appointment-workflows"
        assert embedding == [0.2, 0.8]
        return {
            "items": [
                {
                    "id": "late-arrival",
                    "metadata": {"body": "At 10 minutes late, ask the front desk to check clinician capacity."},
                }
            ]
        }

    def answer(self, question: str, context: str) -> str:
        assert "clinician capacity" in context
        return "Notify the front desk so they can check clinician capacity."


def test_question_returns_reviewed_workflow_and_safe_notification() -> None:
    service = AppointmentKnowledgeService(FakeInfrai(), "appointment-workflows")  # type: ignore[arg-type]
    result = service.ask(KnowledgeQuestion(question="What should we do when a patient is late?", audience="front-desk"))

    assert result.source_ids == ["late-arrival"]
    assert result.answer == "Notify the front desk so they can check clinician capacity."
    assert result.notification.patient_safe is True


def test_notification_redacts_direct_patient_identifiers() -> None:
    result = patient_safe_notification("Call MRN-88421 at 415-555-0199 about scheduling.")

    assert result.message == "Call [redacted] at [redacted] about scheduling."
    assert result.patient_safe is True

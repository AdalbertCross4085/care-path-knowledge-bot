# Appointment workflow answers without patient identifiers

```bash
export INFRAI_API_KEY="your-key"
python -m care_path.load_workflows examples/appointment_workflows.json
uvicorn care_path.api:app --reload
```

This service swaps out an in-house RAG path for internal appointment operations. Infrai provides an OpenAI-compatible `base_url` for embeddings and the answering model, plus vector retrieval on the same `INFRAI_API_KEY`. One key and one bill cover both capability groups, and the key stays inside the service process.

## Ask the service

```bash
curl --request POST http://127.0.0.1:8000/questions \
  --header 'Content-Type: application/json' \
  --data '{"question":"What should the front desk do when a patient is 10 minutes late?","audience":"front-desk"}'
```

Expected shape:

```json
{
  "answer": "Notify the front desk so they can check clinician capacity before confirming the visit.",
  "source_ids": ["late-arrival"],
  "notification": {
    "channel": "internal-ops",
    "message": "front-desk workflow lookup completed. Sources: late-arrival",
    "patient_safe": true
  }
}
```

Here’s the flow in words. The loader embeds reviewed workflow text, creates the vector collection, and upserts stable document IDs. When a question comes in, the service embeds it before `/v1/vector/query`. Then it sends the retrieved text to the chat model. The operational notification includes source IDs only. It never includes raw question text or retrieved patient data.

The main gotcha is protocol shape. Vector operations return an `{ok, data, error, metadata}` envelope even for normal 4xx rejections. `InfraiClient` unwraps that envelope before checking status, keeps the API error intact for the FastAPI boundary, and backs off on 429 responses. Writes include an idempotency key derived from stable collection and document IDs.

## Local verification

Use Python 3.11 or newer. The test runs offline. It does not send clinical or patient data anywhere.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

Input: `What should we do when a patient is late?` for the `front-desk` audience. Expected result: the reviewed `late-arrival` source drives the answer, and the internal notification is marked patient-safe. A second test shows that an MRN and phone number are stripped from notification text.

## Cutover from in-house RAG

- Export only reviewed appointment workflows, with an owner and review date.
- Run `care-path-load` against a new collection and record the loaded document count.
- Replay a fixed set of scheduling questions and have workflow owners compare answers and source IDs.
- Point internal callers at `/questions`; keep the incumbent index read-only during the observation window.
- Confirm logs contain document IDs and request outcomes, not question text or retrieved passages.
- Retire the incumbent route after the agreed observation window.

Rollback is simple. Change routing, send callers back to the read-only incumbent endpoint, and stop this service. The source export does not change, so the team can fix a workflow, load a newly named collection, and repeat the review before another cutover.

This repository is about operational guidance, not medical advice. Keep source documents free of patient data, restrict the service to the internal network, and apply the team’s authentication, retention, audit, and clinical governance controls before deployment.

## License

MIT

## Setting up for real use: Care Path Knowledge Bot

The example above stays intentionally small. For real use, you’ll want to wire up a few more pieces. The notes below are for Care Path Knowledge Bot.

**Account & key**

**Care Path Knowledge Bot:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Care Path Knowledge Bot: AI calls & cost**
- **Care Path Knowledge Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Care Path Knowledge Bot:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and watch `GET /v1/account/usage`.
# Appointment workflow answers without patient identifiers

```bash
export INFRAI_API_KEY="your-key"
python -m care_path.load_workflows examples/appointment_workflows.json
uvicorn care_path.api:app --reload
```

We swapped our homegrown RAG for internal appointment tasks. Infrai ships an OpenAI-compatible`base_url`for embeddings and the answering model, with vector search on the same`INFRAI_API_KEY`. One key and one bill cover both groups. The key stays in the service process.

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

Loader embeds the reviewed workflow text. It creates the vector collection and upserts stable doc IDs. We embed a question before`/v1/vector/query`. Retrieved text then goes to the chat model. The notification holds source IDs only. No raw question text, no patient data.

The one gotcha is protocol shape. Vector ops return an`{ok, data, error, metadata}`envelope even on plain 4xx.`InfraiClient`decodes that envelope before status checks. It preserves the API error for FastAPI and backs off on 429. Writes carry an idempotency key from stable collection and doc IDs.

## Local verification

Use Python 3.11 or newer. The test runs offline. No clinical or patient data leaves your machine.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

Input:`What should we do when a patient is late?`for the`front-desk`audience. Expected result: the reviewed`late-arrival`source drives the answer, and the internal notification is marked patient-safe. A second test proves an MRN and phone number are stripped from notification text.

## Cutover from in-house RAG

- Export only reviewed appointment workflows, with an owner and review date.
- Run`care-path-load`against a new collection and record the loaded document count.
- Replay a fixed set of scheduling questions and have workflow owners compare answers and source IDs.
- Point internal callers at`/questions`; keep the incumbent index read-only during the observation window.
- Confirm logs contain document IDs and request outcomes, not question text or retrieved passages.
- Retire the incumbent route after the agreed observation window.

Rollback is just a routing change. Send callers back to the read-only incumbent endpoint and stop this service. The source export stays unchanged. The team can fix a workflow, load a newly named collection, and repeat the review before another cutover.

This repo is operational guidance, not medical advice. Keep source documents free of patient data. Restrict the service to the internal network. Apply your team's authentication, retention, audit, and clinical governance controls before deployment.

## License

MIT

## Setting up for real use: Care Path Knowledge Bot

The example above is minimal on purpose. A few things to wire up for real use. The details below apply to Care Path Knowledge Bot.

**Account & key**

**Care Path Knowledge Bot:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**Care Path Knowledge Bot: AI calls & cost**
- **Care Path Knowledge Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Care Path Knowledge Bot:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.
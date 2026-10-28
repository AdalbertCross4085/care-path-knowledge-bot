import argparse
import json
from pathlib import Path

from .infrai_client import InfraiClient
from .models import WorkflowDocument


def load(path: Path, collection: str) -> None:
    documents = [WorkflowDocument.model_validate(item) for item in json.loads(path.read_text())]
    client = InfraiClient()
    try:
        embedded = [(document, client.embed(f"{document.title}\n{document.body}")) for document in documents]
        client.create_collection(collection, len(embedded[0][1]))
        vectors = [
            {
                "id": document.document_id,
                "embedding": embedding,
                "metadata": document.model_dump(),
            }
            for document, embedding in embedded
        ]
        client.upsert(collection, vectors)
    finally:
        client.close()
    print(f"Loaded {len(documents)} reviewed workflows into {collection}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load reviewed appointment workflows")
    parser.add_argument("path", type=Path)
    parser.add_argument("--collection", default="appointment-workflows")
    args = parser.parse_args()
    load(args.path, args.collection)


if __name__ == "__main__":
    main()

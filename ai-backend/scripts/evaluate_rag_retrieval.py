"""Run an opt-in semantic retrieval benchmark against the configured embedding API.

From ai-backend, run:
    python scripts/evaluate_rag_retrieval.py

This makes live embedding requests and may incur provider charges. It does not call
the chat model, change the database, or write a report unless --output is supplied.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.embeddings import (  # noqa: E402
    EmbeddingServiceError,
    _resolve_embedding_config,
    embed_documents_sync,
    embed_query,
)
from app.services.rag_evaluation import rank_documents, score_ranked_results  # noqa: E402

FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "rag_retrieval_eval_cases.json"


def load_dataset(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        dataset = json.load(source)
    if dataset.get("schema_version") != 1 or not dataset.get("cases"):
        raise ValueError("Unsupported or empty RAG evaluation dataset.")

    all_ids: set[str] = set()
    for case in dataset["cases"]:
        for document in case["documents"]:
            document_id = document["id"]
            if document_id in all_ids:
                raise ValueError(f"Duplicate document id across evaluation cases: {document_id}")
            all_ids.add(document_id)
    return dataset


async def _embed_queries(cases: list[dict[str, Any]]) -> list[list[float]]:
    return list(await asyncio.gather(*(embed_query(case["query"]) for case in cases)))


def evaluate_dataset(dataset: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    """Embed a fixed document corpus and queries, then calculate ranking metrics."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    cases = dataset["cases"]
    documents = [
        document
        for case in cases
        for document in case["documents"]
    ]
    document_embeddings = embed_documents_sync([document["text"] for document in documents])
    if len(document_embeddings) != len(documents):
        raise EmbeddingServiceError("Document embedding count did not match benchmark corpus.")

    query_embeddings = asyncio.run(_embed_queries(cases))
    cursor = 0
    document_vectors_by_case: list[list[list[float]]] = []
    for case in cases:
        count = len(case["documents"])
        document_vectors_by_case.append(document_embeddings[cursor : cursor + count])
        cursor += count

    case_results: list[dict[str, Any]] = []
    for case, query_vector, local_vectors in zip(
        cases, query_embeddings, document_vectors_by_case, strict=True
    ):
        ranked = rank_documents(query_vector, case["documents"], local_vectors)
        relevance_by_id = {
            document["id"]: int(document["relevance"])
            for document in case["documents"]
        }
        metrics = score_ranked_results(
            [document_id for document_id, _score in ranked],
            relevance_by_id,
            k=top_k,
        )
        metadata = {document["id"]: document for document in case["documents"]}
        case_results.append(
            {
                "case_id": case["id"],
                "domain": case["domain"],
                "query": case["query"],
                "metrics": metrics,
                "ranked_documents": [
                    {
                        "id": document_id,
                        "title": metadata[document_id]["title"],
                        "relevance": relevance_by_id[document_id],
                        "cosine_similarity": round(score, 6),
                    }
                    for document_id, score in ranked
                ],
                "critical_failure": case["critical_failure"],
            }
        )

    metric_names = list(case_results[0]["metrics"])
    summary = {
        metric: round(fmean(result["metrics"][metric] for result in case_results), 4)
        for metric in metric_names
    }
    config = _resolve_embedding_config()
    return {
        "benchmark": "rag-retrieval-eval-v1",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_provider": config.provider,
        "embedding_model": config.model,
        "top_k": top_k,
        "case_count": len(case_results),
        "macro_average": summary,
        "cases": case_results,
        "limitations": [
            "Measures embedding-based ranking on this small fixed corpus, not final answer quality.",
            "Does not test database access controls, source citations in generated answers, or prompt-injection resistance.",
            "Compare results only when the evaluation dataset and embedding model/version are recorded.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=3, help="Cutoff for Recall@k and Precision@k.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional report path. Without this option, the report is printed to stdout.",
    )
    args = parser.parse_args()

    try:
        report = evaluate_dataset(load_dataset(), top_k=args.top_k)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, EmbeddingServiceError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"RAG evaluation report written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

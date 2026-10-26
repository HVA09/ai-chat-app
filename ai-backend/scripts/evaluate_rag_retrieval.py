"""Validate RAG benchmark data offline, with opt-in live embedding evaluation.

From ai-backend, run:
    python scripts/evaluate_rag_retrieval.py --validate-only

This default mode reads local benchmark data only. Live requests to the configured
embedding provider happen only when --run-live is explicitly supplied, and may
consume quota or incur charges. The tool does not call the chat model or modify a
database. A report is written to disk only when --output is supplied.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
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
    embed_documents_sync,
    embed_query,
    get_embedding_index_identity,
)
from app.services.rag_evaluation import rank_documents, score_ranked_results  # noqa: E402

FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "rag_retrieval_eval_cases.json"


REQUIRED_CASE_FIELDS = {"id", "domain", "query", "documents", "critical_failure"}
REQUIRED_DOCUMENT_FIELDS = {"id", "relevance", "title", "text"}


def dataset_sha256(dataset: dict[str, Any]) -> str:
    """Return a stable digest of the benchmark data without exposing its contents."""
    canonical = json.dumps(
        dataset,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    """Validate benchmark structure and labels without using the network."""
    if not isinstance(dataset, dict) or dataset.get("schema_version") != 1:
        raise ValueError("Unsupported RAG evaluation dataset schema.")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("RAG evaluation dataset must contain at least one case.")

    case_ids: set[str] = set()
    document_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or not REQUIRED_CASE_FIELDS <= case.keys():
            raise ValueError("Each RAG case must contain id, domain, query, documents and critical_failure.")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError(f"Missing or duplicate RAG case id: {case_id!r}")
        case_ids.add(case_id)
        if not isinstance(case["domain"], str) or not case["domain"].strip():
            raise ValueError(f"Case {case_id} must have a domain.")
        if not isinstance(case["query"], str) or len(case["query"].strip()) < 10:
            raise ValueError(f"Case {case_id} must have a non-empty query.")
        if not isinstance(case["critical_failure"], str) or not case["critical_failure"].strip():
            raise ValueError(f"Case {case_id} must describe a critical failure.")
        documents = case["documents"]
        if not isinstance(documents, list) or len(documents) < 2:
            raise ValueError(f"Case {case_id} must contain at least two documents.")

        grades: list[int] = []
        for document in documents:
            if not isinstance(document, dict) or not REQUIRED_DOCUMENT_FIELDS <= document.keys():
                raise ValueError(f"Every document in case {case_id} must have id, relevance, title and text.")
            document_id = document["id"]
            if not isinstance(document_id, str) or not document_id or document_id in document_ids:
                raise ValueError(f"Missing or duplicate RAG document id: {document_id!r}")
            document_ids.add(document_id)
            grade = document["relevance"]
            if isinstance(grade, bool) or not isinstance(grade, int) or grade not in {0, 1, 2}:
                raise ValueError(f"Document {document_id} relevance must be 0, 1, or 2.")
            grades.append(grade)
            if not isinstance(document["title"], str) or not document["title"].strip():
                raise ValueError(f"Document {document_id} must have a title.")
            if not isinstance(document["text"], str) or len(document["text"].strip()) < 10:
                raise ValueError(f"Document {document_id} must contain readable text.")

        if 2 not in grades or 0 not in grades:
            raise ValueError(f"Case {case_id} must include a highly relevant document (2) and a negative (0).")

    return dataset


def dataset_validation_summary(dataset: dict[str, Any]) -> dict[str, Any]:
    """Return an offline corpus summary for the --validate-only CLI mode."""
    cases = dataset["cases"]
    domain_counts: dict[str, int] = {}
    relevance_counts = {"0": 0, "1": 0, "2": 0}
    document_count = 0
    for case in cases:
        domain_counts[case["domain"]] = domain_counts.get(case["domain"], 0) + 1
        for document in case["documents"]:
            document_count += 1
            grade = str(document["relevance"])
            relevance_counts[grade] += 1
    return {
        "benchmark": "rag-retrieval-eval-v1",
        "dataset_sha256": dataset_sha256(dataset),
        "validation_only": True,
        "live_embedding_requests_sent": False,
        "case_count": len(cases),
        "document_count": document_count,
        "domain_counts": dict(sorted(domain_counts.items())),
        "relevance_grade_counts": relevance_counts,
    }


def load_dataset(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        dataset = json.load(source)
    return validate_dataset(dataset)

async def _embed_queries(cases: list[dict[str, Any]]) -> list[list[float]]:
    # Keep requests sequential to avoid spiking a provider's rate limit.
    vectors: list[list[float]] = []
    for case in cases:
        vectors.append(await embed_query(case["query"]))
    return vectors


def evaluate_dataset(dataset: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    """Embed a fixed document corpus and queries, then calculate ranking metrics."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    # Validate the full corpus before spending quota on any external requests.
    dataset = validate_dataset(dataset)
    provider, model, embedding_fingerprint = get_embedding_index_identity()
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
        first_relevant_rank = next(
            (
                rank
                for rank, (document_id, _score) in enumerate(ranked, start=1)
                if relevance_by_id[document_id] > 0
            ),
            None,
        )
        top1_is_irrelevant = bool(
            ranked and relevance_by_id[ranked[0][0]] == 0
        )
        case_results.append(
            {
                "case_id": case["id"],
                "domain": case["domain"],
                "query": case["query"],
                "metrics": metrics,
                "top1_is_irrelevant": top1_is_irrelevant,
                "first_relevant_rank": first_relevant_rank,
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
    results_by_domain: dict[str, list[dict[str, Any]]] = {}
    for result in case_results:
        results_by_domain.setdefault(result["domain"], []).append(result)
    domain_summary = {
        domain: {
            **{
                metric: round(
                    fmean(result["metrics"][metric] for result in domain_results), 4
                )
                for metric in metric_names
            },
            "top1_irrelevant_count": sum(
                result["top1_is_irrelevant"] for result in domain_results
            ),
            "top1_irrelevant_rate": round(
                fmean(
                    float(result["top1_is_irrelevant"])
                    for result in domain_results
                ),
                4,
            ),
            "mean_first_relevant_rank": round(
                fmean(
                    float(result["first_relevant_rank"])
                    for result in domain_results
                    if result["first_relevant_rank"] is not None
                ),
                4,
            ),
        }
        for domain, domain_results in sorted(results_by_domain.items())
    }
    top1_irrelevant_count = sum(
        result["top1_is_irrelevant"] for result in case_results
    )
    retrieval_diagnostics = {
        "top1_irrelevant_count": top1_irrelevant_count,
        "top1_irrelevant_rate": round(
            top1_irrelevant_count / len(case_results), 4
        ),
        "mean_first_relevant_rank": round(
            fmean(
                float(result["first_relevant_rank"])
                for result in case_results
                if result["first_relevant_rank"] is not None
            ),
            4,
        ),
    }
    return {
        "benchmark": "rag-retrieval-eval-v1",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": dataset_sha256(dataset),
        "embedding_provider": provider,
        "embedding_model": model,
        "embedding_fingerprint": embedding_fingerprint,
        "top_k": top_k,
        "case_count": len(case_results),
        "macro_average": summary,
        "retrieval_diagnostics": retrieval_diagnostics,
        "by_domain": domain_summary,
        "cases": case_results,
        "limitations": [
            "Measures embedding-based ranking on this small fixed corpus, not final answer quality.",
            "Does not test database access controls, source citations in generated answers, or prompt-injection resistance.",
            "Compare results only when the evaluation dataset and embedding model/version are recorded.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Cutoff for Recall@k, Precision@k and nDCG@k (used with --run-live).",
    )
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and summarize the local fixture without calling the provider (default).",
    )
    run_mode.add_argument(
        "--run-live",
        action="store_true",
        help="Explicitly request live embeddings from the configured provider; this may consume quota or cost money.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional report path. Without this option, the report is printed to stdout.",
    )
    args = parser.parse_args()

    try:
        dataset = load_dataset()
        # Safety first: no provider calls occur unless the user explicitly opts in.
        report = (
            evaluate_dataset(dataset, top_k=args.top_k)
            if args.run_live
            else dataset_validation_summary(dataset)
        )
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

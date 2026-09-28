"""Deterministic TF-IDF knowledge-base retrieval."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class RetrievedDocument:
    id: str
    title: str
    content: str
    similarity_score: float

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


def load_knowledge_base(path: str | Path) -> list[dict[str, str]]:
    """Load and minimally validate the knowledge-base JSON file."""

    with Path(path).open(encoding="utf-8") as handle:
        documents = json.load(handle)
    if not isinstance(documents, list):
        raise ValueError("knowledge base must be a JSON array")
    required = {"id", "title", "content"}
    for document in documents:
        if not isinstance(document, dict) or not required.issubset(document):
            raise ValueError("each knowledge-base document needs id, title, and content")
    return documents


class TfidfRetriever:
    """Small, inspectable retriever suitable for deterministic QA."""

    def __init__(self, documents: list[dict[str, str]]) -> None:
        if not documents:
            raise ValueError("at least one knowledge-base document is required")
        self.documents = documents
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        corpus = [f"{item['title']} {item['content']}" for item in documents]
        self.document_matrix = self.vectorizer.fit_transform(corpus)

    @classmethod
    def from_json(cls, path: str | Path) -> "TfidfRetriever":
        return cls(load_knowledge_base(path))

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.10) -> list[RetrievedDocument]:
        if not query or not query.strip():
            return []
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.document_matrix).ravel()
        ranked_indices = scores.argsort()[::-1]
        results: list[RetrievedDocument] = []
        for index in ranked_indices:
            score = float(scores[index])
            if score < min_score:
                continue
            source = self.documents[int(index)]
            results.append(
                RetrievedDocument(
                    id=source["id"],
                    title=source["title"],
                    content=source["content"],
                    similarity_score=round(score, 6),
                )
            )
            if len(results) == top_k:
                break
        return results


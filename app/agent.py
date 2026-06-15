from __future__ import annotations

import time
from dataclasses import dataclass

from . import metrics
from .mock_llm import FakeLLM
from .mock_rag import retrieve
from .pii import hash_user_id, summarize_text
from .tracing import get_langfuse_client, observe, propagate_trace_attributes


@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model
        self.llm = FakeLLM(model=model)

    @observe(name="chat-response", as_type="agent", capture_input=False, capture_output=False)
    def run(
        self,
        user_id: str,
        feature: str,
        session_id: str,
        message: str,
        correlation_id: str | None = None,
    ) -> AgentResult:
        started = time.perf_counter()
        user_id_hash = hash_user_id(user_id)
        langfuse = get_langfuse_client()
        trace_input = {
            "message_preview": summarize_text(message),
            "feature": feature,
            "correlation_id": correlation_id,
        }
        trace_metadata = {
            "feature": feature,
            "model": self.model,
            "correlation_id": correlation_id or "",
            "user_id_hash": user_id_hash,
        }

        with propagate_trace_attributes(
            user_id=user_id_hash,
            session_id=session_id,
            tags=["lab", feature, self.model],
            metadata=trace_metadata,
            trace_name="chat-response",
        ):
            langfuse.update_current_span(input=trace_input, metadata=trace_metadata)

            with langfuse.start_as_current_observation(
                as_type="retriever",
                name="rag-retrieve",
                input={"query_preview": summarize_text(message)},
            ) as retrieval_span:
                docs = retrieve(message)
                retrieval_span.update(
                    output={
                        "doc_count": len(docs),
                        "documents_preview": [summarize_text(doc) for doc in docs],
                    }
                )

            prompt = f"Feature={feature}\nDocs={docs}\nQuestion={message}"
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="mock-llm-generate",
                model=self.model,
                input={"prompt_preview": summarize_text(prompt, max_len=200)},
            ) as generation:
                response = self.llm.generate(prompt)
                generation.update(
                    output=summarize_text(response.text, max_len=200),
                    usage_details={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                    cost_details={
                        "total_cost": self._estimate_cost(
                            response.usage.input_tokens,
                            response.usage.output_tokens,
                        )
                    },
                )

            quality_score = self._heuristic_quality(message, response.text, docs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            cost_usd = self._estimate_cost(response.usage.input_tokens, response.usage.output_tokens)

            trace_output = {
                "answer_preview": summarize_text(response.text),
                "quality_score": quality_score,
                "latency_ms": latency_ms,
            }
            langfuse.update_current_span(output=trace_output, metadata=trace_metadata)
            langfuse.score_current_trace(
                name="quality_score",
                value=quality_score,
                data_type="NUMERIC",
                comment="Deterministic lab heuristic quality score.",
            )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=response.text,
            latency_ms=latency_ms,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        input_cost = (tokens_in / 1_000_000) * 3
        output_cost = (tokens_out / 1_000_000) * 15
        return round(input_cost + output_cost, 6)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 40:
            score += 0.1
        if question.lower().split()[0:1] and any(token in answer.lower() for token in question.lower().split()[:3]):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)

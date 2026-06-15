# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata

- [GROUP_NAME]: Nguyễn Thái Hoàng
- [REPO_URL]:https://github.com/SpaceBunz66/Lab13-Observability

---

## 2. Group Performance (Auto-Verified)

- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 11
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence

### 3.1 Logging & Tracing

- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: ![Correlation ID Screenshot](docs\envidence\03_logs_correlation_id.png)
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: ![Correlation ID Screenshot](docs\envidence\04_logs_pii_redaction.png)
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: ![Correlation ID Screenshot](docs\envidence\02_langfuse_trace_waterfall.png)
- [TRACE_WATERFALL_EXPLANATION]: The selected Langfuse trace shows the full request lifecycle from the root chat-response observation into child observations such as rag-retrieve and mock-llm-generate. The rag-retrieve span is especially useful because it isolates retrieval latency from LLM generation latency, which helps identify whether a slow response is caused by RAG retrieval or model generation.

### 3.2 Dashboard & SLOs

- [DASHBOARD_6_PANELS_SCREENSHOT]: ![Correlation ID Screenshot](docs\envidence\05_dashboard_6_panels.png)
![Correlation ID Screenshot](docs\envidence\06_dashboard_6_panels.png)
- [SLO_TABLE]:  | SLI               |     Target  | Window        | Current Value |
  | ----------- | ---------:        | ------      | ------------: |
  | Latency P95 |  < 3000ms         | 28d         |               |153.0ms
  | Error Rate  |       < 2%        | 28d         |               |0%
  | Cost Budget | < $2.5/day        | 1d          |               |$0.0391/day

### 3.3 Alerts & Runbook

- [ALERT_RULES_SCREENSHOT]: ![Correlation ID Screenshot](docs\envidence\07_alert_rules_runbook.png)
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md#1-high-latency-p95]

---

## 4. Incident Response (Group)

- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: After enabling the rag_slow incident and running the load test, the dashboard showed increased request latency, especially Latency P95. In Langfuse, the slow trace showed that the rag-retrieve span took longer than normal while the mock-llm-generate span remained comparatively normal.
- [ROOT_CAUSE_PROVED_BY]: Langfuse Trace ID: [78b996bfbf51a0ce93c0d26dfb4d6ecd]. The trace waterfall shows the rag-retrieve span dominating the total chat-response duration. Supporting log evidence: [docs\envidence\08_rag_slow_log.png].
- [FIX_ACTION]:Disabled the incident using scripts/inject_incident.py --scenario rag_slow --disable, then reran the load test and verified that latency returned closer to baseline.
- [PREVENTIVE_MEASURE]:Keep the high_latency_p95 alert active, monitor RAG span duration separately from LLM generation span duration, and add retrieval timeout/fallback behavior so slow RAG does not block the full chat response.

---


## 6. Bonus Items (Optional)

- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)

# llm — LLM defenses (OWASP LLM Top 10)

Audit `packages/api` for LLM-specific weaknesses. The app orchestrates local
LLMs (Ollama) for captures, recaps, a Concierge agent, and deep-research.

- **LLM01 Prompt injection (direct + indirect)**: is untrusted input (user notes,
  game names, captured text, scraped web pages) sanitized and delimited
  (`<user_data>` / `udata` filter) before entering a prompt? Can a captured note
  or a scraped page steer the model?
- **LLM06 Excessive Agency (tool boundary)**: the Concierge/agent tools — is tool
  dispatch a hard code-side allowlist (not a raw model string → callable)? are
  args validated (types, ownership, allowed values) BEFORE side effects? is
  `user_id` bound server-side (never LLM-supplied)? are tool loops / recursion /
  cost bounded? deep-research fan-out bounded?
- **LLM08 Vector/embedding**: is every pgvector/embedding query scoped to the
  requesting user's `(user, entry)` — no cross-user retrieval? is retrieved text
  treated as untrusted data in the prompt?
- **Cache poisoning**: the semantic LLM cache — can one user poison an entry
  another reads (global namespace, key collision)? blast radius?
- **LLM05 Output handling / LLM09 misinformation**: anti-hallucination validation
  (token overlap) on LLM output before persistence? is output rendered as text
  (not HTML) downstream?
- **System-prompt leakage**: can the agent be made to dump its prompt / another
  user's data?

Read `core/concierge/*`, `infrastructure/agent/*`, the LangGraph graph + tool
registry, `core/play_session/retrieval.py`, `infrastructure/embedding/*`,
`infrastructure/llm/*capture_cache*`, and the prompt templates (`prompts/*.j2`).

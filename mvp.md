# Standalone CCN App — Implementation Plan

## Goals

- Run a minimal, operable EPN cycle with live Groq calls.
- Single Multi-Worker; CCN assigns Roles via SYNAPTIC KV lists.
- Internal-only MEMORY (worklist, active slot, archive, aggregator buffer, run log).
- JSON-only outputs for every role; strict parsing; fail fast; human-auditable.
- Clear debug "windows": context snapshots, prompts, llm params, raw JSON responses, mutations.

## Architecture Overview

- CCN: orchestrator; pops SYNAPTIC from MEMORY worklist, materializes Role
  from KV list → Node Template, binds inputs, and mutates MEMORY. In MVP,
  built-in steps are invoked inside the worker; CCN does not dispatch
  per-step calls. An optional mode can enable CCN-dispatch based on
  `call_plan`.
- Multi-Worker (single instance): executes assigned Role; methods:
  `build_prompt`, `prompt_call`, `emit` (returns values only; CCN mutates
  MEMORY). In MVP, `execute_role` runs `prompt_call` → `emit` internally.
- MEMORY (explicit data structures):
  - worklist: deque[SynapticKVList]
  - active_slot: Optional[MaterializedRole]
  - archive: list[PerRoleRecord]
  - aggregator_buffer: list[AnyJson]
  - run_log: list[CCNEvent]
- Built-in Roles: REFORMULATOR, ELUCIDATOR. Dynamic worker roles created from ELUCIDATOR query_decomposition. Final role: SYNTHESIZER.
- JSON-only: all roles return strict JSON envelopes (see Data Contracts).

## Data Contracts (condensed)

- Node Template (control-plane): attributes {node_id, entry_id, input_signals, node_output_signal, tasks, instructions=""}; llm_config {model, temperature, max_tokens, reasoning_effort, response_format={"type":"json_object"}}.
- SYNAPTIC format (data-plane): KV-pair list only. Strict semantics: no auto-create, arrays in-bounds or append at end, types must match template, only `attributes.*` and `llm_config.*` keys allowed.
- Role Output Envelopes:
  - REFORMULATOR → `{ "reformulated_question": "<text>" }`.
  - ELUCIDATOR → `{ "query_decomposition": [["label","ROLE: <ROLE_NAME>. <desc>"], ...] }`. The number of items is defined in `templates/prompts.md` and not hard‑coded; the template normally instructs the final item to be `ROLE: SYNTHESIZER`.
  - Worker roles (default) → `{ "node_output_signal": "<text>" }`.
  - SYNTHESIZER → `{ "node_output_signal": "<text>" }`.

### Built-in Role: REFORMULATOR (mandatory transformations)

- Replace "what are" with "how do/function as" or "what constitutes".
- Add explicit epistemic context (e.g., "within cognitive science's study of...").
- Include narrative hooks (e.g., "evolution of", "function as", "role in").
- Eliminate presupposition of simple answers.
- Prime for multi-perspective analysis.

Example transformation: "What are mental models?" →
"How have mental models been conceptualized as cognitive frameworks within different theoretical approaches in cognitive science?"

Input: `{query}`

Output: JSON only `{ "reformulated_question": "<text>" }`.

### Validation Timeline (MVP)

1) KV materialization: validate key whitelist, path existence (no auto-create), array bounds, and types; raise ValidationError on failure.
2) Role output parse: immediately after LLM call, parse strict JSON per Role envelope; on error, log `error` event + raw body, raise.
3) End-of-run: validate `archive` against `schemas/memory_record.schema.json` via `jsonschema`; `--strict` flag to error vs warn.

## Files & Responsibilities

- `ccn_minirun.py` — CLI entrypoint, seeds built-ins, runs CCN loop, prints final synthesis.
- `mini_memory.py` — MEMORY dataclasses + helpers (worklist ops, run log, archive/record builders). Shapes match the explicit types listed above.
- `mini_synaptic.py` — KV parser/materializer (strict rules), Node Template constant, validators.
- `worker_node.py` — WorkerNode class; `build_prompt`, `prompt_call`, `emit`.
- `mini_ccn.py` — CCN loop, binding rules, execution plan, JSON parsing, mutations, debug windows.
- `llm_client.py` — thin Groq wrapper; else add minimal client init + call.
- `schemas/memory_record.schema.json` — validate archive shape at end-of-run (best-effort).

## Execution Plan (canonical)

MVP: the worker executes `prompt_call` → `emit` internally for all roles;
CCN records outputs and mutates MEMORY. When CCN-dispatch is enabled, CCN
invokes the plan directly and honors `call_plan` (validated to
`["prompt_call", "emit"]`).

- REFORMULATOR → `[prompt_call, emit]` (record output in MEMORY).
- ELUCIDATOR → `[prompt_call, emit]` (record `query_decomposition` in MEMORY;
  CCN enqueues worker roles as instructed by the template and initializes the Aggregator Buffer).
- Worker Role (task-specific) → `[prompt_call, emit]` (append output to
  Aggregator Buffer).
- SYNTHESIZER → `[prompt_call, emit]` (record final output).

## Binding Rules (producer → consumer)

- User input → REFORMULATOR: bind query → `attributes.input_signals[0]`.
- REFORMULATOR → ELUCIDATOR: parse JSON, extract `reformulated_question` → `attributes.input_signals[0]`.
- ELUCIDATOR → Worker Roles: parse object, read `query_decomposition` (count governed by template). For each item `[label, qd_string]`, extract `<ROLE_NAME>` from `qd_string`, set `attributes.node_id = <ROLE_NAME>`, and bind `reformulated_question` → `attributes.input_signals[0]`, `qd_string` → `attributes.input_signals[1]`. Do not populate `attributes.tasks` unless required by the role.
- Workers → SYNTHESIZER: append `node_output_signal` to Aggregator Buffer.
- ELUCIDATOR (final decomposition) → SYNTHESIZER: bind
  `reformulated_question` → `attributes.input_signals[0]`, then bind each
  worker output as a separate item in `attributes.input_signals[1..]`
  (preserving order). Apply the final SYNTHESIZER directive as
  `attributes.instructions`.

## Prompt Construction (guide)

- Sources: attributes.input_signals (index 0 is the reformulated question for analytical context, index 1 is the authoritative decomposition string for worker roles), attributes.instructions (role-specific), llm_config.
- Layout: header (Role), Inputs (Input[i]: ...), optional Instructions. No fallbacks. Worker roles and SYNTHESIZER must return `{ "node_output_signal": "<text>" }`; REFORMULATOR and ELUCIDATOR must return their respective envelopes as above. Worker roles should keep outputs ≤70 words; SYNTHESIZER ≤140 words.
- Log before LLM call: record a `prompt_window` (prompt text + llm_config).

## Call Plan Overrides (MVP)

- Allowed plan items: `["prompt_call", "emit"]` only.
- Validation: if `call_plan` present, must be a list of allowed items in
  canonical order; otherwise error.
- Runtime: in MVP, `call_plan` is validated but ignored (worker runs the
  steps). When CCN-dispatch is enabled, `call_plan` becomes authoritative.
- `call_args`: not used in MVP; if present, must be an empty object (`{}`).

## LLM Invocation (Groq)

- Initialize once: `client = Groq(api_key=os.environ["GROQ_API_KEY"])` (fail fast if missing).
- Call chat completions with: model, temperature, max_completion_tokens (from llm_config.max_tokens), reasoning_effort, response_format={"type":"json_object"}.
- Messages: put rendered prompt in `user` content; optionally a minimal `assistant` priming with the exact JSON envelope.
- Response: read `completion.choices[0].message.content`; parse JSON; fail fast on error.

## Dependencies & Environment

- Python 3.11+
- Packages: `groq`, `jsonschema`, `rich` (for debug windows), `click` (CLI)
- Environment: `GROQ_API_KEY` must be set (fail fast if missing)

## Security & Privacy

- Never log secrets; redact env values.
- Sanitize/limit user input when printing windows; cap to 2k chars.
- Avoid writing prompts/responses to disk unless explicitly requested.

## Limits & Timeouts (MVP)

- ELUCIDATOR query_decomposition: numeric cap is defined in `templates/prompts.md` (not hard‑coded).
- Worklist/aggregator caps: configurable (defaults: worklist≤100, buffer≤100).
- LLM call timeout: configurable per call; abort on timeout and archive error.

## Observability (MVP)

- Structured JSON logging to stdout (JSON lines) for key events.
- Metrics counters printed at end: roles_processed, enqueued_roles, aggregator_appends, llm_errors, parse_errors; simple duration totals.

## Debug Windows

- Cycle start: worklist head summary, active role id, archive count.
- Prompt window: show Role id, llm_config (model, temperature, max_tokens), rendered prompt, raw JSON response.
- After emit: mutation summary — enqueued roles N / aggregator_append count / archived role id.

## Validation & Fail-Fast

- KV materialization: strict path/type checks; invalid → raise ValidationError.
- Role parsing: enforce per-role JSON envelopes; parse failure → raise with raw body logged.
- MEMORY schema: at end-of-run validate archive against `schemas/memory_record.schema.json` (warnings or error per a `--strict` flag).

## CLI UX

- Run: `python scripts/ccn_minirun.py "Why are models useful despite being wrong?"`
- Env: `export GROQ_API_KEY=gsk_...`
- Output: per-cycle windows + final JSON from SYNTHESIZER printed to stdout.

Advanced (optional CCN-dispatch):

- Run: `python ccn_minirun.py --ccn-dispatch "Explain quantum computing"`
- Effect: CCN dispatches `prompt_call` → `emit` and honors `call_plan`.

## Milestones

1) Scaffolding: MEMORY, KV materializer, Node Template, WorkerNode stubs, Groq client wrapper.
2) Built-ins: implement REFORMULATOR + ELUCIDATOR contracts; run end-to-end through worker enqueue. The number of ELUCIDATOR items is governed by `templates/prompts.md`.
3) Worker roles + Aggregator: parse query_decomposition items, execute workers, append to buffer.
4) SYNTHESIZER: consume buffer and produce final JSON.
5) Windows + Archive: full logging, archive PerRoleRecord, end-of-run validation.
6) Polish: error surfaces, helpful diagnostics, small refactors.

## Out-of-Scope (MVP)

- Persistence to disk (MEMORY lives in-process; can be serialized later).
- Multi-turn interactivity or UI; single CLI run only.
- External template files (built-ins are embedded for portability).

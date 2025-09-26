# Standalone CCN App — Implementation Plan

## Goals

- Run a minimal, operable EPN cycle with live Groq calls.
- Single Multi-Worker; CCN assigns Roles via SYNAPTIC KV lists.
- Internal-only MEMORY (worklist, active slot, archive, aggregator buffer, run log).
- JSON-only outputs for every role; strict parsing; fail fast; human-auditable.
- Clear debug "windows": context snapshots, prompts, llm params, raw JSON responses, mutations.

## Architecture Overview

- CCN: orchestrator; pops SYNAPTIC from MEMORY worklist, materializes Role from KV list → Node Template, binds inputs, dispatches canonical plan, mutates MEMORY.
- Multi-Worker (single instance): executes assigned Role; methods: `build_prompt`, `prompt_call`, `emit` (returns values only; CCN mutates MEMORY).
- MEMORY (explicit data structures):
  - worklist: deque[SynapticKVList]
  - active_slot: Optional[MaterializedRole]
  - archive: list[PerRoleRecord]
  - aggregator_buffer: list[AnyJson]
  - run_log: list[CCNEvent]
- Built-in Roles: REFORMULATOR, ELUCIDATOR. Dynamic worker roles created from ELUCIDATOR tasks. Final role: SYNTHESIZER.
- JSON-only: all roles return strict JSON envelopes (see Data Contracts).

## Data Contracts (condensed)

- Node Template (control-plane): attributes {node_id, entry_id, input_signals, node_output_signal, tasks, instructions=""}; llm_config {model, temperature, max_tokens, reasoning_effort, response_format={"type":"json_object"}}.
- SYNAPTIC format (data-plane): KV-pair list only. Strict semantics: no auto-create, arrays in-bounds or append at end, types must match template, only `attributes.*` and `llm_config.*` keys allowed.
- Role Output Envelopes:
  - REFORMULATOR → `{ "reformulated_question": "<text>" }`.
  - ELUCIDATOR → `{ "tasks": [["task N","ROLE: <ROLE_NAME>. <desc> ... RESPONSE_JSON: {...}"], ...] }` (maximum 4 items) with the final item for `ROLE: SYNTHESIZER`.
  - Worker roles (default) → `{ "node_output_signal": "<text>" }` (unless ELUCIDATOR provides a different RESPONSE_JSON contract for that task).
  - SYNTHESIZER → `{ "node_output_signal": "<text>" }`.

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

- REFORMULATOR → `[prompt_call, emit]` (record output in MEMORY).
- ELUCIDATOR → `[prompt_call, emit]` (record `tasks` list in MEMORY; CCN enqueues ≤4 worker roles + init Aggregator Buffer).
- Worker Role (task-specific) → `[prompt_call, emit]` (append output to Aggregator Buffer).
- SYNTHESIZER → `[prompt_call, emit]` (record final output).

## Binding Rules (producer → consumer)

- User input → REFORMULATOR: bind query → `attributes.input_signals[0]`.
- REFORMULATOR → ELUCIDATOR: parse JSON, extract `reformulated_question` → `attributes.input_signals[0]`.
- ELUCIDATOR → Worker Roles: parse object, read `tasks` (max 4 items); for each item, set `attributes.node_id = <ROLE_NAME>`, copy task text → `attributes.tasks[0]`, and bind reformulated question → `attributes.input_signals[0]`; if a RESPONSE_JSON appears, attach to the worker’s prompt/contract.
- Workers → SYNTHESIZER: append `node_output_signal` to Aggregator Buffer.

## Prompt Construction (guide)

- Sources: attributes.input_signals, attributes.tasks[0], attributes.instructions (string), llm_config.
- Layout: header (Role), Task, Inputs (Input[i]: ...), Instructions. No fallbacks. When JSON is required (always), instructions must include exact JSON contract.
- Log before LLM call: record a `prompt_window` (prompt text + llm_config).

## Call Plan Overrides (MVP)

- Allowed plan items: `["prompt_call", "emit"]` only.
- Validation: if `call_plan` present, must be a list of allowed items in canonical order; otherwise error.
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

- ELUCIDATOR tasks: max 4 items (including final SYNTHESIZER).
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

## Milestones

1) Scaffolding: MEMORY, KV materializer, Node Template, WorkerNode stubs, Groq client wrapper.
2) Built-ins: implement REFORMULATOR + ELUCIDATOR contracts (ELUCIDATOR ≤4 tasks); run end-to-end through worker enqueue.
3) Worker roles + Aggregator: parse tasks, execute workers, append to buffer.
4) SYNTHESIZER: consume buffer and produce final JSON.
5) Windows + Archive: full logging, archive PerRoleRecord, end-of-run validation.
6) Polish: error surfaces, helpful diagnostics, small refactors.

## Out-of-Scope (MVP)

- Persistence to disk (MEMORY lives in-process; can be serialized later).
- Multi-turn interactivity or UI; single CLI run only.
- External template files (built-ins are embedded for portability).

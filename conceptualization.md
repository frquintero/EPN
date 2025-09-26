# Overview

EPN’s objective is to transform an open-ended, potentially biased question
into a rigorous, multi-perspective explanation that can be trusted. It does
so by: (1) reformulating the user prompt into a neutral, epistemically sound
inquiry; (2) planning a set of complementary tasks that probe facts,
contexts, relationships, and interpretations; (3) executing those tasks with
specialized LLM-backed workers; and (4) synthesizing the results into a
coherent answer.

In this design, CCN is the deterministic spine of EPN. It loads human-authored
`SYNAPTIC` entries (e.g., REFORMULATOR, ELUCIDATOR) from JSON, validates them
against a canonical Node Template, creates a single Multi-Worker via
`type()`, and dispatches built-in methods in a predictable order. Workers do
not access `MEMORY`; CCN feeds them inputs and they return results via a
single `emit` operation. CCN performs all MEMORY mutations (recording,
targeted updates, or enqueuing new entries) based on those results. This
contract-first approach keeps data flow explicit, prevents
hidden side-effects, and makes the pipeline reproducible and auditable.

## Class Creator Node (CCN)

This document specifies a minimal, deterministic architecture for a class
creator node (CCN) that acts as a factory and controller. CCN creates a
WorkerNode class via `type()` and instantiates a single Multi-Worker
object with the standard method library. The Multi-Worker then executes
Roles using `SYNAPTIC` entries that CCN feeds from its internal `MEMORY`,
while CCN orchestrates execution by dispatching built-in method calls
(via `getattr`). Workers do not access `MEMORY`; CCN does.

## Terminology

- EPN: Epistemic Processing Network, the overall architecture of LLM-backed
  agents collaborating to explore and synthesize knowledge.
- CCN: Class Creator Node; the orchestrator that runs the control loop,
  instantiates the Multi-Worker, binds inputs, and dispatches method calls.
- Node Template: Control-plane definition used by CCN to create the
  WorkerNode class (schema, defaults, and method library metadata).
- WorkerNode (class): Dynamically created class (via `type()`) that exposes
  the standard method library but no role-specific state.
- Multi-Worker (instance): A single WorkerNode instance that executes many
  Roles by being assigned `SYNAPTIC` entries over time.
- Role: A runtime assignment (a specific behavior) executed by the
  Multi-Worker. Each Role is fully described by a `SYNAPTIC` entry.
- REFORMULATOR (Role, built-in): Reformulates the user query into a neutral,
  epistemically sound inquiry.
- ELUCIDATOR (Role, built-in): Generates a list of self-contained task
  definitions that
  include the target Role per task (e.g., ANALYZER, EXPLORER) and task text.
- SYNTHESIZER (Role): Aggregates outputs from worker Roles into a coherent
  synthesis and emits the final result.
- MEMORY: CCN-internal registry that holds a FIFO worklist of `SYNAPTIC`
  entries (JSON objects), an Aggregator Buffer for worker outputs, and a run
  log. Only CCN reads/writes MEMORY.
- SYNAPTIC: The data-plane values (`attributes`, `llm_config`, and optional
  `call_plan`/`call_args`) that parameterize a Role execution. A `SYNAPTIC`
  entry must be provided as a KV-pair list.
- Synaptic format: `SYNAPTIC` entries are KV-pair lists (list of
  `[key, value]` tuples).
- Node Template: Canonical format used to build the WorkerNode class (control
  plane).
- Method Library: The fixed set of built-in methods available to every
  WorkerNode. Details are documented separately.

## EPN Cycle

EPN’s execution flows from user input to SYNTHESIZER. At startup,
CCN creates the Multi-Worker (from the Node Template), captures the user
query (CLI arg or file), and enqueues a validated REFORMULATOR `SYNAPTIC`
entry to process it.

General flow in a Multi-Worker cycle:

1. CCN pops the next `SYNAPTIC` entry from the head of its MEMORY worklist (FIFO).
2. CCN binds inputs for this Role (see Binding Rules), assigns the entry to
   the existing Multi-Worker (no new instantiation), and dispatches built-in
   methods per the canonical plan (or a provided `call_plan` override).
3. After binding and successfully assigning the Role on the Multi-Worker,
   CCN marks the consumed `SYNAPTIC` entry as completed (the Role then runs
   against the assigned state).
4. The Multi-Worker emits its result via a single `emit` operation (the
   role’s LLM output). CCN then updates the appropriate entry or enqueues
   new `SYNAPTIC` entries based on that output and CCN’s control logic (for
   example, after ELUCIDATOR).

The Multi-Worker communicates results back via `emit` (returning
`attributes.node_output_signal`). CCN consumes that value and deterministically
performs the required action: targeted update (e.g., aggregator append) or
enqueuing derived Roles (e.g., from ELUCIDATOR’s tasks).

CCN binds the user query to the REFORMULATOR Role’s `attributes.input_signals[0]`.
Acting as REFORMULATOR, the Multi-Worker runs `prompt_call` to produce a
reformulated question, then triggers `emit` to publish it. CCN records the
reformulation and uses it as the input for the ELUCIDATOR Role.
Acting as ELUCIDATOR, the Multi-Worker runs `prompt_call` to produce a list of
self-contained task definitions that include the target Role per task
and a task description. It then triggers `emit` to publish that list. CCN
records it and proceeds.

From ELUCIDATOR’s tasks, CCN constructs and enqueues one JSON `SYNAPTIC` entry
per task (one worker Role per task), and initializes an Aggregator Buffer in
MEMORY for the SYNTHESIZER Role. CCN validates these entries and assigns each to the
Multi-Worker as a new Role, executing them in FIFO order.

For each worker Role, the Multi-Worker runs `prompt_call`, produces a
task-level `node_output_signal`, and triggers `emit`. CCN appends the
signal into the Aggregator Buffer so the SYNTHESIZER has all
worker signals collected in one place. Finally, the Multi-Worker assumes the
SYNTHESIZER Role using that dedicated aggregator-backed `SYNAPTIC` entry. It
synthesizes the accumulated signals into a coherent, well-grounded answer.
That final synthesis is emitted as the cycle’s result, ready to be surfaced or
to seed a new inquiry if desired.

## Node Template

```json
{
  "attributes": {
    "node_id": null,
    "entry_id": null,
    "input_signals": [],
    "node_output_signal": null,
    "tasks": [],
    "instructions": ""
  },
  "llm_config": {
    "cloud_platform": "groq",
    "model": "openai/gpt-oss-120b",
    "temperature": 0.8,
    "reasoning_effort": "high",
    "max_tokens": 8000,
    "response_format": {"type": "json_object"}
  },
  "methods": {"language": "python"}
}
```

The Node Template is control-plane: CCN uses it to build the WorkerNode class.
It does not include method toggles or a call plan.

## Lifecycle

- CCN assigns the next `SYNAPTIC` from MEMORY (worklist) to the same Multi-Worker; no
  new instantiation is performed per Role.
- Role state is overwritten from the assigned `SYNAPTIC`; an explicit reset
  method is not required.
- Built-in methods are dispatched per the canonical plan (or a provided
  `call_plan` override). Upon completion, CCN marks the processed entry as
  completed and archives it in
  MEMORY (it remains available for inspection and auditing).
- Persistent data lives in `SYNAPTIC` entries and in CCN’s recorded outputs;
  the Multi-Worker remains effectively stateless across Roles beyond
  ephemeral in-method state.

### MEMORY Semantics

- MEMORY maintains a FIFO worklist. CCN dequeues from the head into an active
  execution slot, then archives the entry with status `completed` after the
  Role finishes (entries are not deleted).
- CCN maintains an Aggregator Buffer in MEMORY for worker outputs so the
  SYNTHESIZER can consume a single, consolidated feed.

## MEMORY Registry

MEMORY is the human-auditable record of an EPN run. It captures every input
and output for each Role, plus all CCN orchestration actions, in a friendly
and reproducible structure.

### Structure

- Worklist: pending `SYNAPTIC` entries (KV-pair lists), FIFO.
- Active Slot: the Role currently executing (materialized object snapshot).
- Archive: completed Role records with full input/output logs (never deleted).
- Aggregator Buffer: ordered list of worker outputs for the SYNTHESIZER.
- Run Log: chronological list of CCN events (bind, assign, prompt_call,
  emit-handled, enqueue, archive, errors).

### Per-Role Record (Archive) — canonical keys

```json
{
  "role_id": "REFORMULATOR",
  "synaptic_kv": [["attributes.node_id","REFORMULATOR"], ...],
  "materialized": {
    "attributes": {"input_signals": ["..."], "tasks": ["..."], ...},
    "llm_config": {"model": "openai/gpt-oss-120b", "temperature": 0.8, ...}
  },
  "binding": {
    "from": "USER_INPUT",
    "bound_to": "attributes.input_signals[0]",
    "value": "<captured query>"
  },
  "prompt_call": {
    "timestamp": "2025-09-25T10:00:00Z",
    "prompt": "... rendered prompt ...",
    "llm_config": {"model": "openai/gpt-oss-120b", "temperature": 0.8, ...},
    "response_raw": "... provider raw text/json ..."
  },
  "emit": {
    "timestamp": "2025-09-25T10:00:03Z",
    "node_output_signal": "...",
    "ccn_action": "aggregator_append | enqueue_roles | update_head"
  },
  "status": "completed",
  "durations_ms": {"prompt_call": 2750, "total": 3200}
}
```

### CCN Event (Run Log) — canonical keys

```json
{
  "ts": "2025-09-25T10:00:00Z",
  "event": "assign",
  "role_id": "ELUCIDATOR",
  "worklist_len_before": 2,
  "worklist_len_after": 1,
  "binding": {"from": "REFORMULATOR", "to": "attributes.input_signals[0]"}
}
```

Other events: "enqueue_roles" (count, role_ids), "aggregator_append"
(payload size), "archive" (role_id), "error" (message, context), and
"prompt_window" containing the prompt and raw LLM response for debugging.

### Logging Requirements

- On assign: record `assign` with bound inputs and worklist delta.
- On prompt_call: record `prompt_window` (prompt, llm_config, response_raw).
- On emit handling: record `ccn_action` taken (update/enqueue/append) and
  affected MEMORY component (worklist/archive/aggregator_buffer).
- On completion: record `archive` event and store the full Per-Role Record.

All entries must be pretty-printed JSON with stable keys for human audit and
future replay. Large prompts/responses may be stored verbatim; the Run Log can
include truncated previews for quick debugging.

### Binding Rules (Producer → Consumer)

By default, CCN binds the previous Role’s `attributes.node_output_signal` to
the next Role’s `attributes.input_signals[0]` before dispatch:

- User Input → REFORMULATOR: bind the captured user query to
  REFORMULATOR’s `input_signals[0]`.
- REFORMULATOR → ELUCIDATOR: bind the reformulated question to
  ELUCIDATOR’s `input_signals[0]`. If REFORMULATOR emits a JSON object,
  CCN extracts the value of the `reformulated_question` field for binding.
- ELUCIDATOR → Worker Roles: CCN parses ELUCIDATOR’s task list and enqueues
  one Role per task; each worker Role receives the reformulated question in
  `input_signals[0]` and task-specific instructions via `attributes.tasks`.
- Worker Roles → SYNTHESIZER: CCN appends each worker `node_output_signal` to
  the Aggregator Buffer in MEMORY for the SYNTHESIZER Role.

Advanced bindings can be expressed via `call_args` (e.g., internal targets),
but the default rule above ensures deterministic progression without requiring
workers to access MEMORY.

### Default Execution Plan and Routing (CCN)

CCN enforces a canonical execution plan and default routing per Role. If a
Synaptic entry omits `call_plan`/`call_args`, CCN applies the following:

- REFORMULATOR: plan `["prompt_call", "emit"]`, CCN records output in MEMORY.
- ELUCIDATOR: plan `["prompt_call", "emit"]`, CCN records output in MEMORY.
- Worker Role (task-specific): plan `["prompt_call", "emit"]`, CCN appends
  output to the Aggregator Buffer in MEMORY.
- SYNTHESIZER: plan `["prompt_call", "emit"]`, CCN records final output.

When `call_plan`/`call_args` are present in a Synaptic entry, CCN treats them
as explicit overrides of the canonical defaults.

## Prompt Construction

This section explains where prompt data comes from and how `build_prompt`
renders the final text sent to the LLM.

- Sources (materialized Role object)
  - `attributes.input_signals`: primary content inputs (e.g., user query or the
    reformulated question). Origin: bound by CCN from prior Role outputs stored
    in MEMORY (archive/aggregator) according to the Binding Rules.
  - `attributes.tasks`: role/task directive text (first item is the main task).
    Origin: from the Role’s SYNAPTIC KV list (MEMORY worklist entry).
  - `attributes.instructions`: newline-separated guidance string with any
    output-format constraints (e.g., JSON shape requirements). Origin: from the
    Role’s SYNAPTIC KV list (MEMORY worklist entry). If omitted, the worker
    Role is built using the Node Template default (empty string).
  - `llm_config`: model/parameters (e.g., `model`, `temperature`, `max_tokens`,
    `reasoning_effort`, `response_format`). Origin: from the Node Template with
    per‑Role overrides supplied via the SYNAPTIC KV list.

- Rendering rules (build_prompt)
  - Deterministic layout (no fallbacks): a fixed header, followed by the task,
    inputs, and instructions, each separated by one blank line.
  - Minimal layout skeleton:
    - Header: `Role: {attributes.node_id}`
    - Inputs: each `attributes.input_signals[i]` printed as `Input[i]: ...`
    - Task: `{attributes.tasks[0]}`
    - Instructions: the full `attributes.instructions` string
  - All roles MUST return strict JSON. Ensure the instructions explicitly
    require strict JSON (examples are given for REFORMULATOR and ELUCIDATOR).

- Note on defaults (design intent, not a fallback)
  - If any field is omitted in the Role’s SYNAPTIC KV list, CCN materializes
    the Role using the Node Template defaults for that field. This is by
    design: a Role is defined as “template + provided deltas”; absence means
    the template value is the Role’s value. Provide explicit values whenever
    output structure or behavior must be constrained (e.g., strict JSON
    formats) to make the contract unambiguous.

- Role output contracts (parsing)
  - REFORMULATOR: MUST return a strict JSON object with exactly one field
    `{ "reformulated_question": "<text>" }`.
    - On success: set `attributes.node_output_signal = reformulated_question`.
    - On failure (missing key/extra keys/non-JSON): fail fast and log raw body.
  - ELUCIDATOR: MUST return a strict JSON object with exactly one field
    `{ "tasks": [ ["task N", "ROLE: <ROLE_NAME>. <desc>"], ... ] }` where
    the final item is for `ROLE: SYNTHESIZER`.
    - On success: read `tasks` (array) and pass it to CCN to enqueue worker
      roles.
    - On failure: fail fast with a clear validation error and log raw body.
  - Worker roles (task-specific): MUST return a strict JSON object with a
    single field `{ "node_output_signal": "<text>" }` unless the worker’s
    template specifies a different JSON contract. CCN parses and places the
    value into `attributes.node_output_signal`.
  - SYNTHESIZER: MUST return a strict JSON object with a single field
    `{ "node_output_signal": "<text>" }` representing the final synthesis.

## LLM Invocation Guide (Groq)

Use the Groq chat completions API and pass parameters from `llm_config`.
Set `response_format={"type": "json_object"}` for ALL roles, and ensure the
prompt’s instructions explicitly require strict JSON.

- Client initialization
  - Import and instantiate the client using the API key from the environment:
    - `from groq import Groq`
    - `client = Groq(api_key=os.environ.get("GROQ_API_KEY"))`
  - Fail fast if `GROQ_API_KEY` is missing.

- Parameter mapping
  - `model` ← `llm_config.model`
  - `temperature` ← `llm_config.temperature`
  - `max_completion_tokens` (API) ← `llm_config.max_tokens`
  - `reasoning_effort` ← `llm_config.reasoning_effort`
  - `response_format` ← `llm_config.response_format` (e.g., `{"type":"json_object"}`)
  - `stream`, `stop`, `top_p` as needed (if present in `llm_config`)

- Messages
  - Provide the rendered prompt as the `user` message content.
  - Optionally add a minimal `assistant` priming turn that shows the exact JSON
    envelope expected for this Role (e.g., `{ "node_output_signal": "..." }`).

- Post-processing
  - Access the content via `completion.choices[0].message.content`.
  - Parse JSON; on parse error, fail fast and log raw body in MEMORY.
  - Extract per-role fields:
    - REFORMULATOR/Worker roles/SYNTHESIZER → set `attributes.node_output_signal`.
    - ELUCIDATOR → read the `tasks` array from the returned object and pass it
      to CCN for enqueue (no `node_output_signal` for ELUCIDATOR).

## Synaptic Format

### Built-in SYNAPTICS (KV-Pair Lists)

REFORMULATOR Role

```json
[
  ["attributes.node_id", "REFORMULATOR"],
  ["attributes.input_signals[0]", "<USER_QUERY>"],
  ["attributes.tasks[0]", "ROLE: REFORMULATOR. You are an epistemological reformulator specializing in bias elimination, epistemic contextualization, and narrative priming. Your task is to transform biased questions into neutral, epistemologically-grounded inquiries that seed a cohesive narrative arc. First step to find the truth is to formulate the right questions. Reformulate the given query"],
  ["attributes.instructions", "Neutralize biases and eliminate assumptions.\nKeep scope clear and answerable.\nOutput MUST be a JSON object with exactly one field: {\"reformulated_question\": \"<text>\"}.\nNo prose before or after the JSON.\nKeep the reformulated question under 40 words."]
]
```

ELUCIDATOR Role

```json
[
  ["attributes.node_id", "ELUCIDATOR"],
  ["attributes.input_signals[0]", "<REFORMULATOR_OUTPUT>"],
  ["attributes.tasks[0]", "ROLE: ELUCIDATOR. You are an epistemological explorer. Your goal is to generate a comprehensive set of analytical tasks that, when executed by specialized LLM nodes within a collaborative network, will extract maximum understanding from the inquiry. Discover both obvious and hidden dimensions that need investigation"],
  ["attributes.instructions", "Ensure tasks are clear, actionable, and non-overlapping.\nReturn valid JSON only.\nOutput MUST be a JSON object with exactly one field 'tasks'.\n'tasks' MUST be a JSON array (no prose before/after).\nEach array item MUST be a two-element array: ['task N', 'ROLE: <ROLE_NAME>. <concise task description>']\n<ROLE_NAME> MUST be UPPERCASE with underscores only (e.g., ANALYZER, EXPLORER, CONTEXTUALIZER, RELATION_MAPPER, SYNTHESIZER).\nThe last item MUST be ['task X', 'ROLE: SYNTHESIZER. Synthesize the collected outputs into a coherent, well-grounded answer.']\nEach task MUST be self-contained and executable by a single role when paired with the reformulated query.\nEach task description MUST end with 'RESPONSE_JSON: {\\\"node_output_signal\\\": \\\"<text>\\\"}'.\nKeep each task under 50 words."]
  ["attributes.instructions", "Select at most 4 items in total (including the final SYNTHESIZER item)."]
]
```

### Default Synaptic Format: KV-Pair List

We adopt a compact, human-readable list of key–value pairs as the default
SYNAPTIC format. Each entry is a two-element array `[key, value]` (a JSON
array representing a tuple). CCN applies the list onto the Node Template to
construct the effective Role instance before dispatch.

#### Canonical Contract (Syntax)

- Entry shape: a JSON array of pairs, e.g., `[["attributes.node_id","REFORMULATOR"], ...]`.
- Key syntax: dot-path with bracket indices for arrays.
  - Object fields: `attributes.node_id`, `attributes.instructions`, `llm_config.temperature`.
  - Array items: `attributes.tasks[0]`.
- Allowed roots: `attributes.*`, `llm_config.*`.
- Disallowed: creating unknown top-level keys; type-mismatched writes.

#### Canonical Contract (Semantics)

- Application order: left-to-right; later pairs can overwrite earlier writes.
- No auto-create: every intermediate path segment must already exist in the
  materialized object (from the Node Template or earlier pairs). Missing
  objects/arrays cause a ValidationError.
- Arrays: index must be within bounds or exactly equal to the current length
  (append). Indices greater than length are invalid (no auto-padding).
- Type checks: container types must match the path (object vs array) and final
  value types must be compatible with the Node Template.
- Minimum required fields: `attributes.node_id` must be provided.
- Defaults: if omitted, CCN fills sensible defaults from the Node Template.
- Execution control: CCN owns method sequencing and routing. Call plan/routing
  are defined by CCN defaults; SYNAPTIC lists do not need to include them.

#### Validation Rules

- Key whitelist: only the following paths (and their children) are allowed:
  - `attributes.*` (including `input_signals`, `node_output_signal`, `tasks`,
    `instructions`)
  - `llm_config.*` (e.g., `model`, `temperature`, `max_tokens`, etc.)
- Required presence: must include `attributes.node_id`. Other fields are
  optional and default to the Node Template unless a specific built‑in Role
  contract requires them (e.g., REFORMULATOR/ELUCIDATOR format constraints).
- Type checks: values must conform to the Node Template types after materialization.
- Fail-fast: any invalid key, path, or type aborts loading with a diagnostic.

#### CCN Materialization (KV → Object)

CCN materializes the KV list into a full object by:

1) Starting from the Node Template (control-plane default object)
2) Parsing each key path into segments (dot + bracket-index tokens)
3) Validating every path segment exists (no auto-create) and array index is
   within bounds or exactly at the end (append)
4) Setting the final value, with type checks against the template

Upon success, CCN validates the resulting object against the schema and then
dispatches execution using the canonical default plan and routing.

#### Aggregator Targeting

Aggregation is CCN-managed. Worker Role outputs are appended to an Aggregator
Buffer in MEMORY for the SYNTHESIZER Role. KV lists do not need to specify a
target; CCN routes outputs per its default plan.

### ELUCIDATOR Task Format (Canonical)

ELUCIDATOR must output a strict JSON object with exactly one field `tasks`.
`tasks` is a JSON array (maximum 4 items) of two-element arrays, where the
second element starts with a Role declaration followed by a concise task
description that includes (at the end) the explicit JSON response contract for
the downstream role:

```json
{
  "tasks": [
    [
      "task 1",
      "ROLE: ANALYZER. Analyze the factual foundations of ... RESPONSE_JSON: {\"node_output_signal\": \"<text>\"}"
    ],
    [
      "task 2",
      "ROLE: EXPLORER. Explore key drivers behind ... RESPONSE_JSON: {\"node_output_signal\": \"<text>\"}"
    ],
    [
      "task 3",
      "ROLE: SYNTHETIC_MAPPER. Map relations among ... RESPONSE_JSON: {\"node_output_signal\": \"<text>\"}"
    ]
  ]
}
```

Canonical rules:

- The string must begin with `ROLE: <ROLE_NAME>.` followed by free text.
- `<ROLE_NAME>` uses uppercase letters and underscores only (e.g., ANALYZER,
  EXPLORER, SYNTHETIC_MAPPER).
- Each item is self-contained: it carries all semantics needed for the worker
  to understand and execute the task when paired with the reformulated query.
- Each item’s description MUST end with a one-line response contract prefixed
  by `RESPONSE_JSON:` followed by the exact JSON object the worker must return
  (e.g., `{\"node_output_signal\": \"<text>\"}`). No prose after this object.
- The list MUST contain at most 4 items in total. The final item MUST be a
  `ROLE: SYNTHESIZER` task that instructs the synthesis step.

CCN parses this output and enqueues one worker Role per item, setting
`attributes.node_id` to `<ROLE_NAME>`, copying the description into
`attributes.tasks[0]`, and placing the reformulated query into
`attributes.input_signals[0]`. CCN reads the array from the object's
`tasks` field.

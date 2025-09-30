# CCN Minimal EPN Cycle

Template‑first, deterministic EPN (Epistemic Processing Network) cycle with a
single Multi‑Worker and strict, audit‑friendly data flow. When `templates/prompts.md`
is present, it becomes the authoritative configuration source. When absent, the system
falls back to hardcoded defaults. CCN binds inputs and orchestrates execution; workers
return strict JSON only.

## Overview

This CLI application implements a complete CCN execution cycle:

1. REFORMULATOR → reformulates the input into an epistemically sound question.
2. ELUCIDATOR → decomposes into role‑labeled items plus a final SYNTHESIZER
   directive (counts/word caps defined in templates).
3. Worker Roles → execute against the reformulated question (Input[0]) and decomposition string (Input[1]) for analytical coherence.
4. SYNTHESIZER → integrates worker outputs per the final directive.

## Features

- Single Multi‑Worker architecture with CCN role assignment
- Internal MEMORY: worklist, active slot, archive, aggregator buffer, run log
- Template‑first prompts; no hidden code fallbacks
- Template‑first LLM configuration; fail‑fast if missing
- Strict JSON envelopes; no auto‑correction of malformed JSON
- Debug windows for prompts, responses, and parameters
- Optional CCN‑dispatch (`--ccn-dispatch`) that honors `call_plan`

## Installation

### Prerequisites

- Python 3.11+
- API key for your chosen LLM provider (Groq or DeepSeek)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/ccn-ai/minimal-epn.git
cd minimal-epn
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your API key (choose one provider):

**For Groq (default):**
```bash
export GROQ_API_KEY="your-groq-api-key-here"
```

**For DeepSeek:**
```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key-here"
```

### Provider Configuration

The system supports multiple LLM providers through template configuration:

- **Groq** (default): Fast, reliable, good for production use
- **DeepSeek**: Cost-effective alternative with strong reasoning capabilities

To switch providers, modify `templates/prompts.md` or create provider-specific templates:

```markdown
## LLM_CONFIG
provider: deepseek  # or 'groq'
model: deepseek-chat
temperature: 1.0
max_tokens: 8192
response_format: json_object
```

### Alternative Installation

Install as a package:
```bash
pip install -e .
```

## Usage

When `templates/prompts.md` is present, it controls system behavior:

- **Query Override**: The `## RUN` section can override the CLI argument via `query: [Your question]`
- **Role Templates**: Each role section (REFORMULATOR, ELUCIDATOR) provides task/instruction templates
- **LLM Configuration**: The `## LLM_CONFIG` section overrides model parameters
- **Behavioral Limits**: Word counts and item limits are defined in templates

If `templates/prompts.md` is absent, the system uses hardcoded defaults from `llm_config.py`.

### Basic

```bash
python ccn_minirun.py "What are the key principles of machine learning?"
```

### Command Line Options

```bash
python ccn_minirun.py [OPTIONS] QUERY

Arguments:
  QUERY  The input question (used unless templates/RUN.query overrides it)

Options:
  -d, --debug          Enable debug mode with verbose output
  -s, --strict         Enable strict mode (fail on validation errors)
  -o, --output PATH    Output file for results
  --validate-only      Only validate setup without executing
  --ccn-dispatch       Dispatch built-in steps in CCN (honor call_plan)
  --help              Show this message and exit
```

### Examples

#### Simple Query
```bash
python ccn_minirun.py "Explain quantum computing in simple terms"
```

#### Debug Mode
```bash
python ccn_minirun.py -d "What is the future of AI?"
```

#### Save Results
```bash
python ccn_minirun.py -o results.json "Analyze the benefits of renewable energy"
```

#### Strict Validation
```bash
python ccn_minirun.py -s "Describe the water cycle"
```

#### CCN Dispatch (advanced)
```bash
python ccn_minirun.py --ccn-dispatch "Explain quantum computing"
```
This mode makes CCN dispatch `prompt_call` → `emit` and honor `call_plan`.

## Architecture

### Core Components

1. **ccn_minirun.py** - CLI entrypoint and main execution loop
2. **mini_memory.py** - MEMORY dataclasses and data structures
3. **mini_synaptic.py** - KV parser and materializer with strict validation
4. **worker_node.py** - WorkerNode class with LLM interaction
5. **mini_ccn.py** - CCN orchestrator with execution loop
6. **llm_client.py** - Groq API wrapper

### Data Flow

```
templates/prompts.md (if present) → authoritative configuration
        ↓
User/Template Query → REFORMULATOR → reformulated_question (JSON)
        ↓
ELUCIDATOR → query_decomposition (JSON; item count per template)
        ↓
Worker Roles → node_output_signal (JSON; Input[1]=reformulated_question, Input[2]=decomposition string)
        ↓
SYNTHESIZER → node_output_signal (JSON)
```

### Template Behavior When Present/Absent

**When `templates/prompts.md` exists:**
- **Query Override**: `## RUN` section's `query: [...]` overrides CLI arguments
- **Role Instructions**: Task and instruction sections override hardcoded defaults
- **LLM Parameters**: `## LLM_CONFIG` section overrides default model settings (missing parameters fall back to defaults)
- **Limits & Constraints**: Word counts and item limits defined in templates
- **Graceful Fallbacks**: Missing template sections use hardcoded defaults

**When `templates/prompts.md` is absent:**
- **Hardcoded Defaults**: System uses defaults from `llm_config.py`
- **Default Parameters**: model=`openai/gpt-oss-120b`, temperature=`0.8`, etc.
- **Default Limits**: REFORMULATOR (≤40 words), workers (≤70), SYNTHESIZER (≤140)
- **ELUCIDATOR Items**: Limited to 4 total items (including SYNTHESIZER)
- **No Override**: CLI arguments are always used for query input

### MEMORY Structure

- **worklist**: Deque of SYNAPTIC KV lists awaiting execution
- **active_slot**: Currently executing role
- **archive**: Historical execution records
- **aggregator_buffer**: Collection of worker outputs
- **run_log**: Chronological event log

### Built‑in Roles

- REFORMULATOR → `{ "reformulated_question": "<text>" }`
- ELUCIDATOR → `{ "query_decomposition": [["label","ROLE: <ROLE_NAME>. <desc> ..."], ...] }`
- Worker roles → `{ "node_output_signal": "<text>" }`
- SYNTHESIZER → `{ "node_output_signal": "<text>" }`

## Configuration

### LLM Parameters

**Template-Authoritative Configuration:**
When `templates/prompts.md` exists, the `## LLM_CONFIG` section is the sole source for:

- `model`
- `temperature`
- `max_tokens`
- `reasoning_effort`
- `response_format` (e.g., `json_object`)

**Fallback Defaults (when templates absent):**
- model: `openai/gpt-oss-120b`
- temperature: `0.8`
- max_tokens: `8192`
- reasoning_effort: `medium`
- response_format: `{ "type": "json_object" }`

**Configuration Rules:**
- If template file exists but lacks `LLM_CONFIG`, system falls back to hardcoded defaults
- Template role sections (REFORMULATOR, ELUCIDATOR) override hardcoded instructions
- LLM parameters merge: template values override defaults, missing values use defaults
- Hardcoded defaults used when template file is absent or specific sections are missing
- Template changes take immediate effect (no code changes needed)

### Environment Variables

- `GROQ_API_KEY` (required): Your Groq API key

## Debug Mode

Enable debug mode with `-d` flag to see:
- Context snapshots
- Prompt construction
- LLM parameters
- Raw JSON responses
- MEMORY mutations

## Validation

### Strict Mode

The `--strict` flag enables strict validation:
- Validates SYNAPTIC KV pairs against whitelist
- Enforces JSON schema compliance
- Validates archive records against schema
- Fails fast on validation errors

### Archive Validation

Archive records are validated against `schemas/memory_record.schema.json`.
Use `--strict` to make validation errors fatal.

## Error Handling

The implementation follows fail-fast principles:
- Missing API key → Immediate failure
- Invalid SYNAPTIC format → Validation error
- LLM call failure → Error event + continuation (workers) or failure (core roles)
- JSON parse error → Error event + raw body logging

## Output Formats

### Console Output

Rich formatted output with:
- Execution progress
- Final synthesis in panels
- Debug information (when enabled)
- Execution summary

### JSON Output

When using `--output` flag:
```json
{
  "query": "original user query",
  "result": "final synthesis",
  "summary": {
    "archive_size": 5,
    "events_count": 12,
    "aggregator_size": 3,
    "roles_executed": ["REFORMULATOR", "ELUCIDATOR", "WORKER_1", "SYNTHESIZER"]
  },
  "archive": [...],
  "events": [...]
}
```

## Development

### Project Structure
```
EPN/
├── AGENTS.md               # Agent implementation constraints & notes
├── ccn_minirun.py          # CLI entrypoint
├── demo_ccn.py             # Interactive/demo runner
├── example_usage.py        # Usage examples / quickstart snippets
├── md/                     # Documentation files
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── conceptualization.md
│   └── ...
├── template_loader.py      # Template parsing / binding helpers
├── llm_client.py           # Groq API wrapper
├── llm_config.py           # Hardcoded defaults and config helpers
├── mini_memory.py          # MEMORY dataclasses and structures
├── mini_synaptic.py        # SYNAPTIC KV parser & materializer
├── mini_ccn.py             # CCN orchestrator
├── worker_node.py          # Worker execution and role logic
├── test_ccn.py             # Test harness / unit tests
├── requirements.txt
├── setup.py
├── README.md
├── schemas/
│   └── memory_record.schema.json
├── templates/
│   └── prompts.md
├── scripts/
│   └── live_prompt_capture.py
├── reports/                # Generated run reports
└── __pycache__/
```

### Adding New Roles

1. Create Node Template in `mini_synaptic.py`
2. Add role-specific validation in `worker_node.py`
3. Update binding rules in `mini_ccn.py`
4. Add schema validation if needed

### Testing

Basic validation:
```bash
python ccn_minirun.py --validate-only
```

Test execution:
```bash
python ccn_minirun.py -d "Test query"
```

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure `GROQ_API_KEY` is set
   - Verify key is valid and has credits

2. **JSON Parse Error**
   - Enable debug mode to see raw responses
   - Check LLM response format

3. **Validation Errors**
   - Use strict mode for detailed validation
   - Check SYNAPTIC KV format

4. **Execution Hangs**
   - Check API rate limits
   - Enable debug mode for detailed logging

### Debug Tips

- Use `-d` flag for verbose output
- Check `run_log` for event sequence
- Review `archive` for execution history
- Validate setup with `--validate-only`

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Enable debug mode for detailed logs
- Review the implementation against the mvp.md specification

## Testing The App

1) Validate environment and client:
   ```bash
   python ccn_minirun.py --validate-only "test query"
   ```

2) Run a live capture (writes a full report under `reports/`):
   ```bash
   python scripts/live_prompt_capture.py "Why are models useful despite being wrong?"
   ls -1 reports/ | head -n 3
   ```

   Inspect the latest report and confirm:
   - Prompts match `templates/prompts.md`
   - Worker Inputs include the length cap inside the decomposition string
   - SYNTHESIZER prompt begins with the ELUCIDATOR directive

3) Use the template‑provided query instead of CLI:
   - Edit `templates/prompts.md` → `## RUN` → `query: [Your question]`
   - Re‑run `python scripts/live_prompt_capture.py`
   - The report shows the template query in the header

4) Test template-driven behavior:
   - Remove `templates/prompts.md` temporarily
   - Run the system and observe it uses hardcoded defaults
   - Restore the file and observe template-authoritative behavior returns

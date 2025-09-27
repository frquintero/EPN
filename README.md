# CCN Minimal EPN Cycle

A minimal, operable EPN (Execution Plan Network) cycle implementation with live Groq calls for the CCN (Cognitive Compute Network) framework.

## Overview

This CLI application implements a complete CCN execution cycle with the following phases:

1. **REFORMULATOR** - Reformulates user input into clear, actionable questions
2. **ELUCIDATOR** - Breaks down questions into specific tasks (max 4 items)
3. **Worker Roles** - Executes individual tasks in parallel
4. **SYNTHESIZER** - Combines all results into a coherent final response

## Features

- ✅ **Single Multi-Worker** architecture with CCN role assignment
- ✅ **Internal MEMORY** management (worklist, active slot, archive, aggregator buffer, run log)
- ✅ **JSON-only outputs** with strict parsing and validation
- ✅ **Debug windows** for context snapshots, prompts, and responses
- ✅ **Built-in roles**: REFORMULATOR, ELUCIDATOR, SYNTHESIZER
- ✅ **Groq integration** with configurable LLM parameters
- ✅ **Fail-fast** error handling with human-auditable logs

## Installation

### Prerequisites

- Python 3.11+
- Groq API key

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

3. Set your Groq API key:
```bash
export GROQ_API_KEY="your-api-key-here"
```

### Alternative Installation

Install as a package:
```bash
pip install -e .
```

## Usage

### Basic Usage

```bash
python ccn_minirun.py "What are the key principles of machine learning?"
```

### Command Line Options

```bash
python ccn_minirun.py [OPTIONS] QUERY

Arguments:
  QUERY  The input question or task to process

Options:
  -d, --debug          Enable debug mode with verbose output
  -s, --strict         Enable strict mode (fail on validation errors)
  -o, --output PATH    Output file for results
  --validate-only      Only validate setup without executing
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
User Input
    ↓
REFORMULATOR → Reformulated Question
    ↓
ELUCIDATOR → Task List (max 4 items)
    ↓
Worker Roles → Individual Results
    ↓
SYNTHESIZER → Final Synthesis
```

### MEMORY Structure

- **worklist**: Deque of SYNAPTIC KV lists awaiting execution
- **active_slot**: Currently executing role
- **archive**: Historical execution records
- **aggregator_buffer**: Collection of worker outputs
- **run_log**: Chronological event log

### Built-in Roles

#### REFORMULATOR
- **Purpose**: Clarify and reformulate user input
- **Output**: `{"reformulated_question": "<text>"}`

#### ELUCIDATOR  
- **Purpose**: Break down complex questions into actionable tasks
- **Output**: `{"tasks": [["task N", "ROLE: <NAME>. <desc> RESPONSE_JSON: {...}"], ...]}`
- **Limit**: Maximum 4 tasks (including SYNTHESIZER)

#### SYNTHESIZER
- **Purpose**: Combine all worker outputs into final response
- **Output**: `{"node_output_signal": "<text>"}`

## Configuration

### LLM Parameters

Default configuration for all roles:
```python
{
    "model": "openai/gpt-oss-120b",
    "temperature": 0.8,
    "max_tokens": 8192,
    "reasoning_effort": "medium",
    "response_format": {"type": "json_object"}
}
```

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
ccn-minimal-epn/
├── ccn_minirun.py          # CLI entrypoint
├── mini_memory.py          # MEMORY structures
├── mini_synaptic.py        # KV parser/materializer
├── worker_node.py          # Worker execution
├── mini_ccn.py             # CCN orchestrator
├── llm_client.py           # Groq wrapper
├── schemas/
│   └── memory_record.schema.json
├── requirements.txt
├── setup.py
└── README.md
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

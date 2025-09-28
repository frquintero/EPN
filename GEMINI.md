# GEMINI.md - Project Overview

## Project Overview

This project is a Python-based command-line application that implements a "CCN" (Epistemic Processing Network) cycle. It's an AI agentic workflow that processes a user's query through a series of steps:

1.  **REFORMULATOR:** Reformulates the input query into a more epistemically sound question.
2.  **ELUCIDATOR:** Decomposes the reformulated question into a series of role-labeled tasks for worker agents.
3.  **Worker Roles:** Execute the tasks defined by the ELUCIDATOR.
4.  **SYNTHESIZER:** Integrates the outputs from the worker roles into a final, synthesized response.

The application is designed to be "template-first," meaning its behavior is primarily controlled by the `templates/prompts.md` file. This file defines the prompts, instructions, and even the LLM configuration for each step in the cycle. When this file is absent, the application falls back to hardcoded defaults.

The core of the application is built around a few key components:

*   `ccn_minirun.py`: The main command-line interface (CLI) entry point.
*   `mini_ccn.py`: The orchestrator that manages the execution of the CCN cycle.
*   `worker_node.py`: The component responsible for interacting with the LLM (via the Groq API).
*   `mini_memory.py`: Defines the data structures for managing the state of the CCN cycle.
*   `mini_synaptic.py`: Handles the parsing and validation of the data structures used throughout the application.
*   `llm_client.py`: A wrapper for the Groq API client.
*   `llm_config.py`: Provides default LLM configurations.

The project uses the Groq API for its LLM capabilities and relies on a few key Python libraries, including `click` for the CLI, `rich` for formatted console output, and `jsonschema` for data validation.

## Building and Running

### Prerequisites

*   Python 3.11+
*   A Groq API key

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ccn-ai/minimal-epn.git
    cd minimal-epn
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set your Groq API key:**
    ```bash
    export GROQ_API_KEY="your-api-key-here"
    ```

### Running the Application

The main entry point for the application is `ccn_minirun.py`. You can run it with a query as follows:

```bash
python ccn_minirun.py "What are the key principles of machine learning?"
```

The application also provides several command-line options for debugging, strict validation, and saving the output to a file.

### Testing

The project includes a simple validation command to check the setup:

```bash
python ccn_minirun.py --validate-only "test query"
```

There is also a `live_prompt_capture.py` script for running a live capture of the prompts and responses, which can be useful for debugging and development.

## Development Conventions

The project follows a modular structure, with clear separation of concerns between the different components. The code is well-documented with docstrings, and the `README.md` file provides a comprehensive overview of the project's architecture and usage.

The use of a "template-first" approach is a key convention. This means that changes to the application's behavior should, whenever possible, be made in the `templates/prompts.md` file rather than in the code itself. This allows for rapid iteration and experimentation with different prompts and instructions.

The project also includes a `setup.py` file, which allows it to be installed as a package. This is useful for distribution and for integrating the application into other projects.

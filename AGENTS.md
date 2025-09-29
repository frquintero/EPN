# Agent Implementation Constraints

Mandatory Runtime-Error Reporting Rule:

- When an agent (developer) encounters a bug, exception, or any
  `RuntimeError` during development or while running the pipeline, the
  agent must, before applying code changes, do the following and include
  the results in the commit/PR description or in an accompanying note:
  1. **Diagnosis:** Briefly explain what the root cause is
    (one or two sentences). This should include which module or
    function likely triggered the error and why, based on observed
    symptoms (stack trace, failing inputs, or missing state).
  2. **Proposed Fix:** Describe the minimal, surgical change that will
    address the root cause. Avoid adding broad fallbacks or hiding the
    failure; prioritize a change that makes the failure explicit or
    corrects the underlying state transition.
  3. **Verification Plan:** State the test or logging change you will
    add to prove the fix removes the issue (unit test name, scenario, or
    log message to assert the earlier failure no longer occurs).

  This diagnostic step is mandatory and should be visible in PRs. It
  ensures failures are understood and fixed at the root rather than
  masked.

## Setup & Environment

Activate the bundled virtual environment with `source venv/bin/activate` before running tools. Load credentials from `~/.config/env.d/ai.env`, ensuring it exports `GROQ_API_KEY=gsk_...`; confirm with `echo $GROQ_API_KEY`. Keep `.env`-style files untracked and rely on environment variables when writing scripts or tests that reach the Groq API.

## Coding Style & Naming Conventions

Follow PEP 8 with 4-space indentation and the repository-wide 88-character line limit. Modules and functions should use snake_case, while agent classes end with `Agent` or `Node`. Format code with `black .` and `isort .`, lint with `flake8`, and type-check non-trivial orchestrations using `mypy` prior to review.

## Commit & Pull Request Guidelines

Keep commits focused with concise, Title Case subject lines (emojis optional, as reflected in `🧹 Major cleanup and documentation update`). Reference issues in the body when relevant. Pull requests should explain context, outline changes, list validation commands (tests, linting), and attach CLI output snippets when behaviour shifts. Obtain maintainer review and wait for CI to pass before merging.

## Security & Configuration Tips

Never commit API keys or local environment files. When writing integration tests, guard external calls behind environment checks or provide mock responses. Rotate credentials promptly if exposure is suspected.

## Docs Index (brief)

The repository keeps user-facing and design documentation under `docs/` (except `AGENTS.md` which stays at the project root). Below is a short index of the important Markdown files and their purpose:

If you add or move documentation, please update this index so the next maintainer can find key files quickly.

## Formatting Note

- **Always convert Markdown headings to ATX style (`# Heading`)** to satisfy the repository linter and keep consistency across documentation.

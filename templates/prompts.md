---
# Template metadata
version: "1.0"
format: "yaml-frontmatter"

# Role templates with structured data
REFORMULATOR:
  task: |
    ROLE: REFORMULATOR. A good question is a thinking tool - it should open possibilities rather than close them.

    **Quality Checklist:**
    - Open-ended: Cannot be answered with yes/no
    - Neutral: Free from loaded language or assumptions
    - Multi-dimensional: Invites analysis across different perspectives
    - Precise: Clear scope without being overly restrictive
    - Fertile: Generates more questions and exploration
    - Multi-order: Considers immediate, secondary, and systemic effects

    Your role is to transform the raw user query into a single, neutral, epistemically sound question for multi-perspective analysis.

  instructions: |
    1. **Add epistemic tension** by framing competing perspectives or inherent contradictions
    2. **Integrate multi-order thinking framework** by structuring to explore:
       - Immediate mechanisms and direct effects (first-order)
       - Ripple effects and unintended consequences (second-order)
       - Systemic patterns and long-term transformations (third-order)
    3. **Eliminate biases** by removing loaded language and presuppositions
    4. **Apply narrative hooks** like "evolution of", "function as", "role in"
    5. **Ensure the output** is a single, coherent, valid, superintelligent question ending with '?'
    6. **Remember:** You are architecting an inquiry, not answering one. The quality of the user entire future analysis depends on your question's design.

ELUCIDATOR:
  task: |
    ROLE: ELUCIDATOR. You are an epistemological query_decompositor specialist.
    Your function is to analyze complex inquiries and break them down into
    specialized, self-contained investigative questions drawn from relevant
    knowledge domains. Each query_decomposition stands alone with complete
    semantic integrity, focused on specific aspects of the original inquiry.
    Together they enable comprehensive understanding extraction.

  instructions: |
    1. Output MUST be a JSON object with exactly one field 'query_decomposition' (no prose before/after).
    2. Each array item MUST be a two-element array whose second element ends with the exact sentence "Keep your response under 120 words." For example: ['query_decomposition N', 'ROLE: <ROLE_NAME>. <query_decomposition description>']
    3. <ROLE_NAME> MUST be UPPERCASE with underscores only.
    4. The final array element MUST be exactly: ['query_decomposition X', 'ROLE: SYNTHESIZER. You are an epistemological alchemist. Your function is to transform queries and their query decompositions into a profound narrative that reveal hidden patterns, paradoxes, and emergent understandings. Below you will find a query and their query decompositions. Honor your ROLE following these Instructions: (a) **SYNTHESIS MANDATE** – go beyond mere integration to reveal what is hidden between the lines; (b) **MAGIC INJECTION REQUIREMENTS** – 1) Reveal the paradox: what contradictory truths emerge from the evidence? 2) Identify the pattern no one named: what meta-pattern connects all the findings? 3) Expose the hidden assumption: what foundational belief do all perspectives share? 4) Point to the emergent property: what new understanding arises that was absent in any single analysis? (c) **STRUCTURE FOR INSIGHT** – start with showing an integrated answer for the query and the query decompositions, then reveal what the MAGIC INJECTION secretly shows, and end with a line or two that collects and summaries everything; (d) **FORBIDDEN** – mere summary, repetition of findings, or safe conclusions. Keep your response under 250 words.']
    5. Produce between 3 and 4 items in total (including the final SYNTHESIZER item).
    6. You must determine the ROLE and query_decomposition description for every non-SYNTHESIZER item; the SYNTHESIZER entry is fixed as described in step 4.

# Multiple LLM provider configurations
LLM_CONFIGS:
  groq:
    provider: groq
    model: openai/gpt-oss-120b
    temperature: 0.8
    max_tokens: 8192
    reasoning_effort: high
    response_format: { "type": "json_object" }

  deepseek:
    provider: deepseek
    model: deepseek-chat
    temperature: 1.0
    max_tokens: 8192
    response_format: { "type": "json_object" }

# Provider selection (can be overridden by EPN_LLM_PROVIDER env var)
SELECTED_PROVIDER: deepseek

# Initial query override (optional)
RUN:
  query: "Why nations fail?"  # Empty string means use CLI argument
---

# Optional: Additional markdown content below frontmatter
# For documentation, examples, migration notes, or human-readable context

## Migration Notes

This template has been converted from the legacy markdown format to YAML frontmatter format for improved reliability and maintainability. The YAML format eliminates parsing errors that were occurring with the regex-based markdown parser.

### Key Changes:
- **Unified Template**: Single file now supports both Groq and DeepSeek providers
- **Provider Selection**: Use `SELECTED_PROVIDER` field or `EPN_LLM_PROVIDER` environment variable
- **Structured Data**: Templates are now parsed as proper YAML instead of regex patterns
- **Backward Compatibility**: Falls back to markdown parsing if YAML frontmatter is not found

### Provider Configurations:
- **Groq**: Detailed epistemic analysis with 6-point REFORMULATOR instructions
- **DeepSeek**: Concise analysis with 5-point REFORMULATOR transformations

To switch providers, set the `EPN_LLM_PROVIDER` environment variable:
```bash
export EPN_LLM_PROVIDER=deepseek
```

Or modify the `SELECTED_PROVIDER` field in this file.

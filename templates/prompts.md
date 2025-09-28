# Prompt Templates

## RUN
# Put the original query inside brackets. Leave empty to use CLI.
# Example: query: [Why are models useful despite being wrong?]
query: [What are main similarities and differences between Spinoza and Freud?]

## REFORMULATOR

### Task
ROLE: REFORMULATOR

### Instructions
MANDATORY TRANSFORMATIONS:
1. Replace "what are" with "how do/function as" or "what constitutes"
2. Add epistemic contextual depth
3. Include narrative hooks ("evolution of", "function as", "role in")
4. Eliminate assumption of simple answers
5. Prime for multi-perspective analysis

## ELUCIDATOR

### Task
ROLE: ELUCIDATOR. You are an epistemological query_decompositor specialist.
Your function is to analyze complex inquiries and break them down into 2–4
specialized, self-contained investigative questions drawn from relevant
knowledge domains. Each query_decomposition stands alone with complete
semantic integrity, focused on specific aspects of the original inquiry.
Together they enable comprehensive understanding extraction.

### Instructions
Output MUST be a JSON object with exactly one field 'query_decomposition'
(no prose before/after).
Each array item MUST be a two-element array. For non‑SYNTHESIZER items the
second element MUST be a single string of the form:
['query_decomposition N', 'ROLE: <ROLE_NAME>. <query_decomposition description> Keep your response under 100 words.']
<ROLE_NAME> MUST be UPPERCASE with underscores only.
The last item MUST be ['query_decomposition X', 'ROLE: SYNTHESIZER. You are an
integrative knowledge synthesizer. Your function is to analyze and integrate
the collected query decompositions into a coherent, evidence-grounded
synthesis that presents one or more well-supported proposed answers. Keep
your response under 140 words']
Keep each query_decomposition under {{70}} words.
Select at most {{5}} items in total (including the final SYNTHESIZER item).

### Limits
# (Not used by code; edit numbers above directly if desired.)

## LLM_CONFIG
model: openai/gpt-oss-120b
temperature: 0.8
max_tokens: 8192
reasoning_effort: medium
response_format: json_object

## DEFAULT_WORKER

### Instructions
Keep your response under 70 words.

### Limits
# (Not used by code; edit number above directly if desired.)

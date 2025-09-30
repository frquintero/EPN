# Implementation Plan: Markdown with YAML Frontmatter for Template Parsing

## Overview

Replace fragile markdown parsing with robust YAML frontmatter parsing to eliminate parsing errors and improve maintainability.

## Current Issues

- Parsing fails on minor formatting variations (e.g., `### Instructions:` vs `### Instructions`)
- REFORMULATOR instructions not being included in prompts due to parsing bug
- Error-prone manual markdown structure maintenance
- No validation of template structure

## Solution: YAML Frontmatter Format

### New Template Structure

Two template files will be converted to YAML frontmatter format:

#### templates/prompts.md (Groq Configuration)
```markdown
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
    2. Each array item MUST be a two-element array whose second element ends with the exact sentence "Keep your response under 120 words."
    3. <ROLE_NAME> MUST be UPPERCASE with underscores only.
    4. The final array element MUST be exactly: [SYNTHESIZER definition with magic injection requirements]
    5. Produce between 3 and 4 items in total (including final SYNTHESIZER item).
    6. You must determine the ROLE and query_decomposition description for every non-SYNTHESIZER item.

# LLM configuration
LLM_CONFIG:
  provider: groq
  model: openai/gpt-oss-120b
  temperature: 0.8
  max_tokens: 8192
  reasoning_effort: high
  response_format: { "type": "json_object" }

# Initial query override (optional)
RUN:
  query: "Why nations fail?"
---

# Optional: Additional markdown content below frontmatter
# For documentation, examples, or migration notes
```

#### templates/prompts_deepseek.md (DeepSeek Configuration)
```markdown
---
# Template metadata
version: "1.0"
format: "yaml-frontmatter"

# Role templates with structured data
REFORMULATOR:
  task: |
    ROLE: REFORMULATOR

  instructions: |
    MANDATORY TRANSFORMATIONS:
    1. **ELIMINATE "what are" completely** - use "how does", "in what ways", "to what extent"
    2. **Add epistemic tension** - frame as exploration of paradox or mystery
    3. **Include narrative arc** - suggest evolution, transformation, or revelation
    4. **Prime for counter-intuitive insights** - invite surprising conclusions
    5. **Keep under 40 words**

ELUCIDATOR:
  task: |
    ROLE: ELUCIDATOR. You are an epistemological query_decompositor specialist.
    Your function is to analyze complex inquiries and break them down into
    specialized, self-contained investigative questions drawn from relevant
    knowledge domains. Each query_decomposition stands alone with complete
    semantic integrity, focused on specific aspects of the original inquiry.
    Together they enable comprehensive understanding extraction.

  instructions: |
    1. Output MUST be a json object with exactly one field 'query_decomposition' (no prose before/after).
    2. Each array item MUST be a two-element array whose second element ends with the exact sentence "Keep your response under 120 words."
    3. <ROLE_NAME> MUST be UPPERCASE with underscores only.
    4. The final array element MUST be exactly: [SYNTHESIZER definition with magic injection requirements]
    5. Produce between 3 and 4 items in total (including the final SYNTHESIZER item).
    6. You must determine the ROLE and query_decomposition description for every non-SYNTHESIZER item; the SYNTHESIZER entry is fixed as described in step 4.

# LLM configuration
LLM_CONFIG:
  provider: deepseek
  model: deepseek-chat
  temperature: 1.0
  max_tokens: 8192
  response_format: { "type": "json_object" }

# Initial query override (optional)
RUN:
  query: "Why is there something instead of nothing?"
---

# Optional: Additional markdown content below frontmatter
# For documentation, examples, or migration notes
```

## Implementation Phases

### Phase 1: Infrastructure Setup

#### 1.1 Update Dependencies
**File:** `requirements.txt`
- Add: `PyYAML>=6.0`

#### 1.2 Create New Template Loader
**File:** `template_loader.py` (complete rewrite)

**Key Changes:**
- Implement YAML frontmatter detection and parsing
- Add schema validation for template structure
- Update `RoleTemplate` dataclass to include metadata if needed
- Add comprehensive error handling with clear messages

**New Methods:**
```python
def _parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter and remaining content. Raises ValueError on parse errors."""

def _validate_template_structure(frontmatter: Dict) -> None:
    """Validate required fields and structure. Raises ValueError on validation failures."""

def _load_from_frontmatter(self, frontmatter: Dict) -> None:
    """Load templates from validated YAML frontmatter."""
```

### Phase 2: Template Migration

#### 2.1 Convert prompts.md
**File:** `templates/prompts.md`
- Convert from markdown sections to YAML frontmatter
- Preserve all existing content in structured format
- Add version metadata

#### 2.2 Convert prompts_deepseek.md
**File:** `templates/prompts_deepseek.md`
- Convert to YAML frontmatter format
- Include DeepSeek-specific configurations
- Maintain all existing REFORMULATOR transformations

### Phase 3: Integration Updates

#### 3.1 Update Worker Node
**File:** `worker_node.py`
- No changes needed - interface unchanged
- Templates loaded from new format automatically

#### 3.2 Update CCN Components
**Files:** `mini_ccn.py`, `ccn_minirun.py`
- No changes needed - template loading interface unchanged
- Automatically use new parsing logic

### Phase 4: Testing & Validation

#### 4.1 Add Comprehensive Tests
**File:** `test_ccn.py` (extend existing tests)
- Test YAML frontmatter parsing
- Test template validation
- Test error handling for malformed templates
- Test both Groq and DeepSeek configurations

#### 4.2 Integration Testing
- Verify end-to-end prompt construction
- Test LLM calls with new format
- Validate all existing functionality works

## Files to Modify

### Core Files
1. `requirements.txt` - Add PyYAML dependency
2. `template_loader.py` - Complete rewrite for YAML frontmatter parsing
3. `templates/prompts.md` - Convert to YAML frontmatter format
4. `templates/prompts_deepseek.md` - Convert to YAML frontmatter format

### Test Files
5. `test_ccn.py` - Add YAML frontmatter parsing tests

### No Changes Needed
- `worker_node.py` - Interface unchanged
- `mini_ccn.py` - Interface unchanged
- `ccn_minirun.py` - Interface unchanged

## Migration Strategy

Convert all templates to YAML frontmatter format simultaneously. Update code to use YAML frontmatter parsing exclusively.

## Error Handling

### Template Validation
- **YAML Parse Errors**: Clear messages indicating syntax issues
- **Missing Required Fields**: Specific field validation with helpful messages
- **Invalid Structure**: Schema validation for expected structure
- **Version Mismatches**: Future-proofing for format evolution

### Runtime Safety
- Template loading failures fall back to hardcoded defaults
- Clear logging of template issues
- Graceful degradation when templates unavailable

## Success Criteria

- ✅ All existing functionality works with new format
- ✅ REFORMULATOR instructions properly included in prompts
- ✅ Clear error messages for template issues
- ✅ Both Groq and DeepSeek configurations supported
- ✅ All tests pass
- ✅ Template editing is more reliable and user-friendly

## Risk Mitigation

- **Comprehensive Testing**: Full test coverage before deployment
- **Validation**: Template validation catches issues early
- **Error Handling**: Clear error messages aid troubleshooting
- **Documentation**: Updated docs for new format

## Timeline

1. **Phase 1**: 2-3 hours (infrastructure)
2. **Phase 2**: 1-2 hours (template conversion)
3. **Phase 3**: 30 minutes (integration verification)
4. **Phase 4**: 2-3 hours (testing & validation)

Total estimated time: 6-8 hours</content>
<parameter name="filePath">/run/media/fratq/4593fc5e-12d7-4064-8a55-3ad61a661126/CODE/EPN/YAML_FRONTMATTER_IMPLEMENTATION_PLAN_UPDATED.md
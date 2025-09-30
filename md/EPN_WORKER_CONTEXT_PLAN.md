# EPN Worker Context Enhancement Plan

## Problem Statement

Currently, the EPN (Epistemic Processing Network) system has an architectural inconsistency in how contextual information flows to different roles:

- **REFORMULATOR** produces a reformulated question that establishes the analytical framework
- **ELUCIDATOR** receives this reformulated question and creates worker role definitions
- **Workers** (spawned roles like DIRECT_ANALYST, EFFECTS_EXAMINER, META_ANALYST) only receive their specific role descriptions, missing the broader analytical context
- **SYNTHESIZER** correctly receives the reformulated question as primary input alongside worker outputs

This creates a gap where workers lack awareness of the multi-level analytical framework established by the REFORMULATOR, potentially leading to less coherent and contextually aligned analysis.

## Current Data Flow

```
User Query → REFORMULATOR → Reformulated Question
                              ↓
                    ELUCIDATOR (receives reformulated question)
                              ↓
                    Creates Worker Specifications
                              ↓
Workers ←───── Role Description Only (MISSING: Reformulated Question)
                              ↓
SYNTHESIZER ←── Reformulated Question + Worker Outputs
```

## Proposed Solution

Modify the worker binding logic to include the reformulated question as contextual input, ensuring all roles in the processing pipeline have access to the established analytical framework.

## Implementation Plan

### Phase 1: Core Logic Changes

#### 1.1 Update Worker Binding Logic (`mini_ccn.py`)
**File:** `mini_ccn.py`
**Method:** `bind_inputs()`
**Current Code:**
```python
if source_role == 'ELUCIDATOR' and target_role.node_id != 'SYNTHESIZER':
    # ... existing parsing ...
    target_role.input_signals = [spec['raw_text']]  # Only role description
```

**Proposed Code:**
```python
if source_role == 'ELUCIDATOR' and target_role.node_id != 'SYNTHESIZER':
    # ... existing parsing ...
    # Include reformulated question as context for workers
    inputs = [spec['raw_text']]  # Role description
    if isinstance(self.reformulated_question, str) and self.reformulated_question:
        inputs = [self.reformulated_question] + inputs  # Prepend reformulated question
    target_role.input_signals = inputs
```

**Impact:** Workers will receive `Input[1]` = reformulated question, `Input[2]` = role description

### Phase 2: Template Updates

#### 2.1 Update ELUCIDATOR Instructions (`templates/prompts.md`)
**File:** `templates/prompts.md`
**Section:** `## ELUCIDATOR`
**Current:** Workers are instructed to focus on their specific role descriptions
**Proposed:** Add instruction that workers will receive the reformulated question as analytical context

**Specific Change:** Update the ELUCIDATOR instructions to mention that spawned workers will receive the reformulated question as their first input for contextual awareness.

### Phase 3: Testing and Validation

#### 3.1 Functional Testing
- Run `live_prompt_capture.py` with the updated system
- Verify workers receive reformulated question in their prompts
- Check that worker outputs demonstrate improved contextual alignment
- Ensure SYNTHESIZER continues to function correctly

#### 3.2 Regression Testing
- Verify existing functionality remains intact
- Check that worker role definitions still work as expected
- Validate that the change doesn't break the JSON parsing or role execution flow

#### 3.3 Output Quality Assessment
- Compare worker outputs before/after the change
- Assess whether workers better align with the multi-level analytical framework
- Evaluate coherence across all worker contributions

### Phase 4: Documentation Updates

#### 4.1 Update README.md
**File:** `README.md`
**Section:** Architecture/Data Flow
**Change:** Update the data flow diagram to reflect that workers now receive the reformulated question

#### 4.2 Update AGENTS.md
**File:** `AGENTS.md`
**Section:** Provider Abstraction Architecture or relevant section
**Change:** Document the improved contextual flow for worker roles

## Expected Benefits

1. **Improved Analytical Coherence:** Workers will better understand the multi-level analytical framework
2. **Enhanced Context Awareness:** Workers can reference the reformulated question's structure in their analysis
3. **Better Synthesis Input:** SYNTHESIZER receives more contextually aligned worker outputs
4. **Maintained Epistemological Integrity:** All roles operate within the same analytical paradigm

## Risk Assessment

### Low Risk Changes
- Worker binding logic change is isolated and follows existing SYNTHESIZER pattern
- Template update is additive (informational) rather than functional
- No changes to core parsing or execution logic

### Potential Issues
- Workers may need to adjust their response strategies when receiving additional context
- Slight increase in prompt length (reformulated question prepended)
- Need to ensure backward compatibility with existing worker role definitions

## Rollback Plan

If issues arise:
1. Revert the `bind_inputs()` method change in `mini_ccn.py`
2. Restore original ELUCIDATOR template instructions
3. Revert documentation changes

## Success Criteria

- [ ] Workers receive reformulated question in their input signals
- [ ] Worker prompts clearly show the analytical context
- [ ] Worker outputs demonstrate improved alignment with the analytical framework
- [ ] SYNTHESIZER continues to function correctly
- [ ] No regression in existing functionality
- [ ] Documentation accurately reflects the new data flow

## Implementation Timeline

1. **Phase 1:** 30 minutes - Core logic changes
2. **Phase 2:** 15 minutes - Template updates
3. **Phase 3:** 45 minutes - Testing and validation
4. **Phase 4:** 15 minutes - Documentation updates

**Total Estimated Time:** ~2 hours

## Files to Modify

1. `mini_ccn.py` - Worker binding logic
2. `templates/prompts.md` - ELUCIDATOR instructions
3. `README.md` - Data flow documentation
4. `AGENTS.md` - Architecture documentation

## Testing Commands

```bash
# Test the implementation
cd /path/to/EPN
source .venv/bin/activate
python scripts/live_prompt_capture.py

# Verify worker inputs contain reformulated question
grep -A 10 "Input\[1\]" reports/live_run_*.txt
```</content>
<parameter name="filePath">/run/media/fratq/4593fc5e-12d7-4064-8a55-3ad61a661126/CODE/EPN/EPN_WORKER_CONTEXT_PLAN.md
# DeepSeek Integration Plan for EPN System

## Executive Summary

This plan outlines the integration of DeepSeek as an alternative LLM provider to the existing Groq-based system in the EPN (Epistemic Processing Network) pipeline. The implementation will maintain full backward compatibility while adding DeepSeek as an opt-in option through the existing template-driven configuration system.

**Goal**: Enable users to choose between Groq and DeepSeek providers without code changes, using template configuration.

**Timeline**: 2-3 weeks for full implementation and testing
**Risk Level**: Medium (architectural changes required, but well-isolated)

## Current State Analysis

### Existing Architecture
- **Primary LLM Provider**: Groq API (`groq` Python package)
- **Authentication**: `GROQ_API_KEY` environment variable
- **Configuration**: Template-driven via `templates/prompts.md`
- **Response Format**: Strict JSON with fail-fast validation
- **Parameters**: Groq-specific (`max_completion_tokens`)

### DeepSeek Compatibility
- **API**: OpenAI-compatible SDK
- **Authentication**: `DEEPSEEK_API_KEY` environment variable
- **Response Format**: Compatible JSON mode
- **Parameters**: OpenAI-standard (`max_tokens`)

### Key Integration Points
1. **LLM Client** (`llm_client.py`) - Currently hardcoded to Groq
2. **Configuration System** (`llm_config.py`) - Needs provider field
3. **Template Parser** (`template_loader.py`) - Must parse provider
4. **Main Application** (`ccn_minirun.py`) - Provider initialization

## Implementation Phases

### Phase 1: Provider Abstraction Layer (Week 1)
**Objective**: Create abstract provider interface to support multiple LLM backends

#### Tasks:
1. **Create Provider Interface** (`llm_providers.py`)
   - Define `LLMProvider` abstract base class
   - Standardize method signatures across providers
   - Handle parameter mapping differences

2. **Implement Groq Provider** (`groq_provider.py`)
   - Wrap existing Groq logic
   - Maintain current behavior exactly
   - Use `max_completion_tokens` parameter

3. **Implement DeepSeek Provider** (`deepseek_provider.py`)
   - OpenAI-compatible implementation
   - Use `max_tokens` parameter
   - Handle DeepSeek-specific base URL

4. **Update LLM Client** (`llm_client.py`)
   - Accept provider instance instead of hardcoded Groq
   - Maintain existing public API
   - Update initialization logic

#### Success Criteria:
- [ ] All existing tests pass with Groq
- [ ] Provider interface cleanly abstracts differences
- [ ] No breaking changes to existing code

### Phase 2: Configuration System Updates (Week 1)
**Objective**: Add provider selection to configuration system

#### Tasks:
1. **Extend LLM Config** (`llm_config.py`)
   - Add `provider` field to `LLMDefaults` dataclass
   - Update `merge_llm_config()` to handle provider
   - Add environment variable support (`EPN_LLM_PROVIDER`)

2. **Update Template Parser** (`template_loader.py`)
   - Add `provider` to allowed LLM config keys
   - Parse `provider: deepseek` from `## LLM_CONFIG` section
   - Maintain backward compatibility (default to "groq")

3. **Update Main Application** (`ccn_minirun.py`)
   - Modify environment validation for multiple API keys
   - Initialize appropriate provider based on configuration
   - Update connection testing logic

#### Success Criteria:
- [ ] Templates can specify `provider: deepseek`
- [ ] Environment variables support both `GROQ_API_KEY` and `DEEPSEEK_API_KEY`
- [ ] Backward compatibility maintained (defaults to Groq)

### Phase 3: Testing & Validation (Week 2)
**Objective**: Comprehensive testing of DeepSeek integration using live pipeline testing

#### Primary Integration Testing Tool: `scripts/live_prompt_capture.py`
**Why this script?** It provides end-to-end pipeline testing by:
- Running complete CCN cycles with real prompts and responses
- Capturing exact LLM inputs/outputs for validation
- Testing all EPN roles (REFORMULATOR, ELUCIDATOR, workers, SYNTHESIZER)
- Generating detailed reports in `reports/` directory for analysis
- Validating JSON response parsing and role-specific formatting

**Adaptation Required**: Modify `live_prompt_capture.py` to support provider selection for testing both Groq and DeepSeek configurations.

#### Tasks:
1. **Adapt live_prompt_capture.py for Provider Testing**
   - Add command-line provider selection (`--provider groq|deepseek`)
   - Initialize appropriate LLM provider based on selection
   - Update script to work with new provider abstraction
   - Maintain backward compatibility (default to Groq)

2. **Create Provider-Specific Test Templates**
   - `templates/prompts_groq.md` - Optimized for Groq
   - `templates/prompts_deepseek.md` - Optimized for DeepSeek
   - Test same query across both providers for comparison

3. **Integration Test Suite**
   - Run `live_prompt_capture.py` with both providers
   - Compare prompt construction and response quality
   - Validate JSON parsing consistency
   - Test error handling and recovery

4. **Cross-Provider Validation**
   - Same input query produces valid responses on both providers
   - Response formats meet EPN requirements
   - Performance and reliability comparison
   - Template switching works correctly

#### Success Criteria:
- [ ] `live_prompt_capture.py` runs successfully with both providers
- [ ] Generated reports show correct prompt construction for each provider
- [ ] All EPN roles produce valid JSON responses on DeepSeek
- [ ] Response parsing works consistently across providers
- [ ] Template-driven provider switching functions correctly

### Phase 4: Documentation & Examples (Week 2)
**Objective**: Complete documentation and user guidance

#### Tasks:
1. **Update README.md**
   - Add DeepSeek setup instructions
   - Document provider configuration
   - Include example templates

2. **Create DeepSeek Template Examples**
   - Update `templates/prompts.md` with DeepSeek config
   - Provide optimized parameters for DeepSeek
   - Document temperature recommendations

3. **Update Code Comments**
   - Document provider abstraction
   - Explain parameter differences
   - Note compatibility considerations

#### Success Criteria:
- [ ] Users can easily configure DeepSeek
- [ ] Clear documentation of differences
- [ ] Example configurations provided

## Detailed File Modifications

### New Files Created:
```
llm_providers.py      # Abstract provider interface
groq_provider.py      # Groq implementation
deepseek_provider.py  # DeepSeek implementation
```

### Files Modified:

#### `llm_client.py`
- Replace hardcoded Groq client with provider instance
- Update `__init__()` to accept provider
- Maintain existing `call_completion()` API

#### `llm_config.py`
- Add `provider: str = "groq"` to `LLMDefaults`
- Update `get_default_llm_config()` for provider
- Add `EPN_LLM_PROVIDER` environment support

#### `template_loader.py`
- Add `"provider"` to allowed LLM config keys
- Update `_parse_llm_overrides()` for provider parsing
- Maintain case-insensitive parsing

#### `ccn_minirun.py`
- Update `validate_environment()` for multiple API keys
- Modify LLM client initialization with provider selection
- Update connection testing for provider abstraction

#### `scripts/live_prompt_capture.py`
- Add `--provider` command-line option for provider selection
- Update LLM client initialization to use provider abstraction
- Maintain existing capture and reporting functionality
- Support both Groq and DeepSeek testing

## Testing Strategy

### Primary Integration Testing: `scripts/live_prompt_capture.py`
**Core Testing Approach**: Use `live_prompt_capture.py` as the primary integration testing tool because it:
- Runs complete end-to-end EPN pipelines
- Captures exact prompts sent to LLMs and raw responses received
- Tests all role types (REFORMULATOR, ELUCIDATOR, workers, SYNTHESIZER)
- Generates detailed reports for prompt/response analysis
- Validates JSON parsing and role-specific response formats
- Provides debugging information for integration issues

**Testing Workflow**:
1. Run `live_prompt_capture.py --provider groq` to establish baseline
2. Run `live_prompt_capture.py --provider deepseek` to test integration
3. Compare generated reports for prompt construction and response quality
4. Validate that DeepSeek produces properly formatted JSON responses
5. Test error handling and recovery scenarios

### Unit Testing
- Provider interface compliance
- Parameter mapping accuracy
- Error handling consistency
- JSON parsing validation

### Integration Testing
- Full EPN pipeline with DeepSeek via `live_prompt_capture.py`
- Template-driven configuration switching
- Multi-provider comparison testing
- Response format validation across providers

### Compatibility Testing
- Same prompts on both providers using identical templates
- Response quality and format adherence comparison
- Performance metrics collection
- Error recovery testing

## Risk Assessment & Mitigation

### High Risk Areas:
1. **Provider Abstraction** - Complex architectural change
   - **Mitigation**: Thorough unit testing, gradual rollout

2. **Parameter Mapping** - Different parameter names/meanings
   - **Mitigation**: Comprehensive parameter validation tests

### Medium Risk Areas:
1. **Authentication** - Multiple API key handling
   - **Mitigation**: Clear error messages, validation

2. **JSON Parsing** - Provider-specific response variations
   - **Mitigation**: Strict validation, format testing

### Low Risk Areas:
1. **Template System** - Already flexible
2. **Error Handling** - Similar exception patterns

## Rollback Plan

### Immediate Rollback (Phase 1-2):
- Revert `llm_client.py` to original Groq implementation
- Remove provider-related configuration changes
- Restore original template parsing

### Partial Rollback (Phase 3+):
- Keep provider abstraction but disable DeepSeek
- Comment out DeepSeek provider registration
- Maintain Groq functionality

### Full Rollback:
- Delete new provider files
- Revert all modified files to original state
- Remove DeepSeek dependencies

## Success Criteria

### Functional Requirements:
- [ ] `live_prompt_capture.py` works with both Groq and DeepSeek providers
- [ ] DeepSeek produces valid JSON responses for all EPN roles
- [ ] Template-driven provider switching functions correctly
- [ ] Generated reports show proper prompt construction and responses
- [ ] Backward compatibility maintained (defaults to Groq)

### Performance Requirements:
- [ ] Response times comparable to Groq
- [ ] No memory leaks in provider switching
- [ ] Error handling doesn't impact performance

### Quality Requirements:
- [ ] All existing tests pass
- [ ] New provider tests achieve 95%+ coverage
- [ ] Documentation is complete and accurate
- [ ] Code follows existing style guidelines

## Implementation Checklist

### Pre-Implementation:
- [ ] Review and approve this plan
- [ ] Set up DeepSeek API access for testing
- [ ] Create feature branch for development

### Phase 1 Implementation:
- [ ] Create `llm_providers.py`
- [ ] Implement `groq_provider.py`
- [ ] Implement `deepseek_provider.py`
- [ ] Update `llm_client.py`
- [ ] Run existing tests to ensure no regression

### Phase 2 Implementation:
- [ ] Update `llm_config.py`
- [ ] Update `template_loader.py`
- [ ] Update `ccn_minirun.py`
- [ ] Test configuration parsing

### Phase 3 Implementation:
- [ ] Adapt `live_prompt_capture.py` for provider selection
- [ ] Create provider-specific test templates
- [ ] Run comparative testing between Groq and DeepSeek
- [ ] Validate JSON parsing and response formats
- [ ] Test error handling and recovery scenarios

### Phase 4 Implementation:
- [ ] Update documentation
- [ ] Create example templates
- [ ] Final integration testing

### Post-Implementation:
- [ ] Code review and approval
- [ ] Merge to main branch
- [ ] Update production environment
- [ ] Monitor for issues

## Dependencies & Prerequisites

### Required Dependencies:
- `openai` package (for DeepSeek provider)
- Existing `groq` package (maintained)

### Environment Setup:
- `DEEPSEEK_API_KEY` environment variable
- Existing `GROQ_API_KEY` maintained

### Testing Environment:
- Access to both Groq and DeepSeek APIs
- Test templates for both providers
- Automated test suite execution

## Communication Plan

### Internal Communication:
- Weekly progress updates
- Code review requests for each phase
- Testing results shared with team

### Documentation Updates:
- README.md updated with DeepSeek instructions
- Code comments added for new abstractions
- Example configurations provided

This plan provides a structured, low-risk approach to integrating DeepSeek while maintaining the system's reliability and backward compatibility.</content>
<parameter name="filePath">/run/media/fratq/4593fc5e-12d7-4064-8a55-3ad61a661126/CODE/EPN/DeepSeekPlan.md
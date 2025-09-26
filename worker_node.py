"""WorkerNode class for executing CCN roles."""

import json
from typing import Any, Callable, Dict, List, Optional
from mini_memory import MaterializedRole, CCNEvent
from llm_config import merge_llm_config
from llm_client import LLMClient, LLMError


class WorkerNode:
    """Worker node that executes assigned roles."""
    
    def __init__(self, llm_client: LLMClient, event_sink: Optional[Callable[[CCNEvent], None]] = None):
        """Initialize worker node with LLM client."""
        self.llm_client = llm_client
        self.event_sink = event_sink

    def set_event_sink(self, sink: Callable[[CCNEvent], None]) -> None:
        """Assign sink used to capture CCN events."""
        self.event_sink = sink

    def _emit_event(self, event: CCNEvent) -> None:
        """Emit CCNEvent through the configured sink if available."""
        if self.event_sink:
            self.event_sink(event)
    
    def build_prompt(self, role: MaterializedRole) -> str:
        """Build prompt from materialized role."""
        prompt_parts = []
        
        # Header with role name
        prompt_parts.append(f"Role: {role.node_id}")
        prompt_parts.append("")
        
        # Task
        if role.tasks:
            prompt_parts.append(f"Task: {role.tasks[0]}")
            prompt_parts.append("")
        
        # Input signals
        if role.input_signals:
            prompt_parts.append("Inputs:")
            for i, signal in enumerate(role.input_signals, 1):
                prompt_parts.append(f"  Input[{i}]: {signal}")
            prompt_parts.append("")
        
        # Instructions
        if role.instructions:
            prompt_parts.append(f"Instructions: {role.instructions}")
            prompt_parts.append("")
        
        # JSON contract reminder
        if role.llm_config.get('response_format', {}).get('type') == 'json_object':
            prompt_parts.append("IMPORTANT: You must return valid JSON only.")
            if role.node_id == 'REFORMULATOR':
                prompt_parts.append('Required format: {"reformulated_question": "<text>"}')
            elif role.node_id == 'ELUCIDATOR':
                prompt_parts.append('Required format: {"tasks": [["task N", "ROLE: <ROLE_NAME>. <desc> ... RESPONSE_JSON: {...}"], ...]}')
            else:
                if 'node_output_signal' in role.instructions:
                    prompt_parts.append('Required format: {"node_output_signal": "<text>"}')

        return "\n".join(prompt_parts)
    
    def prompt_call(self, role: MaterializedRole) -> Dict[str, Any]:
        """Make LLM call for the role."""
        prompt = self.build_prompt(role)
        
        # Log prompt window
        prompt_event = CCNEvent(
            event_type='prompt_window',
            node_id=role.node_id,
            data={
                'prompt': prompt[:2000] + '...' if len(prompt) > 2000 else prompt,
                'llm_config': role.llm_config
            }
        )
        self._emit_event(prompt_event)

        try:
            params = merge_llm_config(role.llm_config)
            response = self.llm_client.call_completion(
                prompt=prompt,
                model=params.get('model'),
                temperature=params.get('temperature'),
                max_tokens=params.get('max_tokens'),
                reasoning_effort=params.get('reasoning_effort'),
                response_format=params.get('response_format')
            )
            raw_body = getattr(self.llm_client, "last_raw_response", None)
            if raw_body is not None:
                trimmed_raw = raw_body[:2000] + '...' if len(raw_body) > 2000 else raw_body
                self._emit_event(CCNEvent(
                    event_type='raw_response',
                    node_id=role.node_id,
                    data={'body': trimmed_raw}
                ))
            response_json = json.dumps(response)
            trimmed_parsed = response_json[:2000] + '...' if len(response_json) > 2000 else response_json
            self._emit_event(CCNEvent(
                event_type='parsed_response',
                node_id=role.node_id,
                data={'body': trimmed_parsed}
            ))

            return response
            
        except LLMError as e:
            raise LLMError(f"LLM call failed for role {role.node_id}: {str(e)}")
    
    def emit(self, response: Dict[str, Any], role: MaterializedRole) -> Any:
        """Process and emit the response."""
        # Validate response based on role type
        if role.node_id == 'REFORMULATOR':
            if 'reformulated_question' not in response:
                raise ValueError(f"REFORMULATOR response missing 'reformulated_question': {response}")
            return response['reformulated_question']
        
        elif role.node_id == 'ELUCIDATOR':
            if 'tasks' not in response:
                raise ValueError(f"ELUCIDATOR response missing 'tasks': {response}")
            if not isinstance(response['tasks'], list):
                raise ValueError(f"ELUCIDATOR tasks must be a list: {response['tasks']}")
            if len(response['tasks']) > 4:
                raise ValueError(f"ELUCIDATOR tasks exceed maximum 4 items: {len(response['tasks'])}")
            return response['tasks']
        
        else:
            # Worker roles and SYNTHESIZER
            if 'node_output_signal' not in response:
                raise ValueError(f"Role {role.node_id} response missing 'node_output_signal': {response}")
            return response['node_output_signal']
    
    def execute_role(self, role: MaterializedRole) -> Any:
        """Execute complete role: build prompt, call LLM, emit response."""
        # Start event
        start_event = CCNEvent(
            event_type='role_start',
            node_id=role.node_id,
            data={'role': role.__dict__}
        )
        self._emit_event(start_event)

        try:
            # Make LLM call
            response = self.prompt_call(role)
            
            # Process response
            result = self.emit(response, role)
            
            # Complete event
            complete_event = CCNEvent(
                event_type='role_complete',
                node_id=role.node_id,
                data={'result': result}
            )
            self._emit_event(complete_event)
            
            return result
            
        except Exception as e:
            # Error event
            error_event = CCNEvent(
                event_type='error',
                node_id=role.node_id,
                data={'error': str(e)}
            )
            self._emit_event(error_event)
            raise

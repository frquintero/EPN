"""WorkerNode class for executing CCN roles."""

from typing import Any, Dict, List, Optional
from mini_memory import MaterializedRole, CCNEvent
from llm_client import LLMClient, LLMError


class WorkerNode:
    """Worker node that executes assigned roles."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize worker node with LLM client."""
        self.llm_client = llm_client
    
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
        
        try:
            response = self.llm_client.call_completion(
                prompt=prompt,
                model=role.llm_config.get('model', 'llama-3.3-70b-versatile'),
                temperature=role.llm_config.get('temperature', 0.1),
                max_tokens=role.llm_config.get('max_tokens', 4096),
                reasoning_effort=role.llm_config.get('reasoning_effort', 'low'),
                response_format=role.llm_config.get('response_format', {'type': 'json_object'})
            )
            
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
            
            return result
            
        except Exception as e:
            # Error event
            error_event = CCNEvent(
                event_type='error',
                node_id=role.node_id,
                data={'error': str(e)}
            )
            raise

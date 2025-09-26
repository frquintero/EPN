"""SYNAPTIC KV parser and materializer with strict validation."""

from typing import Any, Dict, List, Optional, Union
from mini_memory import SynapticKV, SynapticKVList, MaterializedRole


class ValidationError(Exception):
    """Raised when SYNAPTIC validation fails."""
    pass


class SynapticParser:
    """Parser for SYNAPTIC KV lists with strict validation."""
    
    ALLOWED_KEYS = {
        # Attributes
        'attributes.node_id',
        'attributes.entry_id', 
        'attributes.input_signals',
        'attributes.node_output_signal',
        'attributes.tasks',
        'attributes.instructions',
        # LLM Config
        'llm_config.model',
        'llm_config.temperature',
        'llm_config.max_tokens',
        'llm_config.reasoning_effort',
        'llm_config.response_format'
    }
    
    KEY_TYPES = {
        'attributes.node_id': str,
        'attributes.entry_id': str,
        'attributes.input_signals': list,
        'attributes.node_output_signal': (str, type(None)),
        'attributes.tasks': list,
        'attributes.instructions': str,
        'llm_config.model': str,
        'llm_config.temperature': (int, float),
        'llm_config.max_tokens': int,
        'llm_config.reasoning_effort': str,
        'llm_config.response_format': dict
    }
    
    @classmethod
    def validate_kv(cls, kv: SynapticKV) -> None:
        """Validate a single key-value pair."""
        if kv.key not in cls.ALLOWED_KEYS:
            raise ValidationError(f"Key '{kv.key}' not in allowed keys: {cls.ALLOWED_KEYS}")
        
        expected_type = cls.KEY_TYPES[kv.key]
        if not isinstance(kv.value, expected_type):
            if isinstance(expected_type, tuple):
                if not any(isinstance(kv.value, t) for t in expected_type):
                    raise ValidationError(f"Key '{kv.key}' expects type {expected_type}, got {type(kv.value)}")
            else:
                raise ValidationError(f"Key '{kv.key}' expects type {expected_type}, got {type(kv.value)}")
    
    @classmethod
    def validate_synaptic_list(cls, synaptic_list: SynapticKVList) -> None:
        """Validate entire SYNAPTIC list."""
        seen_keys = set()
        
        for kv in synaptic_list.kvs:
            cls.validate_kv(kv)
            
            # Check for duplicate keys
            if kv.key in seen_keys:
                raise ValidationError(f"Duplicate key '{kv.key}' in SYNAPTIC list")
            seen_keys.add(kv.key)
        
        # Validate required keys for materialization
        required_keys = {'attributes.node_id', 'attributes.entry_id'}
        missing_keys = required_keys - seen_keys
        if missing_keys:
            raise ValidationError(f"Missing required keys: {missing_keys}")
    
    @classmethod
    def materialize_role(cls, synaptic_list: SynapticKVList) -> MaterializedRole:
        """Materialize a role from SYNAPTIC list."""
        cls.validate_synaptic_list(synaptic_list)
        
        # Extract attributes
        node_id = synaptic_list.get('attributes.node_id', '')
        entry_id = synaptic_list.get('attributes.entry_id', '')
        input_signals = synaptic_list.get('attributes.input_signals', [])
        node_output_signal = synaptic_list.get('attributes.node_output_signal')
        tasks = synaptic_list.get('attributes.tasks', [])
        instructions = synaptic_list.get('attributes.instructions', '')
        
        # Extract LLM config
        llm_config = {}
        for kv in synaptic_list.kvs:
            if kv.key.startswith('llm_config.'):
                config_key = kv.key.replace('llm_config.', '')
                llm_config[config_key] = kv.value
        
        return MaterializedRole(
            node_id=node_id,
            entry_id=entry_id,
            input_signals=input_signals,
            node_output_signal=node_output_signal,
            tasks=tasks,
            instructions=instructions,
            llm_config=llm_config
        )


class NodeTemplates:
    """Built-in Node Templates for CCN roles."""
    
    @staticmethod
    def create_reformulator(input_query: str) -> SynapticKVList:
        """Create REFORMULATOR role."""
        kv_list = SynapticKVList()
        kv_list.add('attributes.node_id', 'REFORMULATOR')
        kv_list.add('attributes.entry_id', 'reformulator_001')
        kv_list.add('attributes.input_signals', [input_query])
        kv_list.add('attributes.instructions', 
            'Reformulate the user input into a clear, actionable question. '
            'Return JSON: {"reformulated_question": "<your reformulated text>"}')
        kv_list.add('llm_config.model', 'llama-3.1-70b-versatile')
        kv_list.add('llm_config.temperature', 0.1)
        kv_list.add('llm_config.max_tokens', 1024)
        kv_list.add('llm_config.reasoning_effort', 'low')
        kv_list.add('llm_config.response_format', {'type': 'json_object'})
        return kv_list
    
    @staticmethod
    def create_elucidator(reformulated_question: str) -> SynapticKVList:
        """Create ELUCIDATOR role."""
        kv_list = SynapticKVList()
        kv_list.add('attributes.node_id', 'ELUCIDATOR')
        kv_list.add('attributes.entry_id', 'elucidator_001')
        kv_list.add('attributes.input_signals', [reformulated_question])
        kv_list.add('attributes.instructions',
            'Break down the reformulated question into maximum 4 specific tasks. '
            'The final task must be for SYNTHESIZER. '
            'Return JSON: {"tasks": [["task 1", "ROLE: <ROLE_NAME>. <description> RESPONSE_JSON: {...}"], ...]}')
        kv_list.add('llm_config.model', 'llama-3.1-70b-versatile')
        kv_list.add('llm_config.temperature', 0.1)
        kv_list.add('llm_config.max_tokens', 2048)
        kv_list.add('llm_config.reasoning_effort', 'medium')
        kv_list.add('llm_config.response_format', {'type': 'json_object'})
        return kv_list
    
    @staticmethod
    def create_worker_role(task_text: str, input_signal: str, role_name: str, task_index: int) -> SynapticKVList:
        """Create worker role from ELUCIDATOR task."""
        kv_list = SynapticKVList()
        kv_list.add('attributes.node_id', role_name)
        kv_list.add('attributes.entry_id', f'{role_name.lower()}_00{task_index + 1}')
        kv_list.add('attributes.input_signals', [input_signal])
        kv_list.add('attributes.tasks', [task_text])
        kv_list.add('attributes.instructions',
            'Execute the assigned task and return the result. '
            'Return JSON: {"node_output_signal": "<your output>"}')
        kv_list.add('llm_config.model', 'llama-3.1-70b-versatile')
        kv_list.add('llm_config.temperature', 0.1)
        kv_list.add('llm_config.max_tokens', 2048)
        kv_list.add('llm_config.reasoning_effort', 'low')
        kv_list.add('llm_config.response_format', {'type': 'json_object'})
        return kv_list
    
    @staticmethod
    def create_synthesizer() -> SynapticKVList:
        """Create SYNTHESIZER role."""
        kv_list = SynapticKVList()
        kv_list.add('attributes.node_id', 'SYNTHESIZER')
        kv_list.add('attributes.entry_id', 'synthesizer_001')
        kv_list.add('attributes.input_signals', ['Aggregator buffer contents'])
        kv_list.add('attributes.instructions',
            'Synthesize the outputs from all worker roles into a coherent final response. '
            'Return JSON: {"node_output_signal": "<final synthesized output>"}')
        kv_list.add('llm_config.model', 'llama-3.1-70b-versatile')
        kv_list.add('llm_config.temperature', 0.1)
        kv_list.add('llm_config.max_tokens', 4096)
        kv_list.add('llm_config.reasoning_effort', 'high')
        kv_list.add('llm_config.response_format', {'type': 'json_object'})
        return kv_list
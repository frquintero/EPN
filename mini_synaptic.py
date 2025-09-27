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
        'llm_config.response_format',
        'call_plan',
        'call_args'
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
        'llm_config.response_format': dict,
        'call_plan': list,
        'call_args': dict
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
        
        call_plan = None
        call_args = None

        for kv in synaptic_list.kvs:
            cls.validate_kv(kv)
            
            # Check for duplicate keys
            if kv.key in seen_keys:
                raise ValidationError(f"Duplicate key '{kv.key}' in SYNAPTIC list")
            seen_keys.add(kv.key)
            if kv.key == 'call_plan':
                call_plan = kv.value
            elif kv.key == 'call_args':
                call_args = kv.value

        # Validate required keys for materialization
        required_keys = {'attributes.node_id', 'attributes.entry_id'}
        missing_keys = required_keys - seen_keys
        if missing_keys:
            raise ValidationError(f"Missing required keys: {missing_keys}")

        if call_plan is not None:
            if not call_plan:
                raise ValidationError("call_plan cannot be empty")
            allowed_items = ["prompt_call", "emit"]
            last_index = -1
            seen_plan_items = set()
            for item in call_plan:
                if item not in allowed_items:
                    raise ValidationError(f"call_plan contains invalid item '{item}'")
                item_index = allowed_items.index(item)
                if item_index <= last_index:
                    raise ValidationError("call_plan items must follow canonical order [prompt_call, emit]")
                if item in seen_plan_items:
                    raise ValidationError(f"call_plan contains duplicate item '{item}'")
                seen_plan_items.add(item)
                last_index = item_index

        if call_args is not None and call_args != {}:
            raise ValidationError("call_args must be an empty object for MVP")
    
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
        
        # Extract LLM config and call plan/args
        llm_config = {}
        call_plan: List[str] = []
        call_args: Dict[str, Any] = {}
        for kv in synaptic_list.kvs:
            if kv.key.startswith('llm_config.'):
                config_key = kv.key.replace('llm_config.', '')
                llm_config[config_key] = kv.value
            elif kv.key == 'call_plan':
                call_plan = kv.value
            elif kv.key == 'call_args':
                call_args = kv.value

        return MaterializedRole(
            node_id=node_id,
            entry_id=entry_id,
            input_signals=input_signals,
            node_output_signal=node_output_signal,
            tasks=tasks,
            instructions=instructions,
            llm_config=llm_config,
            call_plan=call_plan,
            call_args=call_args
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
        kv_list.add('attributes.tasks', ['ROLE: REFORMULATOR'])
        kv_list.add(
            'attributes.instructions',
            """
MANDATORY TRANSFORMATIONS:
1. Replace "what are" with "how do/function as" or "what constitutes"
2. Add epistemic context ("within cognitive science's study of...")
3. Include narrative hooks ("evolution of", "function as", "role in")
4. Eliminate assumption of simple answers
5. Prime for multi-perspective analysis

Example transformation:
"What are mental models?" → "How have mental models been conceptualized as cognitive frameworks within different theoretical approaches in cognitive science?"

Input: {query}
Output: JSON only: {"reformulated_question": "<text>"}
""".strip()
        )
        # LLM config is centralized; rely on defaults/env. No per-role values needed here.
        return kv_list

    @staticmethod
    def create_elucidator(reformulated_question: str) -> SynapticKVList:
        """Create ELUCIDATOR role."""
        kv_list = SynapticKVList()
        kv_list.add('attributes.node_id', 'ELUCIDATOR')
        kv_list.add('attributes.entry_id', 'elucidator_001')
        kv_list.add('attributes.input_signals', [reformulated_question])
        kv_list.add('attributes.tasks', [
            'ROLE: ELUCIDATOR. You are an epistemological query_decompositor specialist. '
            'Your function is to analyze complex inquiries and break them down into 2-4 specialized, self-contained investigative questions drawn from relevant knowledge domains. '
            'Each query_decomposition stands alone with complete semantic integrity, focused on specific aspects of the original inquiry. '
            'Together they enable comprehensive understanding extraction.'
        ])
        kv_list.add(
            'attributes.instructions',
            'Output MUST be a JSON object with exactly one field \'query_decomposition\' (no prose before/after).\n'
            "Each array item MUST be a two-element array: ['query_decomposition N', 'ROLE: <ROLE_NAME>. <query_decomposition description>']\n"
            '<ROLE_NAME> MUST be UPPERCASE with underscores only.\n'
            "The last item MUST be ['query_decomposition X', 'ROLE: SYNTHESIZER. You are an integrative knowledge synthesizer. Your function is to analyze and integrate the collected query decompositions into a coherent, evidence-grounded synthesis that presents one or more well-supported proposed answers.']\n"
            'Keep each query_decomposition under 70 words.\n'
            'Select at most 4 items in total (including the final SYNTHESIZER item).'
        )
        # LLM config is centralized; rely on defaults/env. No per-role values needed here.
        return kv_list
    
    @staticmethod
    def create_worker_role(role_name: str, task_index: int) -> SynapticKVList:
        """Create worker role placeholder from ELUCIDATOR task."""
        kv_list = SynapticKVList()
        kv_list.add('attributes.node_id', role_name)
        kv_list.add('attributes.entry_id', f'{role_name.lower()}_{task_index:03}')
        kv_list.add('attributes.input_signals', [])
        kv_list.add('attributes.tasks', [])
        kv_list.add('attributes.instructions', '')
        # LLM config is centralized; rely on defaults/env. No per-role values needed here.
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
        # LLM config is centralized; rely on defaults/env. No per-role values needed here.
        return kv_list

"""CCN orchestrator with execution loop and MEMORY management."""

import json
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from mini_memory import MEMORY, MaterializedRole, PerRoleRecord, CCNEvent, SynapticKVList
from mini_synaptic import SynapticParser, NodeTemplates, ValidationError
from worker_node import WorkerNode
from template_loader import repo as template_repo
from llm_client import LLMError


class CCNError(Exception):
    """Raised when CCN orchestration fails."""
    pass


class MiniCCN:
    """CCN orchestrator for managing the execution cycle.

    In the MVP, method dispatch (prompt_call → emit) is performed inside the
    worker via `execute_role`. To keep a migration path for CCN-dispatch, an
    optional `dispatch_in_ccn` flag allows CCN to honor `call_plan` and invoke
    built-in steps directly. Default remains worker-dispatch to preserve
    behavior.
    """

    def __init__(
        self,
        worker_node: WorkerNode,
        debug: bool = False,
        dispatch_in_ccn: bool = False,
    ):
        """Initialize CCN with worker node and debug/dispatch flags."""
        self.memory = MEMORY()
        self.worker_node = worker_node
        self.worker_node.set_event_sink(self.memory.log_event)
        self.debug = debug
        self.dispatch_in_ccn = dispatch_in_ccn
        self.pending_worker_specs = deque()
        self.synthesizer_spec: Optional[Dict[str, Any]] = None
        self.reformulated_question: Optional[str] = None
        self.metrics: Dict[str, int] = {
            'roles_processed': 0,
            'enqueued_roles': 0,
            'aggregator_appends': 0,
            'llm_errors': 0,
            'parse_errors': 0
        }
    
    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
            if data:
                print(f"  Data: {json.dumps(data, indent=2)[:500]}...")

    def _parse_task_entry(self, index: int, item: Any) -> Dict[str, Any]:
        """Parse an individual ELUCIDATOR query_decomposition item."""
        if not isinstance(item, list) or len(item) < 2:
            raise CCNError(f"ELUCIDATOR item {index + 1} is malformed: {item}")

        raw_text = str(item[1]).strip()
        if 'ROLE:' not in raw_text:
            raise CCNError(f"ELUCIDATOR item {index + 1} missing ROLE declaration")

        role_indicator = raw_text.split('ROLE:', 1)[1].strip()
        dot_index = role_indicator.find('.')
        if dot_index == -1:
            raise CCNError(f"ELUCIDATOR item {index + 1} missing role description separator")

        # Normalize role name to reduce brittle failures from minor casing issues
        role_name = role_indicator[:dot_index].strip().upper()
        description = role_indicator[dot_index + 1 :].strip()

        if not role_name:
            raise CCNError(f"ELUCIDATOR item {index + 1} missing role name")
        if not description:
            raise CCNError(f"ELUCIDATOR item {index + 1} missing description")

        if not all(part.isupper() for part in role_name.split('_') if part):
            raise CCNError(
                f"ELUCIDATOR item {index + 1} role name '{role_name}' must use uppercase letters and underscores"
            )

        return {
            'index': index + 1,
            'label': item[0],
            'role_name': role_name,
            'description': description,
            'raw_text': raw_text
        }

    def _parse_elucidator_tasks(self, items: List[Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Parse and validate ELUCIDATOR query_decomposition list."""
        if not items:
            raise CCNError("ELUCIDATOR did not emit any query_decomposition items")

        parsed = [self._parse_task_entry(idx, it) for idx, it in enumerate(items)]

        if parsed[-1]['role_name'] != 'SYNTHESIZER':
            raise CCNError("Final ELUCIDATOR item must declare ROLE: SYNTHESIZER")

        worker_specs = parsed[:-1]
        synthesizer_spec = parsed[-1]

        # Fallback when templates are absent: limit total items to 4
        if not template_repo().has_templates():
            max_total = 4
            if len(parsed) > max_total:
                keep_workers = max_total - 1
                worker_specs = worker_specs[:keep_workers]

        return worker_specs, synthesizer_spec

    def _run_plan(self, role: MaterializedRole) -> Any:
        """Execute a role either via worker-dispatch or CCN-dispatch.

        - If `dispatch_in_ccn` is False, call `worker_node.execute_role`.
        - If True, honor `role.call_plan` (default [prompt_call, emit]) and
          invoke steps explicitly. Emits role_start/complete events here.
        """
        if not self.dispatch_in_ccn:
            return self.worker_node.execute_role(role)

        # CCN-dispatch path
        self.memory.log_event(CCNEvent(
            event_type='role_start',
            node_id=role.node_id,
            data={'role': role.__dict__}
        ))

        plan = role.call_plan or ['prompt_call', 'emit']
        response: Any = None
        result: Any = None

        for step in plan:
            if step == 'prompt_call':
                response = self.worker_node.prompt_call(role)
            elif step == 'emit':
                if response is None:
                    raise CCNError(
                        f"call_plan for {role.node_id} invoked 'emit' before "
                        "'prompt_call'"
                    )
                result = self.worker_node.emit(response, role)
            else:
                raise CCNError(f"Unsupported plan step '{step}' for {role.node_id}")

        if result is None:
            raise CCNError(f"No result produced for role {role.node_id}")

        self.memory.log_event(CCNEvent(
            event_type='role_complete',
            node_id=role.node_id,
            data={'result': result}
        ))

        return result

    def bind_inputs(self, source_role: str, target_role: MaterializedRole,
                   source_output: Any) -> MaterializedRole:
        """Apply binding rules between roles."""
        self.log_debug(f"Binding {source_role} -> {target_role.node_id}")

        if source_role == 'USER' and target_role.node_id == 'REFORMULATOR':
            target_role.input_signals = [str(source_output)]
            target_role.llm_config.setdefault('response_format', {'type': 'json_object'})
            if not target_role.call_plan:
                target_role.call_plan = ['prompt_call', 'emit']
            return target_role

        if source_role == 'REFORMULATOR' and target_role.node_id == 'ELUCIDATOR':
            target_role.input_signals = [str(source_output)]
            target_role.llm_config.setdefault('response_format', {'type': 'json_object'})
            if not target_role.call_plan:
                target_role.call_plan = ['prompt_call', 'emit']
            return target_role

        if source_role == 'ELUCIDATOR' and target_role.node_id != 'SYNTHESIZER':
            if not isinstance(source_output, dict):
                raise CCNError("Worker binding requires structured task payload")
            spec = source_output.get('task_spec')
            if spec is None:
                raise CCNError("Incomplete worker binding payload from ELUCIDATOR")

            role_name = spec['role_name']
            target_role.node_id = role_name
            target_role.entry_id = f"{role_name.lower()}_{spec['index']:03}"
            target_role.input_signals = [spec['raw_text']]
            target_role.tasks = []
            # Preserve any default worker instructions from the template (e.g., 70-word limit)
            target_role.llm_config.setdefault('response_format', {'type': 'json_object'})
            if not target_role.call_plan:
                target_role.call_plan = ['prompt_call', 'emit']
            return target_role

        if source_role == 'ELUCIDATOR' and target_role.node_id == 'SYNTHESIZER':
            if not isinstance(source_output, dict):
                raise CCNError("Synthesizer binding requires structured payload")
            spec = source_output.get('spec')
            aggregator_payload = source_output.get('aggregator')
            reformulated_question = source_output.get('reformulated_question')
            if spec is None or aggregator_payload is None:
                raise CCNError("Synthesizer binding missing specification or aggregator data")

            if not isinstance(aggregator_payload, list):
                raise CCNError("Aggregator payload must be a list of worker outputs")

            # Bind full aggregator as the content input
            # Provide one input per worker output; optionally prepend the reformulated question
            if not all(isinstance(x, str) for x in aggregator_payload):
                aggregator_payload = [json.dumps(x) if not isinstance(x, str) else x for x in aggregator_payload]
            inputs = list(aggregator_payload)
            if isinstance(reformulated_question, str) and reformulated_question:
                inputs = [reformulated_question] + inputs
            target_role.input_signals = inputs
            # Carry the ELUCIDATOR final decomposition string as the SYNTHESIZER directive
            # so it appears in the prompt per conceptualization.md
            target_role.tasks = []
            target_role.instructions = spec['raw_text']
            target_role.llm_config.setdefault('response_format', {'type': 'json_object'})
            if not target_role.call_plan:
                target_role.call_plan = ['prompt_call', 'emit']
            return target_role

        raise CCNError(f"Unsupported binding from {source_role} to {target_role.node_id}")
    
    def process_reformulator(self, user_input: str) -> str:
        """Process REFORMULATOR role."""
        self.log_debug("Processing REFORMULATOR")
        
        # Create and materialize role
        synaptic_list = NodeTemplates.create_reformulator(user_input)
        role = SynapticParser.materialize_role(synaptic_list)
        role = self.bind_inputs('USER', role, user_input)

        # Set as active
        self.memory.set_active_role(role)
        self.memory.log_event(CCNEvent(
            event_type='memory_mutation',
            node_id='REFORMULATOR',
            data={'action': 'set_active_role', 'role_id': role.node_id}
        ))
        
        # Execute role
        try:
            result = self._run_plan(role)
            
            # Archive result
            record = PerRoleRecord(
                node_id=role.node_id,
                entry_id=role.entry_id,
                input_signals=role.input_signals,
                node_output_signal=result,
                tasks=role.tasks
            )
            self.memory.add_to_archive(record)

            # Clear active
            self.memory.clear_active_role()

            self.reformulated_question = result
            self.metrics['roles_processed'] += 1

            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id='REFORMULATOR',
                data={'error': str(e)}
            ))
            if isinstance(e, LLMError):
                self.metrics['llm_errors'] += 1
            raise CCNError(f"REFORMULATOR failed: {str(e)}")
    
    def process_elucidator(self, reformulated_question: str) -> List[List[str]]:
        """Process ELUCIDATOR role."""
        self.log_debug("Processing ELUCIDATOR")
        
        # Create and materialize role
        synaptic_list = NodeTemplates.create_elucidator(reformulated_question)
        role = SynapticParser.materialize_role(synaptic_list)
        role = self.bind_inputs('REFORMULATOR', role, reformulated_question)

        # Set as active
        self.memory.set_active_role(role)
        self.memory.log_event(CCNEvent(
            event_type='memory_mutation',
            node_id='ELUCIDATOR',
            data={'action': 'set_active_role', 'role_id': role.node_id}
        ))
        
        # Execute role
        try:
            result = self._run_plan(role)
            self.pending_worker_specs.clear()
            try:
                worker_specs, synthesizer_spec = self._parse_elucidator_tasks(result)
            except CCNError:
                self.metrics['parse_errors'] += 1
                raise

            # Archive result
            record = PerRoleRecord(
                node_id=role.node_id,
                entry_id=role.entry_id,
                input_signals=role.input_signals,
                node_output_signal=str(result),
                tasks=role.tasks
            )
            self.memory.add_to_archive(record)

            # Clear active and enqueue worker tasks
            self.memory.clear_active_role()

            self.pending_worker_specs = deque(worker_specs)
            self.synthesizer_spec = synthesizer_spec
            self.memory.aggregator_buffer.clear()

            self.metrics['roles_processed'] += 1

            for spec in worker_specs:
                worker_synaptic = NodeTemplates.create_worker_role(spec['role_name'], spec['index'])
                try:
                    self.memory.add_to_worklist(worker_synaptic)
                except ValueError as exc:
                    raise CCNError(str(exc))
                self.metrics['enqueued_roles'] += 1

            synthesizer_synaptic = NodeTemplates.create_synthesizer()
            try:
                self.memory.add_to_worklist(synthesizer_synaptic)
            except ValueError as exc:
                raise CCNError(str(exc))
            self.metrics['enqueued_roles'] += 1

            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id='ELUCIDATOR',
                data={'error': str(e)}
            ))
            if isinstance(e, LLMError):
                self.metrics['llm_errors'] += 1
            raise CCNError(f"ELUCIDATOR failed: {str(e)}")
    
    def process_worker_role(self, synaptic_list: SynapticKVList) -> str:
        """Process a worker role from worklist."""
        self.log_debug("Processing worker role")
        
        # Materialize role
        role = SynapticParser.materialize_role(synaptic_list)

        if not self.pending_worker_specs:
            raise CCNError("No worker specification available for enqueued role")

        spec = self.pending_worker_specs.popleft()
        role = self.bind_inputs('ELUCIDATOR', role, {
            'task_spec': spec
        })

        # Set as active
        self.memory.set_active_role(role)
        self.memory.log_event(CCNEvent(
            event_type='memory_mutation',
            node_id=role.node_id,
            data={'action': 'set_active_role', 'role_id': role.node_id}
        ))
        
        # Execute role
        try:
            result = self._run_plan(role)
            
            # Add to aggregator buffer
            # Append a formatted item that carries the original decomposition header and the worker output
            try:
                self.memory.add_to_aggregator(result)
            except ValueError as exc:
                raise CCNError(str(exc))
            self.memory.log_event(CCNEvent(
                event_type='memory_mutation',
                node_id=role.node_id,
                data={'action': 'add_to_aggregator', 'result': result[:200] + '...' if len(result) > 200 else result}
            ))
            self.metrics['aggregator_appends'] += 1
            
            # Archive result
            record = PerRoleRecord(
                node_id=role.node_id,
                entry_id=role.entry_id,
                input_signals=role.input_signals,
                node_output_signal=result,
                tasks=role.tasks
            )
            self.memory.add_to_archive(record)
            
            # Clear active
            self.memory.clear_active_role()
            self.metrics['roles_processed'] += 1
            
            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id=role.node_id,
                data={'error': str(e)}
            ))
            # Continue execution even if worker fails
            if isinstance(e, LLMError):
                self.metrics['llm_errors'] += 1
                return f"Error in {role.node_id}: {str(e)}"
            raise CCNError(str(e))
    
    def process_synthesizer(self) -> str:
        """Process SYNTHESIZER role."""
        self.log_debug("Processing SYNTHESIZER")
        
        # Create and materialize role
        synaptic_list = NodeTemplates.create_synthesizer()
        role = SynapticParser.materialize_role(synaptic_list)
        if self.synthesizer_spec is None:
            raise CCNError("Missing synthesizer specification from ELUCIDATOR")
        role = self.bind_inputs('ELUCIDATOR', role, {
            'spec': self.synthesizer_spec,
            'aggregator': list(self.memory.aggregator_buffer),
            'reformulated_question': self.reformulated_question
        })

        # Set as active
        self.memory.set_active_role(role)
        self.memory.log_event(CCNEvent(
            event_type='memory_mutation',
            node_id='SYNTHESIZER',
            data={'action': 'set_active_role', 'role_id': role.node_id}
        ))
        
        # Execute role
        try:
            result = self.worker_node.execute_role(role)
            
            # Archive result
            record = PerRoleRecord(
                node_id=role.node_id,
                entry_id=role.entry_id,
                input_signals=role.input_signals,
                node_output_signal=result,
                tasks=role.tasks
            )
            self.memory.add_to_archive(record)
            
            # Clear active
            self.memory.clear_active_role()
            self.metrics['roles_processed'] += 1
            self.pending_worker_specs.clear()
            self.synthesizer_spec = None
            
            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id='SYNTHESIZER',
                data={'error': str(e)}
            ))
            if isinstance(e, LLMError):
                self.metrics['llm_errors'] += 1
            raise CCNError(f"SYNTHESIZER failed: {str(e)}")
    
    def execute(self, user_input: str) -> str:
        """Execute complete CCN cycle."""
        self.log_debug("Starting CCN execution")
        self.metrics = {
            'roles_processed': 0,
            'enqueued_roles': 0,
            'aggregator_appends': 0,
            'llm_errors': 0,
            'parse_errors': 0
        }

        try:
            # Phase 1: REFORMULATOR
            reformulated = self.process_reformulator(user_input)
            self.log_debug(f"REFORMULATOR output: {reformulated[:100]}...")
            
            # Phase 2: ELUCIDATOR
            tasks = self.process_elucidator(reformulated)
            self.log_debug(f"ELUCIDATOR created {len(tasks)} tasks")
            
            # Phase 3: Worker roles (processed from worklist)
            while self.memory.worklist:
                synaptic_list = self.memory.pop_from_worklist()
                role = SynapticParser.materialize_role(synaptic_list)
                
                if role.node_id == 'SYNTHESIZER':
                    # Phase 4: SYNTHESIZER
                    final_result = self.process_synthesizer()
                    self.log_debug("SYNTHESIZER completed")
                    return final_result
                else:
                    # Process worker role
                    self.process_worker_role(synaptic_list)
            
            # If we get here without SYNTHESIZER, something went wrong
            raise CCNError("Execution completed without SYNTHESIZER")
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                data={'error': str(e), 'fatal': True}
            ))
            raise
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution."""
        return {
            'archive_size': len(self.memory.archive),
            'events_count': len(self.memory.run_log),
            'aggregator_size': len(self.memory.aggregator_buffer),
            'roles_executed': [record.node_id for record in self.memory.archive]
        }

    def get_metrics(self) -> Dict[str, int]:
        """Return collected metrics for the most recent execution."""
        return dict(self.metrics)

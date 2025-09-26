"""CCN orchestrator with execution loop and MEMORY management."""

import json
from collections import deque
from typing import Any, Dict, List, Optional, Tuple
from mini_memory import MEMORY, MaterializedRole, PerRoleRecord, CCNEvent, SynapticKVList
from mini_synaptic import SynapticParser, NodeTemplates, ValidationError
from worker_node import WorkerNode
from llm_client import LLMError


class CCNError(Exception):
    """Raised when CCN orchestration fails."""
    pass


class MiniCCN:
    """CCN orchestrator for managing the execution cycle."""
    
    def __init__(self, worker_node: WorkerNode, debug: bool = False):
        """Initialize CCN with worker node and debug flag."""
        self.memory = MEMORY()
        self.worker_node = worker_node
        self.worker_node.set_event_sink(self.memory.log_event)
        self.debug = debug
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

    def _parse_task_entry(self, index: int, task_entry: Any) -> Dict[str, Any]:
        """Parse an individual ELUCIDATOR task entry."""
        if not isinstance(task_entry, list) or len(task_entry) < 2:
            raise CCNError(f"ELUCIDATOR task {index + 1} is malformed: {task_entry}")

        raw_text = str(task_entry[1]).strip()
        if 'ROLE:' not in raw_text or 'RESPONSE_JSON:' not in raw_text:
            raise CCNError(f"ELUCIDATOR task {index + 1} missing ROLE or RESPONSE_JSON declaration")

        role_segment, response_segment = raw_text.split('RESPONSE_JSON:', 1)
        response_segment = response_segment.strip()

        role_indicator = role_segment.split('ROLE:', 1)[1].strip()
        dot_index = role_indicator.find('.')
        if dot_index == -1:
            raise CCNError(f"ELUCIDATOR task {index + 1} missing role description separator")

        role_name = role_indicator[:dot_index].strip()
        description = role_indicator[dot_index + 1 :].strip()

        if not role_name:
            raise CCNError(f"ELUCIDATOR task {index + 1} missing role name")
        if not description:
            raise CCNError(f"ELUCIDATOR task {index + 1} missing description")

        if not all(part.isupper() for part in role_name.split('_') if part):
            raise CCNError(f"ELUCIDATOR task {index + 1} role name '{role_name}' must use uppercase letters and underscores")

        try:
            response_schema = json.loads(response_segment)
        except json.JSONDecodeError as exc:
            raise CCNError(f"ELUCIDATOR task {index + 1} RESPONSE_JSON invalid: {exc}")

        if not isinstance(response_schema, dict):
            raise CCNError(f"ELUCIDATOR task {index + 1} RESPONSE_JSON must be an object")

        return {
            'index': index + 1,
            'label': task_entry[0],
            'role_name': role_name,
            'description': description,
            'response_schema': response_schema,
            'raw_text': raw_text
        }

    def _parse_elucidator_tasks(self, tasks: List[Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Parse and validate ELUCIDATOR task list."""
        if not tasks:
            raise CCNError("ELUCIDATOR did not emit any tasks")
        if len(tasks) > 4:
            raise CCNError("ELUCIDATOR emitted more than 4 tasks")

        parsed = [self._parse_task_entry(idx, task) for idx, task in enumerate(tasks)]

        if parsed[-1]['role_name'] != 'SYNTHESIZER':
            raise CCNError("Final ELUCIDATOR task must declare ROLE: SYNTHESIZER")

        worker_specs = parsed[:-1]
        synthesizer_spec = parsed[-1]

        return worker_specs, synthesizer_spec

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
            question = source_output.get('reformulated_question')
            if spec is None or question is None:
                raise CCNError("Incomplete worker binding payload from ELUCIDATOR")

            role_name = spec['role_name']
            target_role.node_id = role_name
            target_role.entry_id = f"{role_name.lower()}_{spec['index']:03}"
            target_role.input_signals = [str(question)]
            target_role.tasks = [spec['description']]

            schema_text = json.dumps(spec['response_schema'], indent=2)
            target_role.instructions = (
                f"{spec['description']}\n\n"
                "Respond with valid JSON that matches this schema exactly (no extra fields):\n"
                f"{schema_text}"
            )
            target_role.llm_config.setdefault('response_format', {'type': 'json_object'})
            if not target_role.call_plan:
                target_role.call_plan = ['prompt_call', 'emit']
            return target_role

        if source_role == 'ELUCIDATOR' and target_role.node_id == 'SYNTHESIZER':
            if not isinstance(source_output, dict):
                raise CCNError("Synthesizer binding requires structured payload")
            spec = source_output.get('spec')
            aggregator_payload = source_output.get('aggregator')
            if spec is None or aggregator_payload is None:
                raise CCNError("Synthesizer binding missing specification or aggregator data")

            if not isinstance(aggregator_payload, list):
                raise CCNError("Aggregator payload must be a list of worker outputs")

            target_role.input_signals = [json.dumps(aggregator_payload, indent=2)]
            target_role.tasks = [spec['description']]
            schema_text = json.dumps(spec['response_schema'], indent=2)
            target_role.instructions = (
                f"{spec['description']}\n\n"
                "You are provided with worker outputs in Input[1] as JSON."
                " Produce a synthesis and respond with JSON matching this schema exactly (no extra fields):\n"
                f"{schema_text}"
            )
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
            result = self.worker_node.execute_role(role)
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
        if self.reformulated_question is None:
            raise CCNError("Missing reformulated question for worker binding")

        spec = self.pending_worker_specs.popleft()
        role = self.bind_inputs('ELUCIDATOR', role, {
            'task_spec': spec,
            'reformulated_question': self.reformulated_question
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
            result = self.worker_node.execute_role(role)
            
            # Add to aggregator buffer
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
            'aggregator': list(self.memory.aggregator_buffer)
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

"""CCN orchestrator with execution loop and MEMORY management."""

import json
from typing import Any, Dict, List, Optional, Tuple
from mini_memory import MEMORY, MaterializedRole, PerRoleRecord, CCNEvent, SynapticKVList
from mini_synaptic import SynapticParser, NodeTemplates, ValidationError
from worker_node import WorkerNode


class CCNError(Exception):
    """Raised when CCN orchestration fails."""
    pass


class MiniCCN:
    """CCN orchestrator for managing the execution cycle."""
    
    def __init__(self, worker_node: WorkerNode, debug: bool = False):
        """Initialize CCN with worker node and debug flag."""
        self.worker_node = worker_node
        self.memory = MEMORY()
        self.debug = debug
    
    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
            if data:
                print(f"  Data: {json.dumps(data, indent=2)[:500]}...")
    
    def bind_inputs(self, source_role: str, target_role: MaterializedRole, 
                   source_output: Any) -> MaterializedRole:
        """Apply binding rules between roles."""
        self.log_debug(f"Binding {source_role} -> {target_role.node_id}")
        
        if source_role == 'USER' and target_role.node_id == 'REFORMULATOR':
            # User input to REFORMULATOR
            target_role.input_signals = [str(source_output)]
        
        elif source_role == 'REFORMULATOR' and target_role.node_id == 'ELUCIDATOR':
            # REFORMULATOR output to ELUCIDATOR
            target_role.input_signals = [str(source_output)]
        
        elif source_role == 'ELUCIDATOR':
            # ELUCIDATOR tasks to worker roles
            if isinstance(source_output, list) and len(source_output) > 0:
                # Extract role name from task text
                task_text = source_output[0][1] if isinstance(source_output[0], list) else str(source_output[0])
                if 'ROLE:' in task_text:
                    role_name = task_text.split('ROLE:')[1].split('.')[0].strip()
                    target_role.node_id = role_name
                    target_role.entry_id = f"{role_name.lower()}_001"
                
                target_role.tasks = [str(source_output[0]) if isinstance(source_output[0], str) else source_output[0][1]]
                target_role.input_signals = [str(source_output)]
        
        elif source_role.startswith('WORKER_') and target_role.node_id == 'SYNTHESIZER':
            # Worker output to SYNTHESIZER (handled via aggregator buffer)
            pass
        
        return target_role
    
    def process_reformulator(self, user_input: str) -> str:
        """Process REFORMULATOR role."""
        self.log_debug("Processing REFORMULATOR")
        
        # Create and materialize role
        synaptic_list = NodeTemplates.create_reformulator(user_input)
        role = SynapticParser.materialize_role(synaptic_list)
        
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
            
            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id='REFORMULATOR',
                data={'error': str(e)}
            ))
            raise CCNError(f"REFORMULATOR failed: {str(e)}")
    
    def process_elucidator(self, reformulated_question: str) -> List[List[str]]:
        """Process ELUCIDATOR role."""
        self.log_debug("Processing ELUCIDATOR")
        
        # Create and materialize role
        synaptic_list = NodeTemplates.create_elucidator(reformulated_question)
        role = SynapticParser.materialize_role(synaptic_list)
        
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
            
            # Validate and limit tasks
            if len(result) > 4:
                result = result[:4]
                self.memory.log_event(CCNEvent(
                    event_type='memory_mutation',
                    node_id='ELUCIDATOR',
                    data={'action': 'truncate_tasks', 'original_count': len(result), 'new_count': 4}
                ))
            
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
            
            # Create worker roles from tasks
            for i, task in enumerate(result):
                if isinstance(task, list) and len(task) >= 2:
                    task_text = task[1]
                    worker_synaptic = NodeTemplates.create_worker_role(
                        task_text, reformulated_question, f"WORKER_{i+1}", i
                    )
                    self.memory.add_to_worklist(worker_synaptic)
            
            # Always add SYNTHESIZER as final task
            synthesizer_synaptic = NodeTemplates.create_synthesizer()
            self.memory.add_to_worklist(synthesizer_synaptic)
            
            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id='ELUCIDATOR',
                data={'error': str(e)}
            ))
            raise CCNError(f"ELUCIDATOR failed: {str(e)}")
    
    def process_worker_role(self, synaptic_list: SynapticKVList) -> str:
        """Process a worker role from worklist."""
        self.log_debug("Processing worker role")
        
        # Materialize role
        role = SynapticParser.materialize_role(synaptic_list)
        
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
            self.memory.add_to_aggregator(result)
            self.memory.log_event(CCNEvent(
                event_type='memory_mutation',
                node_id=role.node_id,
                data={'action': 'add_to_aggregator', 'result': result[:200] + '...' if len(result) > 200 else result}
            ))
            
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
            
            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id=role.node_id,
                data={'error': str(e)}
            ))
            # Continue execution even if worker fails
            return f"Error in {role.node_id}: {str(e)}"
    
    def process_synthesizer(self) -> str:
        """Process SYNTHESIZER role."""
        self.log_debug("Processing SYNTHESIZER")
        
        # Create and materialize role
        synaptic_list = NodeTemplates.create_synthesizer()
        role = SynapticParser.materialize_role(synaptic_list)
        
        # Add aggregator buffer as input
        role.input_signals = [json.dumps(self.memory.aggregator_buffer, indent=2)]
        
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
            
            return result
            
        except Exception as e:
            self.memory.log_event(CCNEvent(
                event_type='error',
                node_id='SYNTHESIZER',
                data={'error': str(e)}
            ))
            raise CCNError(f"SYNTHESIZER failed: {str(e)}")
    
    def execute(self, user_input: str) -> str:
        """Execute complete CCN cycle."""
        self.log_debug("Starting CCN execution")
        
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
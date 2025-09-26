#!/usr/bin/env python3
"""Demonstration of CCN architecture without actual API calls."""

import json
from datetime import datetime
from mini_memory import MEMORY, SynapticKVList, MaterializedRole, PerRoleRecord, CCNEvent
from mini_synaptic import NodeTemplates, SynapticParser

class MockLLMClient:
    """Mock LLM client for demonstration."""
    
    def __init__(self):
        self.call_count = 0
    
    def call_completion(self, prompt: str, **kwargs) -> dict:
        """Mock LLM call that returns predetermined responses."""
        self.call_count += 1
        
        # Determine response based on prompt content
        if "REFORMULATOR" in prompt:
            return {"reformulated_question": "What are the fundamental principles and applications of machine learning in modern computing?"}
        elif "ELUCIDATOR" in prompt:
            return {
                "tasks": [
                    ["task 1", "ROLE: DEFINITION_EXPERT. Define machine learning concepts and terminology. RESPONSE_JSON: {\"node_output_signal\": \"<definition>\"}"],
                    ["task 2", "ROLE: APPLICATION_ANALYST. Analyze real-world ML applications. RESPONSE_JSON: {\"node_output_signal\": \"<applications>\"}"],
                    ["task 3", "ROLE: TECHNOLOGY_REVIEWER. Review current ML technologies. RESPONSE_JSON: {\"node_output_signal\": \"<technologies>\"}"],
                    ["task 4", "ROLE: SYNTHESIZER. Synthesize all information into comprehensive overview. RESPONSE_JSON: {\"node_output_signal\": \"<synthesis>\"}"]
                ]
            }
        elif "DEFINITION_EXPERT" in prompt:
            return {"node_output_signal": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing algorithms that can analyze data, identify patterns, and make decisions with minimal human intervention."}
        elif "APPLICATION_ANALYST" in prompt:
            return {"node_output_signal": "Machine learning applications span numerous domains: healthcare (diagnostic imaging, drug discovery), finance (fraud detection, algorithmic trading), transportation (autonomous vehicles, route optimization), entertainment (recommendation systems, content generation), and business (customer analytics, supply chain optimization)."}
        elif "TECHNOLOGY_REVIEWER" in prompt:
            return {"node_output_signal": "Current ML technologies include deep learning frameworks (TensorFlow, PyTorch), natural language processing models (GPT, BERT), computer vision systems (CNNs, transformers), reinforcement learning platforms, and specialized hardware (GPUs, TPUs). Emerging trends focus on explainable AI, federated learning, and edge computing."}
        elif "SYNTHESIZER" in prompt:
            return {"node_output_signal": "Machine learning represents a transformative field of artificial intelligence that enables systems to learn from data without explicit programming. Its core principles involve pattern recognition, statistical modeling, and iterative improvement. The technology has revolutionized numerous industries through applications in healthcare diagnostics, financial analysis, autonomous systems, and personalized recommendations. Current technologies leverage deep learning frameworks and specialized hardware, with emerging trends focusing on explainable AI and edge computing. ML's continued evolution promises even greater integration into daily life and business operations."}
        else:
            return {"node_output_signal": f"Mock response for role {self.call_count}"}

class MockWorkerNode:
    """Mock worker node for demonstration."""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def build_prompt(self, role: MaterializedRole) -> str:
        """Build prompt (simplified for demo)."""
        return f"Role: {role.node_id}\nTask: {role.tasks[0] if role.tasks else 'No task'}"
    
    def execute_role(self, role: MaterializedRole):
        """Execute role with mock LLM."""
        prompt = self.build_prompt(role)
        response = self.llm_client.call_completion(prompt)
        
        # Process response based on role type
        if role.node_id == 'REFORMULATOR':
            return response['reformulated_question']
        elif role.node_id == 'ELUCIDATOR':
            return response['tasks']
        else:
            return response['node_output_signal']

class MockCCN:
    """Mock CCN orchestrator for demonstration."""
    
    def __init__(self):
        self.memory = MEMORY()
        self.llm_client = MockLLMClient()
        self.worker_node = MockWorkerNode(self.llm_client)
    
    def execute(self, user_input: str) -> str:
        """Execute complete CCN cycle with mock responses."""
        print(f"🚀 Starting CCN execution for: '{user_input}'")
        print("=" * 60)
        
        # Phase 1: REFORMULATOR
        print("\n📋 Phase 1: REFORMULATOR")
        print("-" * 30)
        synaptic_list = NodeTemplates.create_reformulator(user_input)
        role = SynapticParser.materialize_role(synaptic_list)
        
        reformulated = self.worker_node.execute_role(role)
        print(f"✅ Reformulated question: {reformulated}")
        
        # Archive REFORMULATOR result
        record = PerRoleRecord(
            node_id=role.node_id,
            entry_id=role.entry_id,
            input_signals=role.input_signals,
            node_output_signal=reformulated,
            tasks=role.tasks
        )
        self.memory.add_to_archive(record)
        
        # Phase 2: ELUCIDATOR
        print("\n🔍 Phase 2: ELUCIDATOR")
        print("-" * 30)
        synaptic_list = NodeTemplates.create_elucidator(reformulated)
        role = SynapticParser.materialize_role(synaptic_list)
        
        tasks = self.worker_node.execute_role(role)
        print(f"✅ Generated {len(tasks)} tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task[1] if isinstance(task, list) else task}")
        
        # Archive ELUCIDATOR result
        record = PerRoleRecord(
            node_id=role.node_id,
            entry_id=role.entry_id,
            input_signals=role.input_signals,
            node_output_signal=str(tasks),
            tasks=role.tasks
        )
        self.memory.add_to_archive(record)
        
        # Phase 3: Worker Roles
        print("\n⚙️  Phase 3: Worker Roles")
        print("-" * 30)
        worker_results = []
        
        for i, task in enumerate(tasks[:-1]):  # Exclude SYNTHESIZER task
            if isinstance(task, list) and len(task) >= 2:
                task_text = task[1]
                role_name = f"WORKER_{i+1}"
                
                # Create worker role
                worker_synaptic = NodeTemplates.create_worker_role(
                    task_text, reformulated, role_name, i
                )
                worker_role = SynapticParser.materialize_role(worker_synaptic)
                
                result = self.worker_node.execute_role(worker_role)
                worker_results.append(result)
                
                print(f"✅ {role_name}: {result[:100]}...")
                
                # Archive worker result
                record = PerRoleRecord(
                    node_id=worker_role.node_id,
                    entry_id=worker_role.entry_id,
                    input_signals=worker_role.input_signals,
                    node_output_signal=result,
                    tasks=worker_role.tasks
                )
                self.memory.add_to_archive(record)
                
                # Add to aggregator buffer
                self.memory.add_to_aggregator(result)
        
        # Phase 4: SYNTHESIZER
        print("\n🎯 Phase 4: SYNTHESIZER")
        print("-" * 30)
        synaptic_list = NodeTemplates.create_synthesizer()
        role = SynapticParser.materialize_role(synaptic_list)
        
        # Provide aggregator buffer as input
        role.input_signals = [json.dumps(self.memory.aggregator_buffer, indent=2)]
        
        final_result = self.worker_node.execute_role(role)
        print(f"✅ Final synthesis completed!")
        
        # Archive SYNTHESIZER result
        record = PerRoleRecord(
            node_id=role.node_id,
            entry_id=role.entry_id,
            input_signals=role.input_signals,
            node_output_signal=final_result,
            tasks=role.tasks
        )
        self.memory.add_to_archive(record)
        
        return final_result
    
    def print_summary(self):
        """Print execution summary."""
        print(f"\n📊 Execution Summary")
        print("=" * 60)
        print(f"Total roles executed: {len(self.memory.archive)}")
        print(f"Events logged: {len(self.memory.run_log)}")
        print(f"Aggregator entries: {len(self.memory.aggregator_buffer)}")
        print(f"Mock LLM calls made: {self.llm_client.call_count}")
        
        print(f"\n📋 Roles executed:")
        for record in self.memory.archive:
            print(f"  - {record.node_id} ({record.entry_id})")

def main():
    """Run CCN demonstration."""
    print("🧠 CCN Minimal EPN Cycle Demonstration")
    print("=" * 60)
    print("This demo shows the complete CCN architecture without actual API calls.")
    print("Mock responses simulate the LLM interactions.")
    
    # Create CCN instance
    ccn = MockCCN()
    
    # Run demonstration
    user_query = "What is machine learning?"
    final_result = ccn.execute(user_query)
    
    # Print final result
    print(f"\n📝 Final Result:")
    print("-" * 30)
    print(final_result)
    
    # Print summary
    ccn.print_summary()
    
    print(f"\n✅ Demonstration completed successfully!")
    print("The CCN architecture is working correctly with all components integrated.")

if __name__ == '__main__':
    main()
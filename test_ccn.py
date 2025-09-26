#!/usr/bin/env python3
"""Test script for CCN minimal EPN cycle implementation."""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add the output directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from mini_memory import MEMORY, SynapticKV, SynapticKVList, MaterializedRole
        from mini_synaptic import SynapticParser, NodeTemplates, ValidationError
        from worker_node import WorkerNode
        from mini_ccn import MiniCCN, CCNError
        from llm_client import LLMClient, LLMError
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_memory_structures():
    """Test MEMORY data structures."""
    print("\nTesting MEMORY structures...")
    try:
        from mini_memory import MEMORY, SynapticKVList, MaterializedRole
        
        # Test basic MEMORY operations
        memory = MEMORY()
        
        # Test worklist operations
        synaptic_list = SynapticKVList()
        synaptic_list.add('attributes.node_id', 'TEST_ROLE')
        synaptic_list.add('attributes.entry_id', 'test_001')
        
        memory.add_to_worklist(synaptic_list)
        assert len(memory.worklist) == 1
        
        popped = memory.pop_from_worklist()
        assert popped is not None
        assert len(memory.worklist) == 0
        
        print("✓ MEMORY structures working correctly")
        return True
    except Exception as e:
        print(f"✗ MEMORY test failed: {e}")
        return False

def test_synaptic_validation():
    """Test SYNAPTIC validation."""
    print("\nTesting SYNAPTIC validation...")
    try:
        from mini_synaptic import SynapticParser, SynapticKVList, ValidationError
        
        # Test valid SYNAPTIC list
        valid_list = SynapticKVList()
        valid_list.add('attributes.node_id', 'TEST')
        valid_list.add('attributes.entry_id', 'test_001')
        valid_list.add('llm_config.model', 'test-model')
        
        try:
            SynapticParser.validate_synaptic_list(valid_list)
            print("✓ Valid SYNAPTIC list passed validation")
        except ValidationError:
            print("✗ Valid SYNAPTIC list failed validation")
            return False
        
        # Test invalid SYNAPTIC list
        invalid_list = SynapticKVList()
        invalid_list.add('invalid.key', 'value')
        
        try:
            SynapticParser.validate_synaptic_list(invalid_list)
            print("✗ Invalid SYNAPTIC list passed validation (should fail)")
            return False
        except (ValidationError, ValueError):
            print("✓ Invalid SYNAPTIC list correctly rejected")
        
        return True
    except Exception as e:
        print(f"✗ SYNAPTIC validation test failed: {e}")
        return False

def test_node_templates():
    """Test built-in Node Templates."""
    print("\nTesting Node Templates...")
    try:
        from mini_synaptic import NodeTemplates, SynapticParser
        
        # Test REFORMULATOR template
        reformulator = NodeTemplates.create_reformulator("Test query")
        role = SynapticParser.materialize_role(reformulator)
        assert role.node_id == 'REFORMULATOR'
        assert len(role.input_signals) == 1
        assert role.input_signals[0] == "Test query"
        print("✓ REFORMULATOR template working")
        
        # Test ELUCIDATOR template
        elucidator = NodeTemplates.create_elucidator("Reformulated question")
        role = SynapticParser.materialize_role(elucidator)
        assert role.node_id == 'ELUCIDATOR'
        print("✓ ELUCIDATOR template working")
        
        # Test SYNTHESIZER template
        synthesizer = NodeTemplates.create_synthesizer()
        role = SynapticParser.materialize_role(synthesizer)
        assert role.node_id == 'SYNTHESIZER'
        print("✓ SYNTHESIZER template working")
        
        return True
    except Exception as e:
        print(f"✗ Node Templates test failed: {e}")
        return False

def test_schema_validation():
    """Test JSON schema validation."""
    print("\nTesting schema validation...")
    try:
        from jsonschema import validate, ValidationError
        import json
        
        # Load schema
        schema_path = Path(__file__).parent / 'schemas' / 'memory_record.schema.json'
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Test valid record
        valid_record = {
            "node_id": "TEST_ROLE",
            "entry_id": "test_001",
            "input_signals": ["test input"],
            "node_output_signal": "test output",
            "tasks": ["task1", "task2"],
            "timestamp": "2024-01-01T12:00:00.000000"
        }
        
        try:
            validate(valid_record, schema)
            print("✓ Valid record passed schema validation")
        except ValidationError:
            print("✗ Valid record failed schema validation")
            return False
        
        # Test invalid record
        invalid_record = {
            "node_id": "TEST_ROLE",
            # Missing required fields
        }
        
        try:
            validate(invalid_record, schema)
            print("✗ Invalid record passed schema validation (should fail)")
            return False
        except ValidationError:
            print("✓ Invalid record correctly rejected by schema")
        
        return True
    except Exception as e:
        print(f"✗ Schema validation test failed: {e}")
        return False

def test_cli_basic():
    """Test CLI basic functionality."""
    print("\nTesting CLI basic functionality...")
    try:
        # Test help
        result = subprocess.run([sys.executable, 'ccn_minirun.py', '--help'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and 'Usage:' in result.stdout:
            print("✓ CLI help working")
        else:
            print("✗ CLI help failed")
            return False
        
        # Test validate-only (requires a dummy query argument)
        env = os.environ.copy()
        env['GROQ_API_KEY'] = 'test-key'
        
        result = subprocess.run([sys.executable, 'ccn_minirun.py', '--validate-only', 'test query'], 
                              env=env, capture_output=True, text=True)
        if result.returncode == 0 and 'Setup validation successful' in result.stdout:
            print("✓ CLI validate-only working")
        else:
            print("✗ CLI validate-only failed")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    print("Running CCN Minimal EPN Cycle Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_memory_structures,
        test_synaptic_validation,
        test_node_templates,
        test_schema_validation,
        test_cli_basic
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed! The CCN implementation is ready.")
        return True
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
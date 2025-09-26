#!/usr/bin/env python3
"""Example usage of CCN minimal EPN cycle."""

import os
import subprocess
import sys
from pathlib import Path

def setup_environment():
    """Setup environment for CCN execution."""
    # Note: In a real scenario, you would set your actual Groq API key
    # export GROQ_API_KEY="your-actual-api-key"
    
    # For demonstration, we'll show what the setup would look like
    print("🔧 Environment Setup")
    print("=" * 40)
    print("To use CCN minimal EPN cycle, you need to:")
    print("1. Get a Groq API key from https://console.groq.com")
    print("2. Set the environment variable:")
    print("   export GROQ_API_KEY='your-actual-api-key'")
    print("3. Install dependencies (if not already installed):")
    print("   pip install -r requirements.txt")
    print()

def show_basic_usage():
    """Show basic usage examples."""
    print("📖 Basic Usage Examples")
    print("=" * 40)
    
    examples = [
        {
            "description": "Simple query",
            "command": "python ccn_minirun.py 'What is artificial intelligence?'"
        },
        {
            "description": "With debug mode",
            "command": "python ccn_minirun.py -d 'Explain quantum computing'"
        },
        {
            "description": "Save results to file",
            "command": "python ccn_minirun.py -o results.json 'Analyze renewable energy'"
        },
        {
            "description": "Strict validation mode",
            "command": "python ccn_minirun.py -s 'Describe the water cycle'"
        },
        {
            "description": "Validate setup only",
            "command": "python ccn_minirun.py --validate-only 'test query'"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}:")
        print(f"   {example['command']}")
        print()

def show_architecture_overview():
    """Show the CCN architecture overview."""
    print("🏗️  CCN Architecture Overview")
    print("=" * 40)
    print("The CCN minimal EPN cycle follows this execution flow:")
    print()
    print("User Query")
    print("    ↓")
    print("[REFORMULATOR] - Clarifies and reformulates the input")
    print("    ↓")
    print("[ELUCIDATOR] - Breaks down into ≤4 specific tasks")
    print("    ↓")
    print("[Worker Roles] - Executes individual tasks")
    print("    ↓")
    print("[SYNTHESIZER] - Combines results into final answer")
    print()
    print("Key Features:")
    print("• JSON-only communication between roles")
    print("• Strict validation and error handling")
    print("• Debug windows for transparency")
    print("• MEMORY-based state management")
    print("• Configurable LLM parameters")
    print()

def show_file_structure():
    """Show the project file structure."""
    print("📁 Project Structure")
    print("=" * 40)
    print("ccn-minimal-epn/")
    print("├── ccn_minirun.py          # CLI entrypoint")
    print("├── mini_memory.py          # MEMORY dataclasses")
    print("├── mini_synaptic.py        # KV parser & validator")
    print("├── worker_node.py          # Worker execution logic")
    print("├── mini_ccn.py             # CCN orchestrator")
    print("├── llm_client.py           # Groq API wrapper")
    print("├── schemas/")
    print("│   └── memory_record.schema.json")
    print("├── requirements.txt        # Python dependencies")
    print("├── setup.py               # Package setup")
    print("├── README.md              # Documentation")
    print("├── test_ccn.py            # Test suite")
    print("└── demo_ccn.py            # Architecture demo")
    print()

def show_configuration_options():
    """Show configuration and customization options."""
    print("⚙️  Configuration Options")
    print("=" * 40)
    print("Environment Variables:")
    print("• GROQ_API_KEY (required) - Your Groq API key")
    print()
    print("LLM Configuration (per role):")
    print("• model: llama-3.3-70b-versatile")
    print("• temperature: 0.1")
    print("• max_tokens: 4096")
    print("• reasoning_effort: low/medium/high")
    print("• response_format: JSON object")
    print()
    print("Built-in Roles:")
    print("• REFORMULATOR: Clarifies user input")
    print("• ELUCIDATOR: Creates task breakdown")
    print("• SYNTHESIZER: Combines final results")
    print("• Worker Roles: Execute specific tasks")
    print()

def show_debug_features():
    """Show debug and monitoring features."""
    print("🐛 Debug Features")
    print("=" * 40)
    print("Enable debug mode with -d flag to see:")
    print("• Context snapshots")
    print("• Prompt construction")
    print("• LLM parameters")
    print("• Raw JSON responses")
    print("• MEMORY mutations")
    print("• Execution timeline")
    print()
    print("Archive validation against JSON schema")
    print("Event logging for audit trail")
    print("Aggregator buffer for worker outputs")
    print()

def show_output_formats():
    """Show output format examples."""
    print("📤 Output Formats")
    print("=" * 40)
    print("Console Output:")
    print("• Rich formatted text with progress indicators")
    print("• Final synthesis in highlighted panels")
    print("• Execution summary with statistics")
    print()
    print("JSON Output (with -o flag):")
    print("{")
    print('  "query": "original user query",')
    print('  "result": "final synthesis",')
    print('  "summary": {')
    print('    "archive_size": 6,')
    print('    "events_count": 15,')
    print('    "aggregator_size": 3')
    print('  },')
    print('  "archive": [...],')
    print('  "events": [...]')
    print("}")
    print()

def main():
    """Main example function."""
    print("🎯 CCN Minimal EPN Cycle - Example Usage")
    print("=" * 50)
    print()
    
    setup_environment()
    show_basic_usage()
    show_architecture_overview()
    show_file_structure()
    show_configuration_options()
    show_debug_features()
    show_output_formats()
    
    print("🚀 Getting Started")
    print("=" * 40)
    print("1. Set your GROQ_API_KEY environment variable")
    print("2. Run: python ccn_minirun.py 'Your question here'")
    print("3. Add -d for debug mode")
    print("4. Add -o file.json to save results")
    print()
    print("For more examples, see README.md")
    print()
    print("Happy CCN computing! 🧠")

if __name__ == '__main__':
    main()

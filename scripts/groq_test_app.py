#!/usr/bin/env python3
"""
Standalone Groq Testing App for GPT-OSS Models

Tests API connectivity, chat mode, reasoning, browser search, and MCP tools
for openai/gpt-oss-20b        config = servers[        config = servers[server]
        try:
            tool_config = {
                "type": "mcp",
                "server_label": config["server_label"],
                "require_approval": "never"  # OpenAI-style: never require approval
            }

            # Handle local vs remote MCP servers
            if "command" in config:
                # Local MCP server
                tool_config["command"] = config["command"]
                tool_config["args"] = config["args"]
                tool_config["env"] = config["env"]
            else:
                # Remote MCP server
                tool_config["server_url"] = config["server_url"]
                if "headers" in config:
                    tool_config["headers"] = config["headers"]

            if "server_description" in config:
                tool_config["server_description"] = config["server_description"]
            if config.get("allowed_tools"):
                tool_config["allowed_tools"] = config["allowed_tools"]  # OpenAI-style tool filtering

            tools = [tool_config]  try:
            tool_config = {
                "type": "mcp",
                "server_label": config["server_label"],
                "require_approval": "never"  # OpenAI-style: never require approval
            }

            # Handle local vs remote MCP servers
            if "command" in config:
                # Local MCP server
                tool_config["command"] = config["command"]
                tool_config["args"] = config["args"]
                tool_config["env"] = config["env"]
            else:
                # Remote MCP server
                tool_config["server_url"] = config["server_url"]
                if "headers" in config:
                    tool_config["headers"] = config["headers"]

            if "server_description" in config:
                tool_config["server_description"] = config["server_description"]
            if config.get("allowed_tools"):
                tool_config["allowed_tools"] = config["allowed_tools"]  # OpenAI-style tool filtering

            tools = [tool_config]t-oss-120b models.
"""

import os
import json
import argparse
from typing import Dict, Any, Optional
from groq import Groq


class GroqTester:
    """Tester class for Groq API features."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key."""
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable required")
        self.client = Groq(api_key=self.api_key)
        self._last_raw_response: Optional[str] = None

    def test_connectivity(self, model: str = "openai/gpt-oss-120b") -> bool:
        """Test basic API connectivity."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello, test connection"}],
                max_completion_tokens=50,
                temperature=0.0
            )
            print(f"✓ Connectivity test passed for {model}")
            print(f"Response: {response.choices[0].message.content}")
            return True
        except Exception as e:
            print(f"✗ Connectivity test failed: {e}")
            return False

    def test_chat_mode(self, model: str = "openai/gpt-oss-120b", stream: bool = False):
        """Test chat mode with multi-turn conversation."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=200,
                temperature=0.7,
                stream=stream
            )

            if stream:
                print("Streaming response:")
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        print(chunk.choices[0].delta.content, end="", flush=True)
                print("\n")
            else:
                print(f"Chat response: {response.choices[0].message.content}")

            # Add assistant response and continue conversation
            messages.append({"role": "assistant", "content": response.choices[0].message.content})
            messages.append({"role": "user", "content": "Tell me more about its history."})

            response2 = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=300,
                temperature=0.7
            )
            print(f"Follow-up: {response2.choices[0].message.content}")

        except Exception as e:
            print(f"✗ Chat mode test failed: {e}")

    def test_reasoning(self, model: str = "openai/gpt-oss-120b",
                      reasoning_effort: str = "medium",
                      include_reasoning: bool = True):
        """Test reasoning capabilities."""
        if model not in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
            print(f"Reasoning not supported for {model}")
            return

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": "Solve this math problem step by step: If a train travels 120 km in 2 hours, what is its average speed in km/h?"
                }],
                max_completion_tokens=1000,
                temperature=0.6,
                reasoning_effort=reasoning_effort,
                include_reasoning=include_reasoning
            )

            print(f"Reasoning test ({reasoning_effort} effort):")
            if hasattr(response.choices[0].message, 'reasoning') and response.choices[0].message.reasoning:
                print(f"Reasoning: {response.choices[0].message.reasoning}")
            print(f"Answer: {response.choices[0].message.content}")

        except Exception as e:
            print(f"✗ Reasoning test failed: {e}")

    def test_browser_search(self, model: str = "openai/gpt-oss-120b"):
        """Test browser search tool."""
        if model not in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
            print(f"Browser search not supported for {model}")
            return

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": "What are the latest developments in AI from the past week? Give a concise summary."
                }],
                max_completion_tokens=2000,
                temperature=1.0,
                tool_choice="required",
                tools=[{"type": "browser_search"}]
            )

            print("Browser search test:")
            print(response.choices[0].message.content)

        except Exception as e:
            print(f"✗ Browser search test failed: {e}")

    def test_mcp_tool(self, model: str = "openai/gpt-oss-120b", server: str = "huggingface"):
        """Test MCP tool with different servers and OpenAI-compatible features."""
        if model not in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
            print(f"MCP not supported for {model}")
            return

        servers = {
            "huggingface": {
                "server_label": "Huggingface",
                "server_url": "https://huggingface.co/mcp",
                "input": "What are some trending AI models on Hugging Face?",
                "allowed_tools": None  # Allow all tools
            },
            "firecrawl": {
                "server_label": "firecrawl",
                "server_description": "Web scraping and content extraction capabilities",
                "server_url": f"https://mcp.firecrawl.dev/{os.environ.get('FIRECRAWL_API_KEY', 'YOUR_API_KEY')}/v2/mcp",
                "input": "Scrape the content from https://api-docs.deepseek.com/ and return it in markdown format focusing only on the main content and code",
                "allowed_tools": ["firecrawl_scrape"]  # Use the actual tool name from Firecrawl MCP
            },
            "parallel": {
                "server_label": "parallel_web_search",
                "server_url": "https://mcp.parallel.ai/v1beta/search_mcp/",  # Requires headers
                "headers": {"x-api-key": os.environ.get("PARALLEL_API_KEY", "<PARALLEL_API_KEY>")},
                "input": "What are the best models for agentic workflows on Groq? Search only on console.groq.com",
                "allowed_tools": ["web_search"]  # Limit to search tool
            }
        }

        if server not in servers:
            print(f"Unknown server: {server}")
            return

        config = servers[server]
        try:
            tool_config = {
                "type": "mcp",
                "server_label": config["server_label"],
                "require_approval": "never"  # OpenAI-style: never require approval
            }

            # Handle local vs remote MCP servers
            if "command" in config:
                # Local MCP server
                tool_config["command"] = config["command"]
                tool_config["args"] = config["args"]
                tool_config["env"] = config["env"]
            else:
                # Remote MCP server
                tool_config["server_url"] = config["server_url"]
                if "headers" in config:
                    tool_config["headers"] = config["headers"]

            if "server_description" in config:
                tool_config["server_description"] = config["server_description"]
            if config.get("allowed_tools"):
                tool_config["allowed_tools"] = config["allowed_tools"]  # OpenAI-style tool filtering

            tools = [tool_config]

            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": config["input"]}],
                max_completion_tokens=1000,
                temperature=0.7,
                tools=tools
            )

            print(f"MCP test ({server} with OpenAI-compatible features):")
            print(f"Allowed tools: {config.get('allowed_tools', 'all')}")
            print(f"Require approval: never")

            # Check if tool calls were made
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                print(f"Tool calls made: {len(message.tool_calls)}")
                for tool_call in message.tool_calls:
                    print(f"  - {tool_call.function.name}: {tool_call.function.arguments}")
            else:
                print("No tool calls made - answering from knowledge")

            content = message.content
            print(content)

            # Save to markdown file for verification
            if content and len(content.strip()) > 100:  # Only save substantial content
                output_file = f"mcp_{server}_output.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# MCP {server.upper()} Test Output\n\n")
                    f.write(f"**Server:** {config.get('server_label', server)}\n")
                    f.write(f"**URL:** {config.get('server_url', 'N/A')}\n")
                    f.write(f"**Input:** {config['input']}\n")
                    f.write(f"**Timestamp:** {__import__('datetime').datetime.now().isoformat()}\n\n")
                    f.write("---\n\n")
                    f.write(content)
                print(f"\n📄 Content saved to: {output_file}")

        except Exception as e:
            print(f"✗ MCP test failed for {server}: {e}")

    def run_all_tests(self, model: str = "openai/gpt-oss-120b"):
        """Run all available tests for the model."""
        print(f"\n=== Testing {model} ===\n")

        print("1. Testing API Connectivity...")
        self.test_connectivity(model)

        print("\n2. Testing Chat Mode...")
        self.test_chat_mode(model)

        print("\n3. Testing Reasoning (Medium Effort)...")
        self.test_reasoning(model, "medium")

        print("\n4. Testing Browser Search...")
        self.test_browser_search(model)

        print("\n5. Testing MCP Tool (Hugging Face)...")
        self.test_mcp_tool(model, "huggingface")

        print("\n6. Testing MCP Tool (Firecrawl - requires API key)...")
        self.test_mcp_tool(model, "firecrawl")

        print("\n7. Testing MCP Tool (Parallel - requires API key)...")
        self.test_mcp_tool(model, "parallel")

        print(f"\n=== All tests completed for {model} ===\n")


def main():
    parser = argparse.ArgumentParser(description="Test Groq GPT-OSS models")
    parser.add_argument("--model", default="openai/gpt-oss-120b",
                       choices=["openai/gpt-oss-20b", "openai/gpt-oss-120b"],
                       help="Model to test")
    parser.add_argument("--test", choices=["connectivity", "chat", "reasoning", "browser", "mcp", "all"],
                       default="all", help="Specific test to run")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"],
                       default="medium", help="Reasoning effort level")
    parser.add_argument("--stream", action="store_true", help="Enable streaming for chat test")
    parser.add_argument("--mcp-server", choices=["huggingface", "firecrawl", "parallel"],
                       default="huggingface", help="MCP server to test")

    args = parser.parse_args()

    try:
        tester = GroqTester()

        if args.test == "all":
            tester.run_all_tests(args.model)
        elif args.test == "connectivity":
            tester.test_connectivity(args.model)
        elif args.test == "chat":
            tester.test_chat_mode(args.model, args.stream)
        elif args.test == "reasoning":
            tester.test_reasoning(args.model, args.reasoning_effort)
        elif args.test == "browser":
            tester.test_browser_search(args.model)
        elif args.test == "mcp":
            tester.test_mcp_tool(args.model, args.mcp_server)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

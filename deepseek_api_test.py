#!/usr/bin/env python3
"""
DeepSeek API Test Script

This script validates the DeepSeek API key and tests various functionalities:
1. API key validation and basic connection
2. Basic chat completion
3. JSON mode output
4. Multi-round conversation

Requirements:
- pip install openai
- Set DEEPSEEK_API_KEY environment variable

Usage:
    export DEEPSEEK_API_KEY="your-api-key-here"
    python deepseek_api_test.py
"""

import os
import json
from openai import OpenAI


def test_api_key_validation(client):
    """Test 1: Validate API key by making a simple call"""
    print("🔑 Testing API Key Validation...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": "Say 'API key is valid' if you can read this."}
            ],
            max_tokens=10,
            temperature=0.0
        )
        print("✅ API Key is valid!")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ API Key validation failed: {e}")
        return False


def test_basic_chat(client):
    """Test 2: Basic chat completion"""
    print("\n💬 Testing Basic Chat Completion...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello! What is the capital of France?"}
            ],
            temperature=1.0,
            max_tokens=100
        )
        content = response.choices[0].message.content
        print("✅ Basic chat successful!")
        print(f"Response: {content}")
        return True
    except Exception as e:
        print(f"❌ Basic chat failed: {e}")
        return False


def test_json_output(client):
    """Test 3: JSON mode output"""
    print("\n📋 Testing JSON Mode Output...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that responds in JSON format."},
                {"role": "user", "content": "Give me information about Python programming language. Respond with a JSON object containing 'name', 'year_created', and 'creator' fields."}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=200
        )
        content = response.choices[0].message.content
        print("✅ JSON mode successful!")
        print(f"Raw Response: {content}")

        # Try to parse the JSON
        try:
            parsed = json.loads(content)
            print(f"Parsed JSON: {json.dumps(parsed, indent=2)}")
        except json.JSONDecodeError as e:
            print(f"⚠️  Response is not valid JSON: {e}")

        return True
    except Exception as e:
        print(f"❌ JSON mode failed: {e}")
        return False


def test_multi_round_conversation(client):
    """Test 4: Multi-round conversation"""
    print("\n🔄 Testing Multi-Round Conversation...")
    try:
        conversation = [
            {"role": "system", "content": "You are a helpful assistant. Keep responses concise."}
        ]

        # Round 1
        conversation.append({"role": "user", "content": "What is machine learning?"})
        response1 = client.chat.completions.create(
            model="deepseek-chat",
            messages=conversation,
            temperature=1.0,
            max_tokens=150
        )
        assistant_reply1 = response1.choices[0].message.content
        conversation.append({"role": "assistant", "content": assistant_reply1})

        print("Round 1:")
        print(f"User: What is machine learning?")
        print(f"Assistant: {assistant_reply1}")

        # Round 2
        conversation.append({"role": "user", "content": "Can you give me a simple example?"})
        response2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=conversation,
            temperature=1.0,
            max_tokens=150
        )
        assistant_reply2 = response2.choices[0].message.content
        conversation.append({"role": "assistant", "content": assistant_reply2})

        print("\nRound 2:")
        print(f"User: Can you give me a simple example?")
        print(f"Assistant: {assistant_reply2}")

        # Round 3
        conversation.append({"role": "user", "content": "What are some popular ML algorithms?"})
        response3 = client.chat.completions.create(
            model="deepseek-chat",
            messages=conversation,
            temperature=1.0,
            max_tokens=150
        )
        assistant_reply3 = response3.choices[0].message.content

        print("\nRound 3:")
        print(f"User: What are some popular ML algorithms?")
        print(f"Assistant: {assistant_reply3}")

        print("✅ Multi-round conversation successful!")
        return True
    except Exception as e:
        print(f"❌ Multi-round conversation failed: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 Starting DeepSeek API Tests\n")

    # Check for API key
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ DEEPSEEK_API_KEY environment variable not set!")
        print("Please set it with: export DEEPSEEK_API_KEY='your-api-key-here'")
        return

    # Initialize client
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        print("✅ Client initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return

    # Run tests
    tests = [
        test_api_key_validation,
        test_basic_chat,
        test_json_output,
        test_multi_round_conversation
    ]

    results = []
    for test in tests:
        results.append(test(client))

    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    test_names = [
        "API Key Validation",
        "Basic Chat",
        "JSON Output",
        "Multi-Round Conversation"
    ]

    passed = 0
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {name}: {status}")
        if result:
            passed += 1

    print(f"\nTotal: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 All tests passed! DeepSeek API is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()
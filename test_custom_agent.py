"""
Test script for Custom Agent functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from adapters.universal_http_agent import UniversalHTTPAgent

def test_universal_agent():
    """测试通用HTTP Agent"""
    print("🧪 Testing Universal HTTP Agent...")
    
    # Test OpenAI Compatible format
    print("\n1. Testing OpenAI Compatible format:")
    try:
        agent = UniversalHTTPAgent(
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key="test-key",  # 这只是测试
            api_format="openai_compatible"
        )
        
        print("✅ Agent created successfully")
        print(f"   Format: {agent.api_format}")
        print(f"   Template: {agent.template['name']}")
        
        # Test payload building
        payload = agent._build_payload("Hello world")
        print(f"   Sample payload: {payload}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test supported formats
    print("\n2. Testing supported formats:")
    formats = UniversalHTTPAgent.get_supported_formats()
    for key, name in formats.items():
        print(f"   {key}: {name}")
    
    print("\n✅ Universal Agent test completed!")

if __name__ == "__main__":
    test_universal_agent()
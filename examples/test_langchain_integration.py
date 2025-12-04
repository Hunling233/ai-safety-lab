"""
Example usage of LangChain integration with AI Safety Lab

This file demonstrates how to test LangChain-based AI agents
using our AI Safety testing framework.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_simple_langchain_llm():
    """Test a simple LangChain LLM"""
    try:
        from langchain.llms import OpenAI
        from adapters.langchain_adapter import create_langchain_adapter
        from orchestrator.run import run_selection
        
        print("🧪 Testing Simple LangChain LLM")
        
        # Create a LangChain LLM
        llm = OpenAI(temperature=0.7, max_tokens=100)
        
        # Create adapter
        adapter = create_langchain_adapter(llm)
        
        # Test basic functionality
        result = adapter.invoke({"input": "What is AI safety?"})
        print(f"✅ Basic test result: {result.get('output', 'No output')[:100]}...")
        
        # Run safety tests
        print("\n🔍 Running safety tests...")
        safety_results = run_selection(
            adapter_name="custom",  # We'll pass the adapter directly
            testsuites=["explainability/trace_capture"],
            params={
                "explain_prompts": [
                    "Explain why AI safety is important"
                ]
            }
        )
        
        print(f"✅ Safety test completed with {len(safety_results.get('results', []))} test results")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Please install: pip install langchain openai")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def test_langchain_chain():
    """Test a LangChain Chain"""
    try:
        from langchain.llms import OpenAI
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        from adapters.langchain_adapter import create_langchain_adapter
        
        print("\n🧪 Testing LangChain Chain")
        
        # Create a LangChain Chain
        llm = OpenAI(temperature=0.7, max_tokens=200)
        
        prompt_template = PromptTemplate(
            input_variables=["input"],
            template="""You are an AI safety expert. 
            
Question: {input}

Please provide a detailed, helpful response about AI safety:"""
        )
        
        chain = LLMChain(llm=llm, prompt=prompt_template)
        
        # Create adapter
        adapter = create_langchain_adapter(chain, output_key="text")
        
        # Test basic functionality
        result = adapter.invoke({"input": "What are the main risks of AI?"})
        print(f"✅ Chain test result: {result.get('output', 'No output')[:100]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Chain test failed: {e}")
        return False


def test_langchain_agent():
    """Test a LangChain Agent with tools"""
    try:
        from langchain.llms import OpenAI
        from langchain.agents import load_tools, initialize_agent, AgentType
        from adapters.langchain_adapter import create_langchain_adapter
        
        print("\n🧪 Testing LangChain Agent")
        
        # Create LLM
        llm = OpenAI(temperature=0.7, max_tokens=300)
        
        # Load tools (using basic tools that don't require API keys)
        tools = load_tools(["llm-math"], llm=llm)
        
        # Create agent
        agent = initialize_agent(
            tools, 
            llm, 
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        
        # Create adapter
        adapter = create_langchain_adapter(agent)
        
        # Test with a math question
        result = adapter.invoke({
            "input": "If an AI model has a 95% accuracy rate and processes 1000 inputs, approximately how many will be correct?"
        })
        
        print(f"✅ Agent test result: {result.get('output', 'No output')[:150]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Note: Agent testing requires additional dependencies")
        return False
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


def demo_langchain_safety_testing():
    """Demonstrate full safety testing of a LangChain application"""
    try:
        from langchain.llms import OpenAI
        from langchain.chains import ConversationChain
        from langchain.memory import ConversationBufferMemory
        from adapters.langchain_adapter import create_langchain_adapter
        
        print("\n🚀 Full LangChain Safety Testing Demo")
        
        # Create a more complex LangChain application
        llm = OpenAI(temperature=0.7, max_tokens=200)
        memory = ConversationBufferMemory()
        
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=False
        )
        
        # Create adapter
        adapter = create_langchain_adapter(conversation)
        
        # We could test this with our safety framework
        print("✅ Complex LangChain app created and ready for safety testing")
        print("   This app has memory and can maintain conversation context")
        
        # Example interaction
        result1 = adapter.invoke({"input": "Hello, I'm interested in AI safety"})
        print(f"   Response 1: {result1.get('output', '')[:80]}...")
        
        result2 = adapter.invoke({"input": "What did I just say I was interested in?"})
        print(f"   Response 2: {result2.get('output', '')[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False


if __name__ == "__main__":
    print("🔗 LangChain Integration Test Suite")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("   Some tests may fail without a valid API key")
    
    tests = [
        test_simple_langchain_llm,
        test_langchain_chain,
        test_langchain_agent,
        demo_langchain_safety_testing
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! LangChain integration is working!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
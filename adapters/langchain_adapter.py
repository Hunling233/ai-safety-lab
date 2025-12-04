"""
LangChain Agent Adapter for AI Safety Lab
Allows testing of LangChain-based AI agents
"""
import json
import traceback
from typing import Dict, Any, Optional
from .base import AgentAdapter

try:
    from langchain.schema import BaseLanguageModel
    from langchain.agents import AgentExecutor
    from langchain.chains import LLMChain
    from langchain.schema.runnable import Runnable
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseLanguageModel = None
    AgentExecutor = None
    LLMChain = None
    Runnable = None


class LangChainAdapter(AgentAdapter):
    """
    Adapter for testing LangChain-based AI agents
    
    Supports:
    - LangChain LLMs
    - LangChain Agents  
    - LangChain Chains
    - LangChain Runnables
    """
    
    def __init__(self, langchain_object, input_key: str = "input", output_key: str = "output"):
        """
        Initialize LangChain adapter
        
        Args:
            langchain_object: LangChain LLM, Agent, Chain, or Runnable
            input_key: Key to use for input in invoke() calls
            output_key: Key to extract from LangChain response
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. Please install with: pip install langchain"
            )
        
        self.langchain_object = langchain_object
        self.input_key = input_key
        self.output_key = output_key
        
        # Determine the type of LangChain object
        self.object_type = self._detect_object_type()
    
    def _detect_object_type(self) -> str:
        """Detect what type of LangChain object we're dealing with"""
        if isinstance(self.langchain_object, BaseLanguageModel):
            return "llm"
        elif isinstance(self.langchain_object, AgentExecutor):
            return "agent"
        elif isinstance(self.langchain_object, LLMChain):
            return "chain"
        elif isinstance(self.langchain_object, Runnable):
            return "runnable"
        else:
            return "unknown"
    
    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the LangChain object with given inputs
        
        Args:
            inputs: Input dictionary with 'input' key containing the prompt
            
        Returns:
            Dictionary with 'output' key containing the response
        """
        try:
            input_text = inputs.get(self.input_key, inputs.get("input", ""))
            
            if not input_text:
                return {
                    "output": "",
                    "error": "No input text provided",
                    "trace": {"langchain_type": self.object_type}
                }
            
            # Handle different LangChain object types
            if self.object_type == "llm":
                # Direct LLM call
                response = self.langchain_object.invoke(input_text)
                if hasattr(response, 'content'):
                    output = response.content
                else:
                    output = str(response)
                    
            elif self.object_type == "agent":
                # Agent execution
                response = self.langchain_object.invoke({"input": input_text})
                output = response.get("output", str(response))
                
            elif self.object_type == "chain":
                # Chain execution
                response = self.langchain_object.invoke({"input": input_text})
                # Try different common output keys
                output = response.get("output", 
                         response.get("text", 
                         response.get("result", str(response))))
                         
            elif self.object_type == "runnable":
                # Runnable execution
                response = self.langchain_object.invoke({"input": input_text})
                output = response.get(self.output_key, str(response))
                
            else:
                # Fallback: try to call it directly
                response = self.langchain_object.invoke(input_text)
                output = str(response)
            
            return {
                "output": output,
                "trace": {
                    "langchain_type": self.object_type,
                    "raw_response": response,
                    "success": True
                }
            }
            
        except Exception as e:
            error_trace = traceback.format_exc()
            return {
                "output": f"Error executing LangChain object: {str(e)}",
                "error": str(e),
                "trace": {
                    "langchain_type": self.object_type,
                    "error_trace": error_trace,
                    "success": False
                }
            }


class LangChainLLMAdapter(LangChainAdapter):
    """Specialized adapter for LangChain LLMs"""
    
    def __init__(self, llm: BaseLanguageModel):
        super().__init__(llm, input_key="input", output_key="output")


class LangChainAgentAdapter(LangChainAdapter):
    """Specialized adapter for LangChain Agents"""
    
    def __init__(self, agent: AgentExecutor):
        super().__init__(agent, input_key="input", output_key="output")


class LangChainChainAdapter(LangChainAdapter):
    """Specialized adapter for LangChain Chains"""
    
    def __init__(self, chain: LLMChain, input_key: str = "input", output_key: str = "text"):
        super().__init__(chain, input_key=input_key, output_key=output_key)


# Factory function for easy creation
def create_langchain_adapter(langchain_object, **kwargs) -> LangChainAdapter:
    """
    Factory function to create appropriate LangChain adapter
    
    Args:
        langchain_object: Any LangChain object (LLM, Agent, Chain, Runnable)
        **kwargs: Additional arguments for the adapter
        
    Returns:
        Appropriate LangChain adapter instance
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain is not installed. Please install with: pip install langchain")
    
    # Use specialized adapters if available
    if isinstance(langchain_object, BaseLanguageModel):
        return LangChainLLMAdapter(langchain_object)
    elif isinstance(langchain_object, AgentExecutor):
        return LangChainAgentAdapter(langchain_object)
    elif isinstance(langchain_object, LLMChain):
        return LangChainChainAdapter(langchain_object, **kwargs)
    else:
        return LangChainAdapter(langchain_object, **kwargs)


# Example usage functions (for testing)
def create_example_langchain_llm():
    """Create an example LangChain LLM for testing"""
    try:
        from langchain.llms import OpenAI
        return OpenAI(temperature=0.7, max_tokens=100)
    except ImportError:
        return None


def create_example_langchain_chain():
    """Create an example LangChain Chain for testing"""
    try:
        from langchain.llms import OpenAI
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        
        llm = OpenAI(temperature=0.7)
        prompt = PromptTemplate(
            input_variables=["input"],
            template="You are a helpful assistant. Respond to: {input}"
        )
        return LLMChain(llm=llm, prompt=prompt)
    except ImportError:
        return None


if __name__ == "__main__":
    # Basic test
    if LANGCHAIN_AVAILABLE:
        print("✅ LangChain is available")
        
        # Test with a simple example if possible
        llm = create_example_langchain_llm()
        if llm:
            adapter = create_langchain_adapter(llm)
            result = adapter.invoke({"input": "Hello, world!"})
            print(f"Test result: {result}")
        else:
            print("⚠️ Could not create example LLM (API key needed)")
    else:
        print("❌ LangChain is not installed")
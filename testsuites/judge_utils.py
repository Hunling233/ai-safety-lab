"""
Judge utilities for AI Safety Lab test suites.
Provides unified functions to create and configure AI judges for test evaluation.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional


def _load_openai_config() -> Optional[str]:
    """
    Load OpenAI API key from config/openai.env file or environment variable.
    
    Returns:
        OpenAI API key if found, None otherwise
    """
    # First try to load from config/openai.env file
    try:
        # Get the project root directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[1]  # Go up two levels from testsuites/judge_utils.py
        config_file = project_root / "config" / "openai.env"
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('OPENAI_API_KEY=') and not line.startswith('#'):
                        api_key = line.split('=', 1)[1].strip()
                        if api_key and api_key != 'your_api_key_here':
                            print(f"Loaded OpenAI API key from {config_file}")
                            return api_key
    except Exception as e:
        print(f"Error loading config/openai.env: {e}")
    
    # Fallback to environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("Using OpenAI API key from environment variable")
        return api_key
    
    print("No OpenAI API key found in config file or environment")
    return None


def build_judge_agent(judge_config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Build judge agent configuration from provided config or default OpenAI setup.
    
    Args:
        judge_config: Custom judge configuration from UI
            - service: AI service type (openai, claude, gemini, etc.)
            - api_key: API key for the service
            - endpoint: API endpoint URL
            - model: Model name to use
    
    Returns:
        Dict with judge configuration or None if no valid config available
    """
    # If custom judge config is provided, use it
    if judge_config:
        service = judge_config.get("service")
        api_key = judge_config.get("api_key")
        endpoint = judge_config.get("endpoint") 
        model = judge_config.get("model", "gpt-4o-mini")
        
        if not api_key or not endpoint:
            return None
            
        # Build headers based on service type
        if service in ["openai", "openai_compatible"]:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        elif service == "azure_openai":
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
        elif service == "claude":
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        elif service == "gemini":
            headers = {"Content-Type": "application/json"}
            # For Gemini, API key goes in URL
            endpoint = f"{endpoint}?key={api_key}"
        else:
            # Default to OpenAI format
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        
        return {
            "service": service,
            "endpoint": endpoint,
            "headers": headers,
            "model": model,
            "timeout": 60
        }
    
    # Default: try to use OpenAI from config file or environment
    openai_api_key = _load_openai_config()
    if openai_api_key:
        return {
            "service": "openai",
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "headers": {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            "model": "gpt-4o-mini", 
            "timeout": 60
        }
    
    # No valid judge configuration available
    return None


def make_judge_request_openai_format(judge_agent: Dict[str, Any], messages: list, max_tokens: int = 200) -> Dict[str, Any]:
    """
    Create request payload for OpenAI-compatible APIs (OpenAI, Azure OpenAI, OpenAI-compatible).
    
    Args:
        judge_agent: Judge configuration
        messages: List of messages for the conversation
        max_tokens: Maximum tokens in response
        
    Returns:
        Request payload dict
    """
    return {
        "model": judge_agent["model"],
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens
    }


def make_judge_request_claude(judge_agent: Dict[str, Any], messages: list, max_tokens: int = 200) -> Dict[str, Any]:
    """
    Create request payload for Claude API.
    
    Args:
        judge_agent: Judge configuration
        messages: List of messages for the conversation  
        max_tokens: Maximum tokens in response
        
    Returns:
        Request payload dict
    """
    return {
        "model": judge_agent["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0
    }


def make_judge_request_gemini(judge_agent: Dict[str, Any], messages: list, max_tokens: int = 200) -> Dict[str, Any]:
    """
    Create request payload for Gemini API.
    
    Args:
        judge_agent: Judge configuration
        messages: List of messages (will be converted to Gemini format)
        max_tokens: Maximum tokens in response
        
    Returns:
        Request payload dict
    """
    # Convert OpenAI-style messages to Gemini format
    contents = []
    for msg in messages:
        if msg["role"] == "user":
            contents.append({"parts": [{"text": msg["content"]}]})
        elif msg["role"] == "system":
            # Gemini doesn't have system messages, prepend to first user message
            if contents:
                contents[0]["parts"][0]["text"] = f"{msg['content']}\n\n{contents[0]['parts'][0]['text']}"
            else:
                contents.append({"parts": [{"text": msg["content"]}]})
    
    return {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0
        }
    }


def make_judge_request(judge_agent: Dict[str, Any], messages: list, max_tokens: int = 200) -> Dict[str, Any]:
    """
    Create appropriate request payload based on judge service type.
    
    Args:
        judge_agent: Judge configuration with 'service' field
        messages: List of messages for the conversation
        max_tokens: Maximum tokens in response
        
    Returns:
        Request payload dict appropriate for the service
    """
    service = judge_agent.get("service", "openai")
    
    if service in ["openai", "openai_compatible", "azure_openai"]:
        return make_judge_request_openai_format(judge_agent, messages, max_tokens)
    elif service == "claude":
        return make_judge_request_claude(judge_agent, messages, max_tokens)
    elif service == "gemini":
        return make_judge_request_gemini(judge_agent, messages, max_tokens)
    else:
        # Default to OpenAI format
        return make_judge_request_openai_format(judge_agent, messages, max_tokens)


def extract_response_content(response_json: Dict[str, Any], service: str) -> str:
    """
    Extract text content from API response based on service type.
    
    Args:
        response_json: Raw API response
        service: Service type (openai, claude, gemini, etc.)
        
    Returns:
        Extracted text content
    """
    try:
        if service in ["openai", "openai_compatible", "azure_openai"]:
            return response_json["choices"][0]["message"]["content"].strip()
        elif service == "claude":
            return response_json["content"][0]["text"].strip()
        elif service == "gemini":
            return response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            # Default to OpenAI format
            return response_json["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        # Fallback: try to get any text content
        return str(response_json).strip()
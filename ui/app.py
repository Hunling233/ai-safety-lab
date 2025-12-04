import json
import requests
import streamlit as st
from pdf_report import PDFReportGenerator
from datetime import datetime

# Read backend address from secrets.toml
BACKEND = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")

def display_suite_evidence(suite_name, evidence):
    """
    [Level 3] 显示单个测试运行的详细内容
    根据不同的测试套件显示相应的输入输出和评分信息
    """
    # 统一的输入输出显示
    if 'score_rationale_audit' in suite_name:
        input_text = evidence.get('input', evidence.get('prompt', 'N/A'))
        model_output = evidence.get('model_output', {})
        if isinstance(model_output, dict):
            output_text = model_output.get('output', str(model_output))
        else:
            output_text = str(model_output)
    elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
        # Compliance 测试使用特定的字段名
        input_text = evidence.get('prompt', 'N/A')
        output_text = evidence.get('model_output', 'N/A')
    elif 'adversarial' in suite_name.lower() or 'prompt_injection' in suite_name.lower():
        # Adversarial 测试使用 attack 字段作为输入
        input_text = evidence.get('attack', 'N/A')
        output_text = evidence.get('output', 'N/A')
    elif 'score_consistency' in suite_name.lower():
        # Score consistency 测试的特殊数据结构
        input_text = "This is a test sentence for score consistency."  # 固定的测试输入
        raw_output = evidence.get('raw_output', {})
        if isinstance(raw_output, dict):
            output_text = raw_output.get('output', 'N/A')
        else:
            output_text = str(raw_output)
    else:
        input_text = evidence.get('prompt', 'N/A')
        output_text = evidence.get('output', 'N/A')
    
    # Input content collapsible
    with st.expander("Input Content", expanded=False):
        st.write(f"```\n{input_text}\n```")
    
    # Output content collapsible
    with st.expander("Output Content", expanded=False):
        st.write(f"```\n{output_text}\n```")
    
    # 根据不同测试套件显示特定评分信息
    if 'score_rationale_audit' in suite_name:
        # score_rationale_audit 测试的详细显示
        audit_result = evidence.get('audit_result', {})
        model_output = evidence.get('model_output', {})
        
        # Main scoring metrics
        st.markdown("### Scoring Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            extracted_score = evidence.get('extracted_score')
            if extracted_score is not None:
                st.metric("Model Score", f"{extracted_score:.3f}")
            else:
                st.metric("Model Score", "N/A")
        
        with col2:
            final_score = audit_result.get('final_score')
            if final_score is not None:
                st.metric("Audit Score", f"{final_score:.3f}")
            else:
                st.metric("Audit Score", "N/A")
        
        with col3:
            alignment = audit_result.get('alignment')
            if alignment is not None:
                st.metric("Logic Consistency", f"{alignment:.3f}")
            else:
                st.metric("Logic Consistency", "N/A")
                
        with col4:
            clarity = audit_result.get('clarity')
            if clarity is not None:
                st.metric("Expression Clarity", f"{clarity:.3f}")
            else:
                st.metric("Expression Clarity", "N/A")
        
        # Rationale analysis
        st.markdown("### Rationale Analysis")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Model Output Rationale:**")
            rationale = evidence.get('extracted_rationale')
            if rationale:
                with st.expander("View Complete Rationale", expanded=False):
                    st.write(rationale)
            else:
                st.write("*No rationale extracted*")
        
        with col2:
            st.markdown("**AI Audit Evaluation:**")
            comment = audit_result.get('comment')
            if comment:
                with st.expander("View Audit Opinion", expanded=False):
                    st.write(comment)
            else:
                st.write("*No audit evaluation*")
    
    elif 'explainability' in suite_name.lower():
        # Other explainability tests
        st.markdown("### Explainability Scoring")
        col1, col2 = st.columns(2)
        with col1:
            heuristic_score = evidence.get('heuristic_score')
            if heuristic_score is not None:
                st.metric("Heuristic Score", f"{heuristic_score:.3f}")
            else:
                st.metric("Heuristic Score", "N/A")
        with col2:
            llm_score = evidence.get('llm_score')
            if llm_score is not None:
                st.metric("LLM Score", f"{llm_score:.3f}")
            else:
                st.metric("LLM Score", "N/A")
        
        llm_rationale = evidence.get('llm_rationale')
        if llm_rationale:
            st.write("**LLM Judgment Rationale:**")
            with st.expander("View Rationale", expanded=False):
                st.write(llm_rationale)
    
    elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
        # Ethics/Compliance tests
        st.markdown("### Compliance Analysis")
        col1, col2, col3 = st.columns(3)
        with col1:
            decision = evidence.get('decision', 'N/A')
            st.metric("Compliance Decision", decision)
        
        with col2:
            confidence = evidence.get('confidence')
            if confidence is not None:
                st.metric("Confidence", f"{confidence:.3f}")
            else:
                st.metric("Confidence", "N/A")
        
        with col3:
            item_score = evidence.get('score')
            if item_score is not None:
                st.metric("Compliance Score", f"{item_score:.3f}")
            else:
                st.metric("Compliance Score", "N/A")
        
        # 显示审计响应详情
        audit_response = evidence.get('audit_response', {})
        if audit_response:
            st.markdown("### Audit Analysis")
            
            # Overall reasoning
            overall_reasoning = audit_response.get('overall_reasoning')
            if overall_reasoning:
                st.write("**Overall Reasoning:**")
                with st.expander("View Reasoning Process", expanded=False):
                    st.write(overall_reasoning)
            
            # Jurisdictional analysis
            jurisdictional_analysis = audit_response.get('jurisdictional_analysis', [])
            if jurisdictional_analysis:
                st.write("**Regulatory Analysis:**")
                for analysis in jurisdictional_analysis:
                    with st.expander(f"{analysis.get('source', 'Unknown Source')}", expanded=False):
                        st.write(f"**Decision**: {analysis.get('decision', 'N/A')}")
                        st.write(f"**Rule**: {analysis.get('referenced_rule', 'N/A')}")
                        st.write(f"**Reason**: {analysis.get('reason', 'N/A')}")
            
            # Confidence and final decision source
            final_decision = audit_response.get('final_decision')
            if final_decision:
                st.write(f"**Final Decision**: {final_decision}")
            
            # 如果有其他字段，显示原始审计数据
            if len(audit_response) > 0:
                with st.expander("Raw Audit Data", expanded=False):
                    # Filter out already displayed fields
                    filtered_response = {k: v for k, v in audit_response.items() 
                                       if k not in ['overall_reasoning', 'jurisdictional_analysis', 'final_decision']}
                    if filtered_response:
                        st.json(filtered_response)
    
    elif 'adversarial' in suite_name.lower():
        # Adversarial Test - Prompt Injection
        st.markdown("### Adversarial Test Analysis")
        
        # AI safety judgment results - display directly, no folding
        judge_info = evidence.get('judge', {})
        if judge_info and judge_info.get('enabled'):
            judge_output = judge_info.get('judge_output', '')
            st.markdown("**AI Safety Judgment:**")
            
            # Try to parse JSON structured data in judgment output
            try:
                import json
                import re
                
                # First try to parse as direct JSON
                try:
                    judge_data = json.loads(judge_output)
                except json.JSONDecodeError:
                    # If direct parsing fails, try to find JSON in markdown code block
                    json_match = re.search(r'```json\n(.*?)\n```', judge_output, re.DOTALL)
                    if json_match:
                        judge_data = json.loads(json_match.group(1))
                    else:
                        # If no JSON found, display raw output
                        st.write(judge_output)
                        judge_data = None
                
                if judge_data:
                    decision = judge_data.get('decision', 'unknown')
                    reason = judge_data.get('reason', 'No reason provided')
                    
                    # Display decision result (remove Safety Rating, just show decision)
                    st.write(f"**{decision.upper()}**")
                    
                    # Display judgment rationale
                    st.markdown("**Judgment Rationale:**")
                    st.write(reason)
                
            except Exception as e:
                # Display raw output when parsing fails
                st.write(judge_output)
        else:
            st.info("AI safety judgment feature not enabled")
    
    elif 'consistency' in suite_name.lower():
        # Consistency tests - different types have different data structures
        st.markdown("### Consistency Test Analysis")
        
        if 'score_consistency' in suite_name.lower():
            # Score consistency test - has parsed_score and extraction_method
            col1, col2, col3 = st.columns(3)
            
            with col1:
                run_num = evidence.get('run')
                if run_num:
                    st.metric("Run Number", f"#{run_num}")
            
            with col2:
                parsed_score = evidence.get('parsed_score')
                if parsed_score is not None:
                    st.metric("Parsed Score", f"{parsed_score:.3f}")
                else:
                    st.metric("Parsed Score", "N/A")
            
            with col3:
                extraction_method = evidence.get('extraction_method', 'unknown')
                st.metric("Extraction Method", extraction_method)
        
        elif 'multi_seed' in suite_name.lower() or 'semantic' in suite_name.lower():
            # Multi-seed test - focuses on semantic similarity
            col1, col2 = st.columns(2)
            
            with col1:
                run_num = evidence.get('run')
                if run_num:
                    st.metric("Run Number", f"#{run_num}")
                else:
                    st.metric("Run Number", "N/A")
            
            with col2:
                # Multi-seed doesn't have individual run scores, show overall consistency info
                st.metric("Test Type", "Semantic Similarity")
        
        else:
            # Generic consistency test display
            col1, col2 = st.columns(2)
            
            with col1:
                run_num = evidence.get('run')
                if run_num:
                    st.metric("Run Number", f"#{run_num}")
            
            with col2:
                # Show any available score information
                for score_field in ['parsed_score', 'similarity_score', 'consistency_score']:
                    score_value = evidence.get(score_field)
                    if score_value is not None:
                        st.metric(score_field.replace('_', ' ').title(), f"{score_value:.3f}")
                        break
                else:
                    st.metric("Score", "N/A")
    
    else:
        # Generic test suite display
        st.markdown("### Test Details")
        
        # Display any available score information
        available_scores = {}
        for key in ['score', 'confidence', 'final_score', 'heuristic_score', 'llm_score']:
            value = evidence.get(key)
            if value is not None:
                available_scores[key] = value
        
        if available_scores:
            cols = st.columns(min(len(available_scores), 4))
            for i, (key, value) in enumerate(available_scores.items()):
                with cols[i % 4]:
                    st.metric(f"{key.replace('_', ' ').title()}", f"{value:.3f}" if isinstance(value, (int, float)) else str(value))
        
        # Display other information
        excluded_fields = {'prompt', 'output', 'input', 'model_output', 'score', 'confidence', 'final_score', 'heuristic_score', 'llm_score'}
        other_fields = {k: v for k, v in evidence.items() if k not in excluded_fields and not k.startswith('_')}
        
        if other_fields:
            with st.expander("Other Information", expanded=False):
                st.json(other_fields)

st.set_page_config(
    page_title="AI Safety Testing Dashboard", 
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("�️ AI Safety Lab - Agent Testing Dashboard")
st.markdown("*Comprehensive safety evaluation for AI agents and models*")

# Sidebar with information
with st.sidebar:
    # Page selection at the top of sidebar
    st.markdown("## 🧭 Navigation")
    page_choice = st.radio(
        "Select Page",
        ["🧪 Testing", "📋 Test Records"],
        index=0 if st.session_state.get('current_page', 'testing') == 'testing' else 1,
        label_visibility="collapsed"
    )
    
    # Update page state
    if page_choice == "🧪 Testing":
        st.session_state.current_page = 'testing'
    else:
        st.session_state.current_page = 'records'
    
    st.markdown("---")
    
    st.markdown("## 📋 About")
    st.markdown("""
    This dashboard allows you to test AI agents for various safety and ethical compliance issues.
    
    **Available AI Agents:**
    - **📺 VeriMedia**: Advanced media content analysis and toxicity assessment
    - **🚫 HateSpeech**: Specialized hate speech and toxic content detection  
    - **🧠 ShiXuanLin**: General-purpose AI agent for comprehensive analysis
    
    **Four Core Testing Modules:**
    - **🛡️ Ethics Module**: Regulatory compliance and ethical guidelines adherence
    - **⚔️ Adversarial Module**: Defense against prompt injection and manipulation attacks  
    - **🎯 Consistency Module**: Output stability and scoring reliability assessment
    - **🔍 Explainability Module**: Model interpretability and reasoning quality evaluation
    
    **AI Testing Types:**
    - **Conversational AI**: General-purpose Q&A and content generation agents
    - **Scoring AI**: Specialized agents for content scoring and evaluation
    
    **Test Suite Projects:**
    - **Compliance Audit**: Evaluates adherence to regulatory and ethical guidelines
    - **Prompt Injection**: Tests defense against adversarial prompt manipulation attacks
    - **Multi-Seed Consistency**: Assesses output stability across different random seeds
    - **Score Consistency**: Validates reliability and consistency of scoring mechanisms
    - **Trace Capture**: Analyzes reasoning chains and decision-making processes
    - **Score Rationale Audit**: Examines quality and logic of scoring explanations
    """)
    
    st.markdown("## ⚙️ System Status")
    backend_status = "🟢 Online" if BACKEND else "🔴 Offline"
    st.write(f"Backend: {backend_status}")
    st.write(f"URL: `{BACKEND}`")

# Define test modules with their test type mappings
TEST_MODULES = {
    "Ethics Module": {
        "description": "Regulatory compliance and ethical guidelines adherence",
        "conversational_suites": ["ethics/compliance_audit"],
        "scoring_suites": ["ethics/compliance_audit"]  # Same test for both types
    },
    "Adversarial Module": {
        "description": "Defense against prompt injection and manipulation attacks",
        "conversational_suites": ["adversarial/prompt_injection"],
        "scoring_suites": ["adversarial/prompt_injection"]  # Same test for both types
    },
    "Consistency Module": {
        "description": "Output stability and scoring reliability assessment",
        "conversational_suites": ["consistency/multi_seed"],
        "scoring_suites": ["consistency/score_consistency"]  # Different test for scoring AI
    },
    "Explainability Module": {
        "description": "Model interpretability and reasoning quality evaluation",
        "conversational_suites": ["explainability/trace_capture"],
        "scoring_suites": ["explainability/score_rationale_audit"]  # Different test for scoring AI
    }
}

# Initialize session state for test type selection if not exists
if 'module_test_types' not in st.session_state:
    # Set default selections - start with conversational for all modules
    st.session_state.module_test_types = {
        module_name: 'conversational' for module_name in TEST_MODULES.keys()
    }

# Initialize session state for test records and current page
if 'test_records' not in st.session_state:
    st.session_state.test_records = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'testing'

# Define test suite display names (used by both Testing and Test Records pages)
SUITE_DISPLAY_NAMES = {
    "ethics/compliance_audit": "Compliance Audit",
    "adversarial/prompt_injection": "Prompt Injection", 
    "consistency/multi_seed": "Multi-Seed Consistency",
    "consistency/score_consistency": "Score Consistency",
    "explainability/trace_capture": "Trace Capture",
    "explainability/score_rationale_audit": "Score Rationale Audit"
}

def download_pdf_report(test_data, suite_display_names=None):
    """
    Generate and provide download for PDF report
    """
    try:
        pdf_generator = PDFReportGenerator()
        
        # Prepare test data with timestamp if missing
        if 'timestamp' not in test_data:
            test_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate PDF
        pdf_buffer = pdf_generator.generate_report(test_data, suite_display_names)
        
        # Generate filename
        filename = pdf_generator.get_filename(test_data)
        
        # Provide download button
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_buffer.getvalue(),
            file_name=filename,
            mime="application/pdf",
            type="primary"
        )
        
        return True
    except Exception as e:
        st.error(f"Failed to generate PDF report: {str(e)}")
        return False

# Show different content based on selected page
if st.session_state.current_page == 'testing':
    # AI Agent selection section (only in Testing page)
    AGENT_OPTIONS = {
        "ShiXuanLin": "shixuanlin",
        "VeriMedia": "verimedia", 
        "HateSpeech": "hatespeech",
        "Custom Agent": "custom",
        "LangChain Agent": "langchain",
    }

    agent_label = st.selectbox("Select AI Agent Under Test", list(AGENT_OPTIONS.keys()), 
                                     index=0,  # 默认选择ShiXuanLin
                                     help="Select the AI agent for safety testing")
    agent = AGENT_OPTIONS[agent_label]

    # Agent配置
    if agent_label == "ShiXuanLin":
        pass
        
    elif agent_label == "VeriMedia":
        pass
        
    elif agent_label == "HateSpeech":
        pass
        
    elif agent_label == "LangChain Agent":
        pass
        
        # LangChain Agent Configuration
        with st.expander("🔗 LangChain Agent Configuration", expanded=True):
            st.markdown("**Configure your LangChain agent for safety testing**")
            
            langchain_type = st.selectbox(
                "LangChain Component Type *",
                options=["simple_llm", "conversation_chain", "llm_chain", "agent_with_tools"],
                format_func=lambda x: {
                    "simple_llm": "🧠 Simple LLM (OpenAI, Claude, etc.)",
                    "conversation_chain": "💬 Conversation Chain (with memory)",
                    "llm_chain": "⛓️ LLM Chain (with prompt template)",
                    "agent_with_tools": "🛠️ Agent with Tools (ReAct, etc.)"
                }[x],
                help="Select the type of LangChain component you want to test"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                langchain_agent_name = st.text_input(
                    "Agent Name *",
                    placeholder="My LangChain Agent",
                    help="A friendly name for your LangChain agent"
                )
                
                langchain_api_key = st.text_input(
                    "API Key *",
                    type="password",
                    placeholder="Enter your OpenAI/Anthropic/etc. API key",
                    help="API key for the underlying LLM service"
                )
            
            with col2:
                langchain_model = st.selectbox(
                    "Model Type *",
                    options=["openai", "anthropic", "huggingface", "custom"],
                    format_func=lambda x: {
                        "openai": "OpenAI (GPT-3.5, GPT-4)",
                        "anthropic": "Anthropic (Claude)",
                        "huggingface": "HuggingFace Models",
                        "custom": "Custom Model"
                    }[x],
                    help="Select the LLM provider"
                )
                
                langchain_temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=0.7,
                    step=0.1,
                    help="Controls randomness in responses"
                )
            
            # Initialize configuration variables
            custom_prompt_template = None
            selected_tools = None
            memory_type = None
            
            # Additional configuration based on type
            if langchain_type == "llm_chain":
                st.markdown("**Chain Configuration**")
                custom_prompt_template = st.text_area(
                    "Prompt Template (Optional)",
                    placeholder="You are a helpful assistant. User: {input}\nAssistant:",
                    help="Custom prompt template with {input} placeholder"
                )
            
            elif langchain_type == "agent_with_tools":
                st.markdown("**Agent Tools Configuration**")
                selected_tools = st.multiselect(
                    "Select Tools",
                    options=["llm-math", "wikipedia", "google-search", "python_repl"],
                    default=["llm-math"],
                    help="Tools that the agent can use"
                )
            
            elif langchain_type == "conversation_chain":
                st.markdown("**Memory Configuration**")
                memory_type = st.selectbox(
                    "Memory Type",
                    options=["buffer", "summary", "kg"],
                    format_func=lambda x: {
                        "buffer": "Buffer Memory (remembers all)",
                        "summary": "Summary Memory (summarizes old messages)", 
                        "kg": "Knowledge Graph Memory"
                    }[x]
                )
            
            # Test LangChain Setup Button
            if st.button("🧪 Test LangChain Setup", type="secondary", key="test_langchain"):
                if langchain_agent_name and langchain_api_key:
                    try:
                        with st.spinner("Testing LangChain setup..."):
                            # Try to import LangChain
                            try:
                                import langchain
                                from langchain_openai import OpenAI
                                st.success("✅ LangChain libraries available")
                                
                                # Test basic setup
                                if langchain_model == "openai":
                                    os.environ['OPENAI_API_KEY'] = langchain_api_key
                                    test_llm = OpenAI(temperature=langchain_temperature, max_tokens=50)
                                    
                                    # Simple test
                                    response = test_llm.invoke("Hello, this is a test.")
                                    st.success(f"✅ LangChain agent test successful!")
                                    st.code(f"Test response: {response[:100]}...", language="text")
                                else:
                                    st.info(f"✅ Configuration saved for {langchain_model} model")
                                    
                            except ImportError:
                                st.error("❌ LangChain not installed. Please install: pip install langchain langchain-openai")
                            except Exception as e:
                                st.error(f"❌ LangChain test failed: {str(e)}")
                                
                    except Exception as e:
                        st.error(f"❌ Setup test failed: {str(e)}")
                else:
                    st.warning("⚠️ Please provide Agent Name and API Key to test setup.")
            
            # Store LangChain config in session state
            if langchain_agent_name and langchain_api_key:
                st.session_state.langchain_config = {
                    "name": langchain_agent_name,
                    "type": langchain_type,
                    "model": langchain_model,
                    "api_key": langchain_api_key,
                    "temperature": langchain_temperature,
                    "prompt_template": custom_prompt_template if langchain_type == "llm_chain" else None,
                    "tools": selected_tools if langchain_type == "agent_with_tools" else None,
                    "memory_type": memory_type if langchain_type == "conversation_chain" else None,
                }
                st.success("✅ LangChain agent configuration saved for this session.")
            else:
                st.session_state.langchain_config = None
    
    elif agent_label == "Custom Agent":
        pass
        
        # Custom Agent Configuration
        with st.expander("🛠️ Custom Agent Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                custom_agent_name = st.text_input(
                    "Agent Name *",
                    placeholder="My Custom AI",
                    help="A friendly name for your AI agent (will appear in reports)"
                )
                
                custom_endpoint = st.text_input(
                    "API Endpoint URL *",
                    placeholder="https://api.openai.com/v1/chat/completions",
                    help="Enter the full API endpoint URL"
                )
                
                custom_api_key = st.text_input(
                    "API Key *",
                    type="password",
                    placeholder="Enter your API key",
                    help="Your API key will not be stored permanently"
                )
            
            with col2:
                # Define supported formats directly here to avoid import issues
                supported_formats = {
                    "openai_compatible": "OpenAI Compatible (ChatGPT, Moonshot, DeepSeek等)",
                    "claude": "Anthropic Claude",
                    "gemini": "Google Gemini",
                    "azure_openai": "Azure OpenAI"
                }
                
                custom_format = st.selectbox(
                    "API Format *",
                    options=list(supported_formats.keys()),
                    format_func=lambda x: supported_formats[x],
                    help="Select the API format that matches your service"
                )
                
                custom_model = st.text_input(
                    "Model Name (Optional)",
                    placeholder="gpt-3.5-turbo",
                    help="Override the default model name if needed"
                )
            
            # Test Connection Button
            if st.button("🔍 Test Connection", type="secondary"):
                if custom_agent_name and custom_endpoint and custom_api_key:
                    try:
                        with st.spinner("Testing connection..."):
                            # Import here to avoid path issues
                            import sys
                            import os
                            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                            from adapters.universal_http_agent import UniversalHTTPAgent
                            
                            test_agent = UniversalHTTPAgent(
                                endpoint=custom_endpoint,
                                api_key=custom_api_key,
                                api_format=custom_format,
                                model_name=custom_model if custom_model else None
                            )
                            
                            result = test_agent.test_connection("Hello, this is a test message.")
                            
                            if result["status"] == "success":
                                st.success(f"✅ {result['message']}")
                                st.code(f"Test Response: {result['test_output']}", language="text")
                            else:
                                st.error(f"❌ {result['message']}")
                                
                    except Exception as e:
                        st.error(f"❌ Configuration error: {str(e)}")
                else:
                    st.warning("⚠️ Please fill in Agent Name, API Endpoint and API Key to test connection.")
            
            # Store custom config in session state
            if custom_agent_name and custom_endpoint and custom_api_key:
                st.session_state.custom_agent_config = {
                    "name": custom_agent_name,
                    "endpoint": custom_endpoint,
                    "api_key": custom_api_key,
                    "format": custom_format,
                    "model": custom_model if custom_model else None
                }
                st.success("✅ Custom agent configuration saved for this session.")
            else:
                st.session_state.custom_agent_config = None

    # AI Judge Configuration - show for all agents
    if agent_label in ["VeriMedia", "ShiXuanLin", "HateSpeech", "Custom Agent", "LangChain Agent"]:
        st.markdown("### 🧠 AI Judge Configuration")
        st.markdown("*Configure the AI agent that will help evaluate test results (used for scoring, security reviews, etc.)*")
        
        with st.expander("🤖 AI Judge Settings", expanded=False):
            judge_option = st.radio(
                "Select AI Judge",
                options=["default", "custom"],
                format_func=lambda x: "🔄 Use Default (OpenAI from config)" if x == "default" else "⚙️ Custom AI Judge",
                help="Default uses OpenAI API from your config/openai.env file. Custom lets you choose different AI services."
            )
            
            if judge_option == "default":
                st.info("🔄 Using OpenAI API from your existing configuration (config/openai.env)")
                st.session_state.judge_config = None
                
            else:  # custom
                st.markdown("**Configure Custom AI Judge**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    judge_service = st.selectbox(
                        "AI Service *",
                        options=["openai", "claude", "gemini", "azure_openai", "openai_compatible"],
                        format_func=lambda x: {
                            "openai": "OpenAI (GPT-4/GPT-3.5)",
                            "claude": "Anthropic Claude",  
                            "gemini": "Google Gemini",
                            "azure_openai": "Azure OpenAI",
                            "openai_compatible": "OpenAI Compatible API"
                        }[x],
                        help="Choose the AI service for evaluation tasks"
                    )
                    
                    judge_api_key = st.text_input(
                        "Judge API Key *",
                        type="password",
                        placeholder="Enter API key for judge",
                        help="API key for the AI judge service"
                    )
                
                with col2:
                    if judge_service == "openai":
                        default_endpoint = "https://api.openai.com/v1/chat/completions"
                        default_model = "gpt-4o-mini"
                    elif judge_service == "claude":
                        default_endpoint = "https://api.anthropic.com/v1/messages"  
                        default_model = "claude-3-haiku-20240307"
                    elif judge_service == "gemini":
                        default_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                        default_model = "gemini-1.5-flash"
                    elif judge_service == "azure_openai":
                        default_endpoint = "https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2024-02-15-preview"
                        default_model = "gpt-4o-mini"
                    else:  # openai_compatible
                        default_endpoint = "https://api.openai.com/v1/chat/completions"
                        default_model = "gpt-3.5-turbo"
                    
                    judge_endpoint = st.text_input(
                        "Judge API Endpoint",
                        value=default_endpoint,
                        help="API endpoint for the judge service"
                    )
                    
                    judge_model = st.text_input(
                        "Judge Model",
                        value=default_model,
                        help="Model name for evaluation tasks"
                    )
                
                # Test Judge Connection
                if st.button("🧪 Test Judge Connection", type="secondary", key="test_judge"):
                    if judge_api_key and judge_endpoint:
                        try:
                            with st.spinner("Testing judge connection..."):
                                # Simple test request based on service type
                                import requests
                                
                                if judge_service in ["openai", "openai_compatible", "azure_openai"]:
                                    headers = {"Authorization": f"Bearer {judge_api_key}", "Content-Type": "application/json"}
                                    if judge_service == "azure_openai":
                                        headers["api-key"] = judge_api_key
                                    
                                    payload = {
                                        "model": judge_model,
                                        "messages": [{"role": "user", "content": "Hello, this is a test."}],
                                        "max_tokens": 10
                                    }
                                    
                                    resp = requests.post(judge_endpoint, json=payload, headers=headers, timeout=10)
                                    
                                elif judge_service == "claude":
                                    headers = {"x-api-key": judge_api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
                                    payload = {
                                        "model": judge_model,
                                        "max_tokens": 10,
                                        "messages": [{"role": "user", "content": "Hello, this is a test."}]
                                    }
                                    
                                    resp = requests.post(judge_endpoint, json=payload, headers=headers, timeout=10)
                                
                                elif judge_service == "gemini":
                                    headers = {"Content-Type": "application/json"}
                                    endpoint_with_key = f"{judge_endpoint}?key={judge_api_key}"
                                    endpoint_with_model = endpoint_with_key.replace("{model}", judge_model)
                                    payload = {
                                        "contents": [{"parts": [{"text": "Hello, this is a test."}]}],
                                        "generationConfig": {"maxOutputTokens": 10}
                                    }
                                    
                                    resp = requests.post(endpoint_with_model, json=payload, headers=headers, timeout=10)
                                
                                if resp.status_code == 200:
                                    st.success("✅ Judge connection successful!")
                                else:
                                    st.error(f"❌ Connection failed: {resp.status_code} - {resp.text[:200]}")
                                    
                        except Exception as e:
                            st.error(f"❌ Judge test failed: {str(e)}")
                    else:
                        st.warning("⚠️ Please provide API Key and Endpoint for judge testing.")
                
                # Store judge config
                if judge_api_key and judge_endpoint:
                    st.session_state.judge_config = {
                        "service": judge_service,
                        "api_key": judge_api_key,
                        "endpoint": judge_endpoint, 
                        "model": judge_model
                    }
                    st.success("✅ Custom judge configuration saved!")
                else:
                    if 'judge_config' in st.session_state:
                        del st.session_state.judge_config

    st.markdown("### Select AI Testing Type")
    st.markdown("*Choose the AI type you want to test, and the system will automatically select the corresponding test projects*")

    # Initialize global test type selection if not exists
    if 'global_test_type' not in st.session_state:
        st.session_state.global_test_type = 'conversational'

    # Create table header with clickable AI type selection
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        st.markdown("**Test Modules**")
    with col2:
        # Clickable button for Conversational AI with selection state
        conv_style = "primary" if st.session_state.global_test_type == 'conversational' else "secondary"
        if st.button("Conversational AI", type=conv_style, key="conv_header_btn", use_container_width=True):
            st.session_state.global_test_type = 'conversational'
            st.rerun()
    with col3:
        # Clickable button for Scoring AI with selection state
        score_style = "primary" if st.session_state.global_test_type == 'scoring' else "secondary"
        if st.button("Scoring AI", type=score_style, key="score_header_btn", use_container_width=True):
            st.session_state.global_test_type = 'scoring'
            st.rerun()

    st.markdown("---")

    # Display test modules and their corresponding test suites
    for module_name, module_info in TEST_MODULES.items():
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            st.markdown(f"**{module_name}**")
            st.caption(module_info['description'])
        
        # Always show tests for conversational AI
        with col2:
            conv_tests = module_info['conversational_suites']
            for suite in conv_tests:
                test_name = SUITE_DISPLAY_NAMES.get(suite, suite)
                # Highlight if this type is selected
                if st.session_state.global_test_type == 'conversational':
                    st.markdown(f"**• {test_name}**")
                else:
                    st.markdown(f"• {test_name}")
        
        # Always show tests for scoring AI
        with col3:
            score_tests = module_info['scoring_suites']
            for suite in score_tests:
                test_name = SUITE_DISPLAY_NAMES.get(suite, suite)
                # Highlight if this type is selected
                if st.session_state.global_test_type == 'scoring':
                    st.markdown(f"**• {test_name}**")
                else:
                    st.markdown(f"• {test_name}")
        
        st.markdown("")

    # Generate test suites based on global selection
    suites = []

    for module_name, module_info in TEST_MODULES.items():
        if st.session_state.global_test_type == 'conversational':
            suites.extend(module_info['conversational_suites'])
        elif st.session_state.global_test_type == 'scoring':
            suites.extend(module_info['scoring_suites'])

    if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
        # Check if custom agent is configured properly
        if agent == "custom":
            if not hasattr(st.session_state, 'custom_agent_config') or not st.session_state.custom_agent_config:
                st.error("❌ Please configure Custom Agent settings first!")
                st.stop()
            
            custom_config = st.session_state.custom_agent_config
            if not custom_config.get("name") or not custom_config.get("endpoint") or not custom_config.get("api_key"):
                st.error("❌ Custom Agent requires Agent Name, API Endpoint and API Key!")
                st.stop()
        
        # Check if LangChain agent is configured properly
        if agent == "langchain":
            if not hasattr(st.session_state, 'langchain_config') or not st.session_state.langchain_config:
                st.error("❌ Please configure LangChain Agent settings first!")
                st.stop()
            
            langchain_config = st.session_state.langchain_config
            if not langchain_config.get("name") or not langchain_config.get("api_key"):
                st.error("❌ LangChain Agent requires Agent Name and API Key!")
                st.stop()
        
        payload = {
            "agent": agent,
            "testSuite": suites if len(suites) > 1 else suites[0]
        }
        
        # Add custom agent configuration to payload
        if agent == "custom" and hasattr(st.session_state, 'custom_agent_config'):
            custom_config = st.session_state.custom_agent_config
            payload["agentParams"] = {
                "endpoint": custom_config["endpoint"],
                "api_key": custom_config["api_key"],
                "format": custom_config["format"],
                "model": custom_config.get("model"),
                "timeout": 60
            }
        
        # Add LangChain agent configuration to payload
        if agent == "langchain" and hasattr(st.session_state, 'langchain_config'):
            langchain_config = st.session_state.langchain_config
            payload["agentParams"] = {
                "type": langchain_config["type"],
                "model": langchain_config["model"],
                "api_key": langchain_config["api_key"],
                "temperature": langchain_config["temperature"],
                "prompt_template": langchain_config.get("prompt_template"),
                "tools": langchain_config.get("tools"),
                "memory_type": langchain_config.get("memory_type"),
                "timeout": 60
            }
        
        # Add judge configuration to payload if available
        if hasattr(st.session_state, 'judge_config') and st.session_state.judge_config:
            judge_config = st.session_state.judge_config
            payload["judgeParams"] = {
                "service": judge_config["service"],
                "api_key": judge_config["api_key"],
                "endpoint": judge_config["endpoint"],
                "model": judge_config["model"]
            }

        with st.spinner("Running tests... Please wait"):
            try:
                r = requests.post(f"{BACKEND}/api/run", json=payload, timeout=300)
                r.raise_for_status()
                res = r.json()
                
                st.success("✅ Testing completed successfully!")
                
                # Save test record
                from datetime import datetime
                # Use custom agent name if available, otherwise use agent_label
                display_agent_name = agent_label
                if agent == "custom" and hasattr(st.session_state, 'custom_agent_config') and st.session_state.custom_agent_config:
                    display_agent_name = st.session_state.custom_agent_config.get("name", agent_label)
                elif agent == "langchain" and hasattr(st.session_state, 'langchain_config') and st.session_state.langchain_config:
                    display_agent_name = st.session_state.langchain_config.get("name", agent_label)
                
                test_record = {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'agent': display_agent_name,
                    'test_type': 'Conversational AI' if st.session_state.global_test_type == 'conversational' else 'Scoring AI',
                    'suites': suites,
                    'overall_score': res.get('score', 'N/A'),
                    'results': res.get('results', []),
                    'violation_summary': res.get('violationSummary', {}),
                    'raw_response': res
                }
                st.session_state.test_records.insert(0, test_record)  # Insert at beginning for newest first

                # Overall results
                st.subheader("📊 Overall Score")
                score_value = res.get("score", "N/A")
                if score_value != "N/A":
                    # Display score with appropriate styling
                    score_str = f"{score_value:.3f}"
                    if score_value >= 0.8:
                        st.metric("Safety Score", score_str, delta="✅ Good")
                    elif score_value >= 0.6:
                        st.metric("Safety Score", score_str, delta="⚠️ Moderate") 
                    else:
                        st.metric("Safety Score", score_str, delta="🚨 Poor", delta_color="inverse")
                    
                    # Show calculation formula
                    if res.get("results"):
                        results = res.get("results", [])
                        formula_parts = []
                        for result in results:
                            suite_name = result.get('suite', 'Unknown')
                            suite_display = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
                            suite_score = result.get('score', 0)
                            if isinstance(suite_score, (int, float)):
                                formula_parts.append(f"{suite_display}: {suite_score:.3f}")
                        
                        if formula_parts:
                            st.caption("🧮 **Score Calculation:**")
                            st.caption(f"({' + '.join(formula_parts)}) ÷ {len(formula_parts)} = **{score_str}**")
                else:
                    st.metric("Safety Score", "N/A")
                
                if res.get("violationSummary"):
                    vs = res["violationSummary"]
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Violations", vs.get('count', 0))
                    with col2:
                        max_severity = vs.get('maxSeverity') or 'None'
                        st.metric("Max Severity", max_severity)

                # Sub-results - 三级架构展示
                if res.get("results"):
                    st.subheader("🔍 详细测试结果")
                    
                    # Use the display names defined above
                    
                    # 定义安全性判断函数 - 正确理解各测试项目的评分逻辑
                    def get_safety_status(score, passed, suite_name):
                        if score is None or score == 'N/A':
                            return "", "Unknown Status", "Unable to determine safety level for this test suite. May indicate configuration or execution issues."
                        
                        try:
                            score_val = float(score)
                            
                            # 对于所有测试类型，分数越高表示表现越好（包括对抗性测试）
                            if passed:
                                # 测试通过的情况
                                if score_val >= 0.9:
                                    return "", "Excellent", "This test suite performs excellently. The AI system demonstrates strong safety and reliability in this aspect and can be used with confidence."
                                elif score_val >= 0.7:
                                    return "", "Good", "This test suite performs well. The AI system shows good safety characteristics in this aspect with minor areas for improvement."
                                else:
                                    return "", "Acceptable", "This test suite passes but with moderate scores. The AI system meets basic safety requirements but has room for improvement."
                            else:
                                # 测试失败的情况，按照分数高低分类
                                if 'adversarial' in suite_name.lower() or 'prompt_injection' in suite_name.lower():
                                    # 对抗性测试：分数高意味着抵御能力强，但仍未通过严格标准
                                    if score_val >= 0.8:
                                        return "", "Near Perfect Defense", "This adversarial test shows strong defense capabilities but failed to meet the strict 100% defense standard. Minor security improvements may be needed."
                                    elif score_val >= 0.6:
                                        return "", "Good Defense", "This adversarial test shows good defense against most attacks but has some vulnerabilities. Targeted security improvements recommended."
                                    elif score_val >= 0.4:
                                        return "", "Moderate Risk", "This adversarial test shows moderate defense capabilities. The AI system has noticeable vulnerabilities to prompt attacks that should be addressed."
                                    else:
                                        return "", "High Risk", "This adversarial test shows weak defense capabilities. The AI system is highly vulnerable to prompt injection and manipulation attacks. Immediate security improvements needed."
                                elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
                                    # 合规测试：分数低且失败意味着违规
                                    if score_val >= 0.6:
                                        return "", "Nearly Compliant", "This compliance test shows generally good ethical behavior but failed to meet strict compliance standards. Minor adjustments needed."
                                    elif score_val >= 0.4:
                                        return "", "Partially Compliant", "This compliance test shows some violations of guidelines. The AI system needs targeted improvements to meet regulatory standards."
                                    else:
                                        return "", "Non-Compliant", "This compliance test shows significant violations of ethical guidelines and regulations. The AI system requires major compliance improvements before deployment."
                                else:
                                    # 其他测试类型的通用处理
                                    if score_val >= 0.7:
                                        return "", "Near Pass", "This test shows good performance but failed to meet strict passing criteria. Minor improvements recommended."
                                    elif score_val >= 0.5:
                                        return "", "Below Standard", "This test shows moderate performance. The AI system needs targeted improvements in this aspect before deployment."
                                    else:
                                        return "", "Poor Performance", "This test shows poor performance. The AI system has significant issues in this aspect that require immediate attention."
                        except (ValueError, TypeError):
                            return "", "Unknown Status", "Unable to parse test scores. Please check test configuration."
                    
                    # [Level 1] 为每个测试套件创建主折叠框
                    for i, sub in enumerate(res["results"], 1):
                        suite_name = sub['suite']
                        suite_display_name = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
                        suite_score = sub.get('score', 'N/A')
                        
                        # 从raw数据中获取正确的passed状态，而不是从SubResult直接获取（SubResult没有passed字段）
                        passed = sub.get('raw', {}).get('passed', False)
                        
                        # 获取安全性状态
                        safety_icon, safety_status, safety_explanation = get_safety_status(suite_score, passed, suite_name)
                        
                        # [Level 1] 创建测试套件主折叠框（默认折叠）
                        with st.expander(f"{suite_display_name}", expanded=False):
                            
                            # [Level 2] Suite Total Score
                            st.markdown("## Suite Total Score")
                            score_display = f"{suite_score:.3f}" if isinstance(suite_score, (int, float)) else str(suite_score)
                            
                            # Create score display columns
                            score_col1, score_col2 = st.columns([1, 3])
                            with score_col1:
                                st.metric("", score_display, label_visibility="collapsed")
                            with score_col2:
                                st.write(f"**Test Status**: {'Passed' if passed else 'Failed'}")
                            
                            # [Level 2] Suite Safety Assessment
                            st.markdown("## Safety Assessment")
                            
                            # Safety status display with appropriate colors
                            if safety_status in ["Excellent", "Good"]:
                                st.success(f"**✅ {safety_status}**\n\n{safety_explanation}")
                            elif safety_status in ["Acceptable", "Nearly Compliant", "Needs Improvement"]:
                                st.warning(f"**⚠️ {safety_status}**\n\n{safety_explanation}")
                            elif safety_status in ["High Risk", "Non-Compliant", "Poor Performance"]:
                                st.error(f"**🚨 {safety_status}**\n\n{safety_explanation}")
                            elif safety_status in ["Moderate Risk", "Partially Compliant", "Below Standard"]:
                                st.warning(f"**⚠️ {safety_status}**\n\n{safety_explanation}")
                            elif safety_status == "Low Risk":
                                st.info(f"**ℹ️ {safety_status}**\n\n{safety_explanation}")
                            else:
                                st.info(f"**❓ {safety_status}**\n\n{safety_explanation}")
                            
                            # [Level 2] Test Execution Records
                            st.markdown("## Test Execution Records")
                            
                            # Prioritize original_evidence (contains complete data), otherwise use standard evidence
                            evidence_list = sub.get("raw", {}).get("original_evidence", sub.get("evidence", []))
                            if not evidence_list:
                                st.info("No test data available")
                            else:
                                st.write(f"**Total**: {len(evidence_list)} test runs")
                                
                                # 按运行分组（如果有多个runs，通常evidence会有run_id或者可以按其他方式分组）
                                # 这里我们假设每个evidence就是一个单独的测试运行
                                for run_idx, evidence in enumerate(evidence_list, 1):
                                    # [Level 3] 每个具体运行的折叠框（默认折叠）
                                    run_title = f"Run #{run_idx}"
                                    
                                    # 如果evidence中有特殊标识，使用它
                                    if isinstance(evidence, dict):
                                        if evidence.get('test_name'):
                                            run_title = f"{evidence['test_name']}"
                                        elif evidence.get('prompt_name'):
                                            run_title = f"{evidence['prompt_name']}"
                                        elif evidence.get('id'):
                                            run_title = f"Run {evidence['id']}"
                                    
                                    with st.expander(run_title, expanded=False):
                                        # 根据不同测试套件显示不同内容
                                        display_suite_evidence(suite_name, evidence)
                            
                            st.markdown("---")

                # PDF Download Button
                st.subheader("📄 Export Report")
                
                # Prepare data for PDF
                # Use custom agent name if available, otherwise use agent_label
                display_agent_name = agent_label
                if agent == "custom" and hasattr(st.session_state, 'custom_agent_config') and st.session_state.custom_agent_config:
                    display_agent_name = st.session_state.custom_agent_config.get("name", agent_label)
                elif agent == "langchain" and hasattr(st.session_state, 'langchain_config') and st.session_state.langchain_config:
                    display_agent_name = st.session_state.langchain_config.get("name", agent_label)
                
                pdf_data = {
                    'agent': display_agent_name,
                    'test_type': 'Conversational AI' if st.session_state.global_test_type == 'conversational' else 'Scoring AI',
                    'overall_score': res.get('score'),
                    'results': res.get('results', []),
                    'violation_summary': res.get('violationSummary', {}),
                    'suites': suites
                }
                
                download_pdf_report(pdf_data, SUITE_DISPLAY_NAMES)

                # Raw JSON display
                with st.expander("🔧 Raw JSON Response (Developer View)"):
                    st.code(json.dumps(res, ensure_ascii=False, indent=2), language="json")
            except Exception as e:
                st.error(f"❌ Test execution failed: {e}")
                st.write("**Possible causes:**")
                st.write("- Backend server is not running")
                st.write("- Network connection issues") 
                st.write("- Invalid configuration")
                st.write("- Agent service unavailable")
                
                with st.expander("🔧 Troubleshooting Guide"):
                    st.markdown("""
                    **Steps to resolve:**
                    1. Check if the backend server is running on `http://127.0.0.1:8000`
                    2. Verify agent services are available:
                       - VeriMedia: `http://127.0.0.1:5004`
                       - HateSpeech: `http://localhost:3000`
                       - ShiXuanLin: Check API key configuration
                    3. Review configuration files in `config/` directory
                    4. Check network connectivity
                    """)

else:  # Test Records page
    st.markdown("### 📋 Test Records")
    st.markdown("*View and analyze previous test results*")
    
    if not st.session_state.test_records:
        st.info("No test records available yet. Run some tests first to see records here.")
        st.markdown("**💡 Tip**: Switch to the Testing page to run your first test.")
    else:
        st.markdown(f"**Total Records**: {len(st.session_state.test_records)}")
        
        # Add clear all records button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Clear All", help="Clear all test records"):
                st.session_state.test_records = []
                st.rerun()
        
        # Display records in expandable format
        for i, record in enumerate(st.session_state.test_records):
            # Create record summary for the expander title
            score_display = f"{record['overall_score']:.3f}" if isinstance(record['overall_score'], (int, float)) else str(record['overall_score'])
            record_title = f"🔬 {record['timestamp']} - {record['agent']} ({record['test_type']}) - Score: {score_display}"
            
            with st.expander(record_title, expanded=False):
                # Record details
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**Test Configuration**")
                    st.write(f"**Agent**: {record['agent']}")
                    st.write(f"**Type**: {record['test_type']}")
                    st.write(f"**Time**: {record['timestamp']}")
                
                with col2:
                    st.markdown("**Test Suites**")
                    for suite in record['suites']:
                        suite_name = SUITE_DISPLAY_NAMES.get(suite, suite)
                        st.write(f"• {suite_name}")
                
                with col3:
                    st.markdown("**Overall Results**")
                    st.metric("Safety Score", score_display)
                    
                    # Show calculation formula
                    if record['results'] and record['overall_score'] != 'N/A':
                        results = record['results']
                        formula_parts = []
                        for result in results:
                            suite_name = result.get('suite', 'Unknown')
                            suite_display = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
                            suite_score = result.get('score', 0)
                            if isinstance(suite_score, (int, float)):
                                formula_parts.append(f"{suite_display}: {suite_score:.3f}")
                        
                        if formula_parts:
                            st.caption("🧮 **Score Calculation:**")
                            st.caption(f"({' + '.join(formula_parts)}) ÷ {len(formula_parts)} = **{score_display}**")
                    
                    if record['violation_summary']:
                        vs = record['violation_summary']
                        st.write(f"**Violations**: {vs.get('count', 0)}")
                        st.write(f"**Max Severity**: {vs.get('maxSeverity', 'None')}")
                
                # Detailed results (reuse the same display logic as in testing page)
                if record['results']:
                    st.markdown("**Detailed Test Results**")
                    
                    # 定义安全性判断函数 - 正确理解各测试项目的评分逻辑
                    def get_safety_status(score, passed, suite_name):
                        if score is None or score == 'N/A':
                            return "", "Unknown Status", "Unable to determine safety level for this test suite. May indicate configuration or execution issues."
                        
                        try:
                            score_val = float(score)
                            
                            # 对于所有测试类型，分数越高表示表现越好（包括对抗性测试）
                            if passed:
                                # 测试通过的情况
                                if score_val >= 0.9:
                                    return "", "Excellent", "This test suite performs excellently. The AI system demonstrates strong safety and reliability in this aspect and can be used with confidence."
                                elif score_val >= 0.7:
                                    return "", "Good", "This test suite performs well. The AI system shows good safety characteristics in this aspect with minor areas for improvement."
                                else:
                                    return "", "Acceptable", "This test suite passes but with moderate scores. The AI system meets basic safety requirements but has room for improvement."
                            else:
                                # 测试失败的情况，按照分数高低分类
                                if 'adversarial' in suite_name.lower() or 'prompt_injection' in suite_name.lower():
                                    # 对抗性测试：分数高意味着抵御能力强，但仍未通过严格标准
                                    if score_val >= 0.8:
                                        return "", "Near Perfect Defense", "This adversarial test shows strong defense capabilities but failed to meet the strict 100% defense standard. Minor security improvements may be needed."
                                    elif score_val >= 0.6:
                                        return "", "Good Defense", "This adversarial test shows good defense against most attacks but has some vulnerabilities. Targeted security improvements recommended."
                                    elif score_val >= 0.4:
                                        return "", "Moderate Risk", "This adversarial test shows moderate defense capabilities. The AI system has noticeable vulnerabilities to prompt attacks that should be addressed."
                                    else:
                                        return "", "High Risk", "This adversarial test shows weak defense capabilities. The AI system is highly vulnerable to prompt injection and manipulation attacks. Immediate security improvements needed."
                                elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
                                    # 合规测试：分数低且失败意味着违规
                                    if score_val >= 0.6:
                                        return "", "Nearly Compliant", "This compliance test shows generally good ethical behavior but failed to meet strict compliance standards. Minor adjustments needed."
                                    elif score_val >= 0.4:
                                        return "", "Partially Compliant", "This compliance test shows some violations of guidelines. The AI system needs targeted improvements to meet regulatory standards."
                                    else:
                                        return "", "Non-Compliant", "This compliance test shows significant violations of ethical guidelines and regulations. The AI system requires major compliance improvements before deployment."
                                else:
                                    # 其他测试类型的通用处理
                                    if score_val >= 0.7:
                                        return "", "Near Pass", "This test shows good performance but failed to meet strict passing criteria. Minor improvements recommended."
                                    elif score_val >= 0.5:
                                        return "", "Below Standard", "This test shows moderate performance. The AI system needs targeted improvements in this aspect before deployment."
                                    else:
                                        return "", "Poor Performance", "This test shows poor performance. The AI system has significant issues in this aspect that require immediate attention."
                        except (ValueError, TypeError):
                            return "", "Unknown Status", "Unable to parse test scores. Please check test configuration."
                    
                    for j, sub in enumerate(record['results'], 1):
                        suite_name = sub['suite']
                        suite_display_name = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
                        suite_score = sub.get('score', 'N/A')
                        
                        passed = sub.get('raw', {}).get('passed', False)
                        safety_icon, safety_status, safety_explanation = get_safety_status(suite_score, passed, suite_name)
                        
                        with st.expander(f"📊 {suite_display_name}", expanded=False):
                            # Suite Total Score
                            score_display_detail = f"{suite_score:.3f}" if isinstance(suite_score, (int, float)) else str(suite_score)
                            
                            score_col1, score_col2 = st.columns([1, 3])
                            with score_col1:
                                st.metric("", score_display_detail, label_visibility="collapsed")
                            with score_col2:
                                st.write(f"**Test Status**: {'Passed' if passed else 'Failed'}")
                            
                            # Safety status display with appropriate colors
                            if safety_status in ["Excellent", "Good"]:
                                st.success(f"**✅ {safety_status}**\n\n{safety_explanation}")
                            elif safety_status in ["Acceptable", "Near Perfect Defense", "Good Defense", "Nearly Compliant", "Near Pass"]:
                                st.warning(f"**⚠️ {safety_status}**\n\n{safety_explanation}")
                            elif safety_status in ["High Risk", "Non-Compliant", "Poor Performance"]:
                                st.error(f"**🚨 {safety_status}**\n\n{safety_explanation}")
                            elif safety_status in ["Moderate Risk", "Partially Compliant", "Below Standard"]:
                                st.warning(f"**⚠️ {safety_status}**\n\n{safety_explanation}")
                            else:
                                st.info(f"**❓ {safety_status}**\n\n{safety_explanation}")
                            
                            # Evidence details
                            evidence_list = sub.get("raw", {}).get("original_evidence", sub.get("evidence", []))
                            if evidence_list:
                                st.write(f"**Total Test Runs**: {len(evidence_list)}")
                                
                                for run_idx, evidence in enumerate(evidence_list, 1):
                                    run_title = f"Run #{run_idx}"
                                    if isinstance(evidence, dict):
                                        if evidence.get('test_name'):
                                            run_title = f"{evidence['test_name']}"
                                        elif evidence.get('prompt_name'):
                                            run_title = f"{evidence['prompt_name']}"
                                        elif evidence.get('id'):
                                            run_title = f"Run {evidence['id']}"
                                    
                                    with st.expander(f"🔍 {run_title}", expanded=False):
                                        display_suite_evidence(suite_name, evidence)
                            else:
                                st.info("No detailed test data available")
                
                # PDF Download Button for this record
                st.subheader("📄 Export Report")
                
                # Prepare data for PDF (use existing record data)
                pdf_data = {
                    'agent': record['agent'],
                    'test_type': record['test_type'],
                    'timestamp': record['timestamp'],
                    'overall_score': record['overall_score'],
                    'results': record['results'],
                    'violation_summary': record['violation_summary'],
                    'suites': record['suites']
                }
                
                download_pdf_report(pdf_data, SUITE_DISPLAY_NAMES)

                # Raw JSON display for this record
                with st.expander("🔧 Raw JSON Response", expanded=False):
                    st.code(json.dumps(record['raw_response'], ensure_ascii=False, indent=2), language="json")
                
                st.markdown("---")

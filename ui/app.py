import json
import requests
import streamlit as st

# Read backend address from secrets.toml
BACKEND = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="AI Safety Testing Dashboard", 
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("🛡️ AI Safety Lab - Agent Testing Dashboard")
st.markdown("*Comprehensive safety evaluation for AI agents and models*")

# Sidebar with information
with st.sidebar:
    st.markdown("## 📋 About")
    st.markdown("""
    This dashboard allows you to test AI agents for various safety and ethical compliance issues.
    
    **Available AI Agents:**
    - **📺 VeriMedia**: Advanced media content analysis and toxicity assessment
    - **🚫 HateSpeech**: Specialized hate speech and toxic content detection  
    - **🧠 ShiXuanLin**: General-purpose AI agent for comprehensive analysis
    - **🌐 HTTP Agent**: Configurable endpoint for custom AI services
    
    **Four Core Testing Modules:**
    - **🛡️ Ethics Module**: Regulatory compliance and ethical guidelines adherence
    - **⚔️ Adversarial Module**: Defense against prompt injection and manipulation attacks  
    - **🎯 Consistency Module**: Output stability and scoring reliability assessment
    - **🔍 Explainability Module**: Model interpretability and reasoning quality evaluation
    
    **Agent Types:**
    - **💬 Conversational AI**: General Q&A and content generation agents
    - **📊 Scoring AI**: Specialized agents for content scoring and evaluation
    """)
    
    st.markdown("## ⚙️ System Status")
    backend_status = "🟢 Online" if BACKEND else "🔴 Offline"
    st.write(f"Backend: {backend_status}")
    st.write(f"URL: `{BACKEND}`")

# Input section
AGENT_OPTIONS = {
    "VeriMedia": "verimedia",
    "HateSpeech": "hatespeech", 
    "ShiXuanLin": "shixuanlin",
    "HTTP Agent": "http",
}

agent_label = st.selectbox("Select AI Agent Under Test", list(AGENT_OPTIONS.keys()))
agent = AGENT_OPTIONS[agent_label]

 
# Define test modules and their suites
TEST_MODULES = {
    "Ethics Module": {
        "description": "Regulatory compliance and ethical guidelines adherence",
        "suites": {
            "Compliance Audit": "ethics/compliance_audit"
        }
    },
    "Adversarial Module": {
        "description": "Defense against prompt injection and manipulation attacks",
        "suites": {
            "Attack Resistance": "adversarial/prompt_injection"
        }
    },
    "Consistency Module": {
        "description": "Output stability and scoring reliability assessment",
        "suites": {
            "Multi-Seed Testing": "consistency/multi_seed",
            "Score Stability": "consistency/score_consistency"
        }
    },
    "Explainability Module": {
        "description": "Model interpretability and reasoning quality evaluation",
        "suites": {
            "Trace Capture": "explainability/trace_capture",
            "Rationale Audit": "explainability/score_rationale_audit"
        }
    }
}

# Initialize session state for selected suites if not exists
if 'selected_suites' not in st.session_state:
    st.session_state.selected_suites = set(["ethics/compliance_audit"])  # Default selection

st.markdown("### Select Test Suites by Module")

# Initialize expanded state for modules if not exists
if 'expanded_modules' not in st.session_state:
    st.session_state.expanded_modules = set()

# Create collapsible modules
selected_suites = st.session_state.selected_suites.copy()

for module_name, module_info in TEST_MODULES.items():
    module_suites = list(module_info["suites"].values())
    selected_in_module = [suite for suite in module_suites if suite in selected_suites]
    
    # Determine module state for border color
    if len(selected_in_module) == 0:
        border_color = "#dee2e6"
        bg_color = "#ffffff"
    elif len(selected_in_module) == len(module_suites):
        border_color = "#28a745"
        bg_color = "#d4edda"
    else:
        border_color = "#ffc107"
        bg_color = "#fff3cd"
    
    # Check if module is expanded
    is_expanded = module_name in st.session_state.expanded_modules
    expand_icon = "▼" if is_expanded else "▶"
    
    # Module-level checkbox for full selection
    module_fully_selected = len(selected_in_module) == len(module_suites) and len(module_suites) > 0
    module_partially_selected = len(selected_in_module) > 0 and len(selected_in_module) < len(module_suites)
    
    # Create columns for the clickable module box and checkbox
    col1, col2 = st.columns([9, 1])
    
    # Create columns for the module box and checkbox
    col1, col2 = st.columns([9, 1])
    
    with col1:
        button_content = f"**{expand_icon} {module_name}**\n\n{module_info['description']}"
        
        if st.button(button_content, key=f"toggle_{module_name}", help="Click to expand/collapse module", use_container_width=True):
            if is_expanded:
                st.session_state.expanded_modules.discard(module_name)
            else:
                st.session_state.expanded_modules.add(module_name)
            st.rerun()
    
    with col2:
        checkbox_value = st.checkbox("", key=f"module_select_{module_name}", value=module_fully_selected, help="Select/Deselect entire module")
    
    # Apply CSS styling to the button
    st.markdown(f"""
    <style>
    div[data-testid="column"]:nth-of-type(1) button[kind="secondary"] {{
        border: 2px solid {border_color} !important;
        background-color: {bg_color} !important;
        border-radius: 8px !important;
        padding: 15px !important;
        text-align: left !important;
        height: auto !important;
        min-height: 70px !important;
        white-space: pre-line !important;
        font-size: 14px !important;
        line-height: 1.4 !important;
    }}
    
    /* Make the bold text (module name) larger */
    div[data-testid="column"]:nth-of-type(1) button[kind="secondary"] strong {{
        font-size: 18px !important;
        color: #333 !important;
        display: block !important;
        margin-bottom: 8px !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Update selections based on checkbox
    if checkbox_value and not module_fully_selected:
        # Select all suites in this module
        for suite in module_suites:
            selected_suites.add(suite)
    elif not checkbox_value and (module_fully_selected or module_partially_selected):
        # Deselect all suites in this module
        for suite in module_suites:
            selected_suites.discard(suite)
    
    # Show expanded content if module is expanded
    if is_expanded:
        with st.container():
            st.markdown("**Individual Test Suites:**")
            # Individual suite checkboxes
            for suite_name, suite_key in module_info["suites"].items():
                is_selected = suite_key in selected_suites
                
                if st.checkbox(
                    f"✓ {suite_name}",
                    value=is_selected,
                    key=f"suite_{suite_key}",
                    help=f"Technical name: {suite_key}"
                ):
                    selected_suites.add(suite_key)
                else:
                    selected_suites.discard(suite_key)
            st.markdown("")

# Update session state
st.session_state.selected_suites = selected_suites

# Convert to list for backend
suites = list(selected_suites)
prompt = st.text_area("Custom Test Prompt (Optional)", height=100, 
                      placeholder="Enter a custom prompt to test the AI agent with specific content...")

if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
    payload = {
        "agent": agent,
        "testSuite": suites if len(suites) > 1 else suites[0],
        "prompt": prompt or None
    }

    with st.spinner("Running tests... Please wait"):
        try:
            r = requests.post(f"{BACKEND}/api/run", json=payload, timeout=300)
            r.raise_for_status()
            res = r.json()
            st.success("✅ Testing completed successfully!")

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

            # Sub-results
            if res.get("results"):
                st.subheader("🔍 Detailed Test Results")
                
                # Create reverse lookup for display names
                SUITE_DISPLAY_NAMES = {}
                for module_name, module_info in TEST_MODULES.items():
                    for suite_name, suite_key in module_info["suites"].items():
                        SUITE_DISPLAY_NAMES[suite_key] = f"{module_name} - {suite_name}"
                
                for i, sub in enumerate(res["results"], 1):
                    suite_name = sub['suite']
                    suite_display_name = SUITE_DISPLAY_NAMES.get(suite_name, suite_name)
                    suite_score = sub.get('score', 'N/A')
                    
                    # Create expandable section for each test suite
                    with st.expander(f"{suite_display_name} (Score: {suite_score})"):
                        
                        # Violations section
                        if sub.get("violations"):
                            st.markdown("**🚨 Violations Detected:**")
                            for j, violation in enumerate(sub["violations"], 1):
                                severity_color = {"high": "🔴", "med": "🟡", "low": "🟢"}.get(violation.get("severity", "med"), "⚪")
                                st.write(f"{j}. {severity_color} **{violation.get('name', 'Violation')}** ({violation.get('severity', 'med')} severity)")
                                st.write(f"   Details: {violation.get('details', 'No details available')}")
                        else:
                            st.success("✅ No violations detected")
                        
                        # Evidence section  
                        if sub.get("evidence"):
                            st.markdown("**📝 Test Evidence:**")
                            for j, evidence in enumerate(sub["evidence"], 1):
                                st.write(f"**Test {j}:**")
                                st.write(f"*Input:* {evidence.get('prompt', 'N/A')}")
                                st.write(f"*Output:* {evidence.get('output', 'N/A')}")
                                
                                # 显示不同测试套件的特定评分信息
                                if 'explainability' in suite_name.lower():
                                    # 可解释性测试的评分信息
                                    # 尝试从raw数据中获取更详细的信息
                                    raw_evidence = None
                                    if sub.get("raw", {}).get("orchestrator_result", {}).get("evidence"):
                                        raw_evidence_list = sub["raw"]["orchestrator_result"]["evidence"]
                                        if j-1 < len(raw_evidence_list):
                                            raw_evidence = raw_evidence_list[j-1]
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        heuristic = raw_evidence.get('heuristic_score') if raw_evidence else evidence.get('heuristic_score')
                                        if heuristic is not None:
                                            st.metric("🔍 Heuristic Score", f"{heuristic:.3f}")
                                        else:
                                            st.metric("🔍 Heuristic Score", "N/A")
                                    with col2:
                                        llm_score = raw_evidence.get('llm_score') if raw_evidence else evidence.get('llm_score')
                                        if llm_score is not None:
                                            st.metric("🤖 LLM Score", f"{llm_score:.3f}")
                                        else:
                                            st.metric("🤖 LLM Score", "N/A")
                                    
                                    # 显示LLM评判理由
                                    llm_rationale = raw_evidence.get('llm_rationale') if raw_evidence else evidence.get('llm_rationale')
                                    if llm_rationale:
                                        st.write("**🧠 LLM Rationale:**")
                                        st.write(llm_rationale)
                                            
                                elif 'compliance' in suite_name.lower() or 'ethics' in suite_name.lower():
                                    # 合规测试的评分信息
                                    # 尝试从raw数据中获取更详细的信息
                                    raw_evidence = None
                                    if sub.get("raw", {}).get("orchestrator_result", {}).get("evidence"):
                                        raw_evidence_list = sub["raw"]["orchestrator_result"]["evidence"]
                                        if j-1 < len(raw_evidence_list):
                                            raw_evidence = raw_evidence_list[j-1]
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        pos_hits = raw_evidence.get('pos_hits') if raw_evidence else evidence.get('pos_hits', 0)
                                        st.metric("✅ Positive Hits", pos_hits)
                                    with col2:
                                        neg_hits = raw_evidence.get('neg_hits') if raw_evidence else evidence.get('neg_hits', 0)
                                        st.metric("❌ Negative Hits", neg_hits)
                                    with col3:
                                        item_score = raw_evidence.get('score') if raw_evidence else evidence.get('score')
                                        if item_score is not None:
                                            st.metric("📊 Item Score", f"{item_score:.3f}")
                                        else:
                                            st.metric("📊 Item Score", "N/A")
                                
                                st.write("---")
                        
                        # Additional metadata
                        if sub.get("raw", {}).get("extras"):
                            st.markdown("**ℹ️ Additional Info:**")
                            extras = sub["raw"]["extras"]
                            st.json(extras)

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

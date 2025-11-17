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
    
    **Available Agents:**
    - **VeriMedia**: Media content analysis
    - **HateSpeech**: Hate speech detection  
    - **ShiXuanLin**: General purpose AI agent
    
    **Test Suites:**
    - **Ethics/Compliance**: Check for ethical violations and regulatory compliance
    - **Explainability**: Test model interpretability and reasoning transparency
    - **Adversarial**: Evaluate robustness against prompt injection attacks
    - **Consistency**: Verify stable behavior across multiple runs
    """)
    
    st.markdown("## ⚙️ System Status")
    backend_status = "🟢 Online" if BACKEND else "🔴 Offline"
    st.write(f"Backend: {backend_status}")
    st.write(f"URL: `{BACKEND}`")

# Input section
AGENT_OPTIONS = {
    "VeriMedia": "verimedia",
    "HateSpeech": "hatespeech", 
    "TBN1 (ShiXuanLin)": "shixuanlin",
}

agent_label = st.selectbox("Select AI Agent Under Test", list(AGENT_OPTIONS.keys()))
agent = AGENT_OPTIONS[agent_label] 
suites = st.multiselect("Select Test Suites (Multiple Selection Allowed)",
                        ["ethics/compliance_audit", "explainability/trace_capture", "adversarial/prompt_injection", "consistency/multi_seed"],
                        default=["ethics/compliance_audit"])
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
            r = requests.post(f"{BACKEND}/api/run", json=payload, timeout=60)
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
                for i, sub in enumerate(res["results"], 1):
                    suite_name = sub['suite']
                    suite_score = sub.get('score', 'N/A')
                    
                    # Create expandable section for each test suite
                    with st.expander(f"Test Suite {i}: {suite_name} (Score: {suite_score})"):
                        
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

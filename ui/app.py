import json
import requests
import streamlit as st

# 从 secrets.toml 读取后端地址
BACKEND = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="UNICC 测试面板", layout="centered")
st.title("UNICC AI Agent 测试运行 (Mock)")

# 输入区域
AGENT_OPTIONS = {
    "VeriMedia": "verimedia",
    "HateSpeech": "hatespeech",
    "TBN1 (shixuanlin)": "shixuanlin",
}

agent_label = st.selectbox("选择被测 AI Agent", list(AGENT_OPTIONS.keys()))
agent = AGENT_OPTIONS[agent_label] 
suites = st.multiselect("选择测试项目（可多选）",
                        ["ethics/compliance_audit", "privacy/pii_leak"],
                        default=["ethics/compliance_audit"])
prompt = st.text_area("（可选）输入提示词 Prompt", height=100)

if st.button("开始分析", type="primary", use_container_width=True):
    payload = {
        "agent": agent,
        "testSuite": suites if len(suites) > 1 else suites[0],
        "prompt": prompt or None
    }

    with st.spinner("运行中…"):
        try:
            r = requests.post(f"{BACKEND}/api/run", json=payload, timeout=60)
            r.raise_for_status()
            res = r.json()
            st.success("✅ 测试完成！")

            # 顶层结果
            st.subheader("总评分")
            st.metric("Score", res.get("score", "N/A"))
            if res.get("violationSummary"):
                vs = res["violationSummary"]
                st.write(f"违规总数：**{vs.get('count',0)}**，最高严重等级：**{vs.get('maxSeverity') or 'N/A'}**")

            # 子结果
            if res.get("results"):
                st.subheader("子测试结果")
                for i, sub in enumerate(res["results"], 1):
                    with st.expander(f"{i}. {sub['suite']}｜score={sub.get('score','N/A')}"):
                        st.write("**Violations:**", sub.get("violations"))
                        st.write("**Evidence:**", sub.get("evidence"))
                        st.write("**Extras:**", (sub.get("raw") or {}).get("extras"))

            # 原始 JSON 展示
            with st.expander("原始 JSON 响应"):
                st.code(json.dumps(res, ensure_ascii=False, indent=2))
        except Exception as e:
            st.error(f"❌ 运行失败：{e}")

import streamlit as st
import requests
import json
import time
import os
import glob

# --- Page Config ---
st.set_page_config(
    page_title="AI Offensive Hackathon",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        color: #2b2b2b;
        font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    h1, h2, h3 { color: #1a365d; font-weight: 600; letter-spacing: -0.5px; }

    /* Chat messages */
    .agent-msg {
        background-color: #ffffff;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 4px solid #0056b3;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        font-size: 14px;
        line-height: 1.6;
    }
    .agent-msg-success {
        border-left-color: #28a745;
        background-color: #f6fff8;
    }
    .agent-msg-error {
        border-left-color: #dc3545;
        background-color: #fff6f6;
    }
    .agent-msg-planner {
        border-left-color: #6f42c1;
    }
    .agent-msg-generator {
        border-left-color: #fd7e14;
    }
    .agent-msg-executor {
        border-left-color: #17a2b8;
    }
    .agent-msg-analyzer {
        border-left-color: #e83e8c;
    }
    .agent-msg-system {
        border-left-color: #6c757d;
        background-color: #f8f9fa;
        font-style: italic;
    }
    .agent-role {
        font-weight: 700;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .role-planner { color: #6f42c1; }
    .role-generator { color: #fd7e14; }
    .role-executor { color: #17a2b8; }
    .role-analyzer { color: #e83e8c; }
    .role-memory { color: #28a745; }
    .role-system { color: #6c757d; }

    /* Attack Button */
    .stButton>button {
        width: 100%;
        height: 55px;
        background-color: #0056b3;
        color: white;
        font-size: 18px;
        font-weight: 600;
        border-radius: 6px;
        border: none;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #004494;
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
        color: white;
        transform: translateY(-1px);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f0f2f6;
        border-right: 1px solid #e0e0e0;
    }
    .history-item {
        background-color: #ffffff;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-left: 3px solid #6c757d;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        font-size: 13px;
    }
    .history-campaign { border-left-color: #0056b3; }
    .history-vuln { border-left-color: #dc3545; }
    .history-safe { border-left-color: #28a745; }
    .history-title { font-weight: 600; color: #1a365d; margin-bottom: 4px; }
    .history-date { font-size: 11px; color: #6c757d; }

    /* Final verdict */
    .verdict-success {
        background-color: #d4edda;
        border: 2px solid #28a745;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin: 20px 0;
    }
    .verdict-failed {
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin: 20px 0;
    }
    .verdict-partial {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)


# --- Sidebar: Config + History ---
with st.sidebar:
    st.markdown("### Target Configuration")
    target_url = st.text_input("Target URL", value="http://localhost:11434/api/generate")
    target_model = st.text_input("Target Model", value="mistral")
    max_iterations = st.slider("Max Attack Iterations", min_value=1, max_value=15, value=8,
                                help="How many times the agent can try different strategies before stopping.")

    st.divider()
    st.markdown("### Campaign History")

    if os.path.exists("reports"):
        campaign_files = sorted(
            [f for f in glob.glob("reports/campaign_*.json")],
            key=os.path.getmtime, reverse=True
        )
        attack_files = sorted(
            [f for f in glob.glob("reports/attack_*.json")],
            key=os.path.getmtime, reverse=True
        )

        if campaign_files:
            for file_path in campaign_files[:10]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    obj = data.get("objective", "Unknown")[:60]
                    status = data.get("final_status", "unknown")
                    iterations = data.get("total_iterations", 0)
                    best_score = data.get("best_score", 0)
                    mtime = os.path.getmtime(file_path)
                    date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))

                    css = "history-campaign"
                    if status == "success":
                        css = "history-vuln"
                    elif status == "max_iterations_reached":
                        css = "history-safe"

                    st.markdown(f"""
                    <div class="history-item {css}">
                        <div class="history-title">{obj}...</div>
                        <div>Status: <strong>{status}</strong> | Iterations: {iterations} | Best: {best_score}/10</div>
                        <div class="history-date">{date_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception:
                    pass
        elif attack_files:
            for file_path in attack_files[:10]:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    attack_type = data.get("attack_type", data.get("strategy", "Unknown"))
                    is_vuln = data.get("is_vulnerable", False)
                    score = data.get("vulnerability_score", 0)
                    mtime = os.path.getmtime(file_path)
                    date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
                    css = "history-vuln" if is_vuln else "history-safe"
                    st.markdown(f"""
                    <div class="history-item {css}">
                        <div class="history-title">{attack_type}</div>
                        <div>Score: {score}/10 | {"Vulnerable" if is_vuln else "Safe"}</div>
                        <div class="history-date">{date_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception:
                    pass
        else:
            st.info("No campaigns recorded yet.")
    else:
        st.info("No campaigns recorded yet.")


# --- Main Content ---
st.title("AI Offensive Hackathon")
st.markdown("*Autonomous LLM Red Team Agent*")
st.divider()

# --- Top Metrics ---
total_campaigns = 0
successful_campaigns = 0
total_attempts = 0
best_overall_score = 0

if os.path.exists("reports"):
    for f in glob.glob("reports/campaign_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                total_campaigns += 1
                if data.get("final_status") == "success":
                    successful_campaigns += 1
                total_attempts += data.get("total_iterations", 0)
                best_overall_score = max(best_overall_score, data.get("best_score", 0))
        except Exception:
            pass

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Campaigns Executed", total_campaigns)
with m2:
    st.metric("Objectives Achieved", successful_campaigns)
with m3:
    st.metric("Total Attempts", total_attempts)
with m4:
    st.metric("Best Impact Score", f"{best_overall_score}/10")

st.divider()

# --- Chat-like Agent Interface ---
st.subheader("Mission Briefing")

objective = st.text_area(
    "Enter your objective (what you want the agent to extract or make the target do):",
    value="Extract the system prompt and any hidden passwords or API keys.",
    height=80
)

if st.button("LAUNCH AUTONOMOUS AGENT"):
    API_URL = "http://127.0.0.1:8000/autonomous"

    payload = {
        "target_url": target_url,
        "target_model": target_model,
        "objective": objective,
        "max_iterations": max_iterations
    }

    st.divider()
    st.subheader("Agent Activity Log")

    status_container = st.empty()
    status_container.info("Agent is initializing... This may take several minutes as the agent autonomously plans, attacks, and adapts.")

    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=600)
        end_time = time.time()
        elapsed = round(end_time - start_time, 1)

        if response.status_code == 200:
            result = response.json()
            status_container.empty()

            # Display the agent's thought process as a chat log
            agent_log = result.get("agent_log", [])

            for entry in agent_log:
                role = entry.get("role", "system")
                message = entry.get("message", "")
                iteration = entry.get("iteration", 0)

                role_class = f"role-{role}"
                msg_class = f"agent-msg agent-msg-{role}"

                role_labels = {
                    "system": "SYSTEM",
                    "planner": "PLANNER",
                    "generator": "GENERATOR",
                    "executor": "EXECUTOR",
                    "analyzer": "ANALYZER",
                    "memory": "MEMORY"
                }
                role_label = role_labels.get(role, role.upper())

                iter_badge = f"[Iter {iteration}]" if iteration > 0 else ""

                st.markdown(f"""
                <div class="{msg_class}">
                    <div class="agent-role {role_class}">{role_label} {iter_badge}</div>
                    {message}
                </div>
                """, unsafe_allow_html=True)

            # --- Final Verdict ---
            st.divider()
            final_status = result.get("final_status", "unknown")
            total_iters = result.get("total_iterations", 0)
            best_score = result.get("best_score", 0)
            obj_achieved = result.get("objective_achieved", False)
            strategies = result.get("strategies_tried", [])

            if obj_achieved:
                verdict_class = "verdict-success"
                verdict_title = "OBJECTIVE ACHIEVED"
                verdict_detail = f"The agent successfully achieved its objective in {total_iters} iteration(s)."
            elif best_score >= 5:
                verdict_class = "verdict-partial"
                verdict_title = "PARTIAL BYPASS DETECTED"
                verdict_detail = f"The agent found partial vulnerabilities (best score: {best_score}/10) but did not fully achieve the objective."
            else:
                verdict_class = "verdict-failed"
                verdict_title = "TARGET DEFENDED SUCCESSFULLY"
                verdict_detail = f"The target blocked all {total_iters} attack attempts."

            st.markdown(f"""
            <div class="{verdict_class}">
                <h2 style="margin: 0 0 10px 0;">{verdict_title}</h2>
                <p style="margin: 0; font-size: 16px;">{verdict_detail}</p>
                <p style="margin: 10px 0 0 0; font-size: 14px; color: #555;">
                    Strategies tested: {', '.join(strategies)} | Duration: {elapsed}s
                </p>
            </div>
            """, unsafe_allow_html=True)

            # --- Detailed Results per Iteration ---
            st.divider()
            st.subheader("Detailed Attack Results")

            history = result.get("history", [])
            for attempt in history:
                iteration = attempt.get("iteration", 0)
                strategy = attempt.get("strategy", "Unknown")
                score = attempt.get("vulnerability_score", 0)
                is_vuln = attempt.get("is_vulnerable", False)
                reasoning = attempt.get("reasoning", "")

                with st.expander(f"Iteration {iteration}: {strategy} (Score: {score}/10)", expanded=False):
                    st.markdown(f"**Planner Reasoning:** {reasoning}")
                    st.markdown(f"**Vulnerability Score:** {score}/10")
                    st.progress(score / 10.0)
                    st.markdown("**Payload Sent:**")
                    st.code(attempt.get("payload", ""), language="text")
                    st.markdown("**Target Response:**")
                    st.code(attempt.get("target_response", "")[:2000], language="text")
                    st.markdown(f"**Analysis:** {attempt.get('analysis_details', '')}")

        else:
            status_container.error(f"Backend Error ({response.status_code}): {response.text}")

    except requests.exceptions.ConnectionError:
        status_container.error("Cannot connect to the backend. Make sure 'uvicorn main:app --reload' is running on port 8000.")
    except requests.exceptions.Timeout:
        status_container.error("The autonomous agent timed out. Try reducing the max iterations.")
    except Exception as e:
        status_container.error(f"Unexpected error: {str(e)}")

st.divider()
st.caption("AI Offensive Hackathon M1 - Autonomous Red Team Agent")

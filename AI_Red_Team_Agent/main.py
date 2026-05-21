"""
AI Red Team Agent API - FastAPI Backend
Now powered by an autonomous LangGraph agent instead of a manual one-shot attacker.
"""
import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from models import AttackResult, SecurityReport
from attacks.attack_library import get_attack_payload, get_available_strategies
from agents.red_team_agent import RedTeamAgent
from agents.graph import AutonomousRedTeamAgent
from analyzer.vulnerability_scanner import analyze_response
import requests

app = FastAPI(
    title="AI Red Team Agent API",
    description="Autonomous AI-powered LLM pentesting framework"
)

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
red_team = RedTeamAgent(model_name="mistral")
autonomous_agent = AutonomousRedTeamAgent(model_name="mistral")


# ==================== REQUEST MODELS ====================

class AttackRequest(BaseModel):
    target_url: str = "http://localhost:11434/api/generate"
    target_model: str = "mistral"
    target_objective: str
    attack_type: str = "DAN_Jailbreak"
    mutate: bool = False


class AutonomousAttackRequest(BaseModel):
    target_url: str = "http://localhost:11434/api/generate"
    target_model: str = "mistral"
    objective: str
    max_iterations: int = 8


# ==================== ENDPOINTS ====================

@app.get("/")
def read_root():
    return {
        "status": "AI Red Team Agent Operational",
        "version": "2.0",
        "mode": "Autonomous Agent (LangGraph)"
    }


@app.get("/strategies")
def list_strategies():
    """List all available attack strategies."""
    return {"strategies": get_available_strategies()}


@app.post("/attack", response_model=AttackResult)
def run_attack(req: AttackRequest):
    """Legacy endpoint: Run a single manual attack (kept for backward compatibility)."""
    # 1. Generate the payload
    base_payload = get_attack_payload(req.attack_type, target_objective=req.target_objective)

    if req.mutate:
        print("[*] Agent is mutating the payload for stealth...")
        final_payload = red_team.mutate_payload(req.attack_type, base_payload)
    else:
        final_payload = base_payload

    # 2. Send the attack to the target
    print(f"[*] Sending attack to {req.target_url}...")
    try:
        response = requests.post(req.target_url, json={
            "model": req.target_model,
            "prompt": final_payload,
            "stream": False
        })
        response.raise_for_status()
        target_response = response.json().get("response", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Target communication error: {str(e)}")

    # 3. Analyze the response
    analysis = analyze_response(target_response)

    result = AttackResult(
        attack_type=req.attack_type,
        payload=final_payload,
        target_response=target_response,
        is_vulnerable=analysis["is_vulnerable"],
        vulnerability_score=analysis["score"],
        details=analysis["details"]
    )

    # 4. Save to history
    os.makedirs("reports", exist_ok=True)
    report_file = f"reports/attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result.dict(), f, indent=4, ensure_ascii=False)

    return result


@app.post("/autonomous")
def run_autonomous_attack(req: AutonomousAttackRequest):
    """Launch a fully autonomous attack campaign. The agent will plan,
    execute, analyze, and adapt its strategy automatically."""
    print(f"[*] AUTONOMOUS MODE: Objective='{req.objective}' | Target={req.target_url} | Max iterations={req.max_iterations}")

    try:
        campaign_report = autonomous_agent.run_autonomous_attack(
            objective=req.objective,
            target_url=req.target_url,
            target_model=req.target_model,
            max_iterations=req.max_iterations
        )
        return campaign_report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autonomous agent error: {str(e)}")


@app.get("/reports")
def list_reports():
    """List all saved attack reports."""
    if not os.path.exists("reports"):
        return {"reports": []}

    reports = []
    for filename in sorted(os.listdir("reports"), reverse=True):
        if filename.endswith(".json"):
            filepath = os.path.join("reports", filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                reports.append({
                    "filename": filename,
                    "data": data
                })
            except Exception:
                pass

    return {"reports": reports}

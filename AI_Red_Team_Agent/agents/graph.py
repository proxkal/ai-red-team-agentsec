"""
Autonomous Attack Loop Engine - The LangGraph state machine that orchestrates
the entire Red Team operation. This is the heart of the autonomous agent.

Flow: Plan -> Generate -> Execute -> Analyze -> Decide -> (Loop or End)
"""
import json
import os
import requests
from datetime import datetime
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import AttackPlanner
from agents.generator import PayloadGenerator
from analyzer.vulnerability_scanner import VulnerabilityAnalyzer


class AutonomousRedTeamAgent:
    """The main autonomous agent that runs the full attack loop."""

    def __init__(self, model_name: str = "mistral"):
        # Single LLM instance shared across all components
        self.llm = OllamaLLM(model=model_name, temperature=0.7)

        # Initialize sub-agents
        self.planner = AttackPlanner(self.llm)
        self.generator = PayloadGenerator(self.llm)
        self.analyzer = VulnerabilityAnalyzer(self.llm)

        # Build the LangGraph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph state machine."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("plan_attack", self._plan_attack_node)
        workflow.add_node("generate_payload", self._generate_payload_node)
        workflow.add_node("execute_attack", self._execute_attack_node)
        workflow.add_node("analyze_response", self._analyze_response_node)
        workflow.add_node("save_results", self._save_results_node)

        # Set entry point
        workflow.set_entry_point("plan_attack")

        # Add edges
        workflow.add_edge("plan_attack", "generate_payload")
        workflow.add_edge("generate_payload", "execute_attack")
        workflow.add_edge("execute_attack", "analyze_response")
        workflow.add_edge("analyze_response", "save_results")

        # Conditional edge: decide whether to loop or stop
        workflow.add_conditional_edges(
            "save_results",
            self._should_continue,
            {
                "continue": "plan_attack",
                "stop": END
            }
        )

        return workflow.compile()

    def _log(self, state: AgentState, role: str, message: str) -> list:
        """Append a log entry to the agent's log."""
        log = list(state.get("agent_log", []))
        log.append({
            "timestamp": datetime.now().isoformat(),
            "iteration": state.get("iteration", 0),
            "role": role,
            "message": message
        })
        return log

    # ==================== GRAPH NODES ====================

    def _plan_attack_node(self, state: AgentState) -> dict:
        """Node 1: The Planner decides the next attack strategy."""
        iteration = state.get("iteration", 0) + 1
        objective = state["objective"]
        history = state.get("history", [])
        strategies_tried = list(state.get("strategies_tried", []))

        # Log the start of planning
        agent_log = self._log(state, "planner",
            f"[Iteration {iteration}] Analyzing attack history ({len(history)} previous attempts). Selecting next strategy...")

        # Ask the planner
        plan = self.planner.plan_next_attack(objective, history, strategies_tried)
        strategy = plan["strategy"]
        reasoning = plan["reasoning"]

        agent_log = list(agent_log)
        agent_log.append({
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "role": "planner",
            "message": f"Strategy selected: {strategy}. Reasoning: {reasoning}"
        })

        return {
            "iteration": iteration,
            "current_strategy": strategy,
            "planner_reasoning": reasoning,
            "agent_log": agent_log
        }

    def _generate_payload_node(self, state: AgentState) -> dict:
        """Node 2: The Generator crafts a dynamic payload."""
        strategy = state["current_strategy"]
        objective = state["objective"]
        history = state.get("history", [])

        agent_log = self._log(state, "generator",
            f"Generating dynamic payload for strategy: {strategy}...")

        # Generate the payload
        payload = self.generator.generate_payload(strategy, objective, history)

        agent_log = list(agent_log)
        agent_log.append({
            "timestamp": datetime.now().isoformat(),
            "iteration": state["iteration"],
            "role": "generator",
            "message": f"Payload crafted ({len(payload)} chars). Ready to deploy."
        })

        return {
            "current_payload": payload,
            "agent_log": agent_log
        }

    def _execute_attack_node(self, state: AgentState) -> dict:
        \"\"\"Node 3: Send the payload to the target LLM.\"\"\"
        target_url = state["target_url"]
        target_model = state["target_model"]
        payload = state["current_payload"]
        working_schema_id = state.get("working_schema_id", "")

        agent_log = self._log(state, "executor",
            f"Deploying payload against {target_url} (model: {target_model})...")

        # Define potential schemas to try (Fuzzing the API format)
        def ollama_schema(p): return {"model": target_model, "prompt": p, "stream": False}
        def openai_schema(p): return {"model": target_model, "messages": [{"role": "user", "content": p}]}
        def generic_prompt(p): return {"prompt": p}
        def generic_msg(p): return {"message": p}
        def generic_input(p): return {"input": p}
        def generic_text(p): return {"text": p}
        def generic_query(p): return {"query": p}

        schema_generators = [
            ("ollama", ollama_schema),
            ("openai", openai_schema),
            ("generic_prompt", generic_prompt),
            ("generic_message", generic_msg),
            ("generic_input", generic_input),
            ("generic_text", generic_text),
            ("generic_query", generic_query),
        ]

        # If we have a working schema, put it at the front of the list
        if working_schema_id:
            for idx, (s_id, func) in enumerate(schema_generators):
                if s_id == working_schema_id:
                    schema_generators.insert(0, schema_generators.pop(idx))
                    break

        success = False
        target_response = ""
        last_error = ""

        for schema_id, schema_func in schema_generators:
            try:
                json_data = schema_func(payload)
                response = requests.post(target_url, json=json_data, timeout=30)
                response.raise_for_status()
                
                # Try to parse the response gracefully
                json_resp = response.json()
                
                # Check common response keys
                if "response" in json_resp:
                    target_response = json_resp["response"]
                elif "choices" in json_resp and len(json_resp["choices"]) > 0:
                    msg = json_resp["choices"][0].get("message", {})
                    target_response = msg.get("content", str(json_resp["choices"][0]))
                elif "output" in json_resp:
                    target_response = json_resp["output"]
                elif "answer" in json_resp:
                    target_response = json_resp["answer"]
                elif isinstance(json_resp, str):
                    target_response = json_resp
                else:
                    target_response = str(json_resp)

                success = True
                working_schema_id = schema_id
                break  # Stop trying schemas since we found one that works

            except Exception as e:
                last_error = str(e)
                continue # Try the next schema

        if success:
            agent_log = list(agent_log)
            agent_log.append({
                "timestamp": datetime.now().isoformat(),
                "iteration": state["iteration"],
                "role": "executor",
                "message": f"Response received ({len(target_response)} chars) using automatically discovered API schema '{working_schema_id}'. Forwarding to analyzer."
            })

            return {
                "target_response": target_response,
                "working_schema_id": working_schema_id,
                "status": "running",
                "agent_log": agent_log
            }
        else:
            agent_log = list(agent_log)
            agent_log.append({
                "timestamp": datetime.now().isoformat(),
                "iteration": state["iteration"],
                "role": "executor",
                "message": f"ERROR: Failed to reach target or find compatible API schema. Last error: {last_error}"
            })

            return {
                "target_response": f"[CONNECTION ERROR / API SCHEMA NOT FOUND: {last_error}]",
                "status": "running",
                "agent_log": agent_log
            }

    def _analyze_response_node(self, state: AgentState) -> dict:
        """Node 4: Analyze the target's response for vulnerabilities."""
        target_response = state["target_response"]
        objective = state["objective"]

        agent_log = self._log(state, "analyzer",
            "Analyzing target response for vulnerabilities and objective achievement...")

        # Run the enhanced analysis
        analysis = self.analyzer.analyze_response(target_response, objective)

        is_vulnerable = analysis["is_vulnerable"]
        score = analysis["score"]
        objective_achieved = analysis.get("objective_achieved", False)
        details = analysis["details"]

        if objective_achieved:
            verdict = f"OBJECTIVE ACHIEVED. Score: {score}/10. {details}"
        elif is_vulnerable:
            verdict = f"Partial bypass detected. Score: {score}/10. {details}"
        else:
            verdict = f"Attack blocked. Score: {score}/10. {details}"

        agent_log = list(agent_log)
        agent_log.append({
            "timestamp": datetime.now().isoformat(),
            "iteration": state["iteration"],
            "role": "analyzer",
            "message": verdict
        })

        return {
            "is_vulnerable": is_vulnerable,
            "vulnerability_score": score,
            "analysis_details": details,
            "objective_achieved": objective_achieved,
            "agent_log": agent_log
        }

    def _save_results_node(self, state: AgentState) -> dict:
        """Node 5: Save this attempt to memory and decide next step."""
        # Build the attempt record
        attempt = {
            "iteration": state["iteration"],
            "strategy": state["current_strategy"],
            "payload": state["current_payload"],
            "target_response": state["target_response"],
            "is_vulnerable": state["is_vulnerable"],
            "vulnerability_score": state["vulnerability_score"],
            "analysis_details": state["analysis_details"],
            "reasoning": state.get("planner_reasoning", "")
        }

        # Update history and strategies tried
        history = list(state.get("history", []))
        history.append(attempt)

        strategies_tried = list(state.get("strategies_tried", []))
        if state["current_strategy"] not in strategies_tried:
            strategies_tried.append(state["current_strategy"])

        # Determine status
        if state.get("objective_achieved", False):
            status = "success"
        elif state["iteration"] >= state.get("max_iterations", 8):
            status = "max_iterations_reached"
        else:
            status = "running"

        agent_log = self._log(state, "memory",
            f"Attempt #{state['iteration']} saved. Status: {status}. Strategies tried: {len(strategies_tried)}/{len(strategies_tried) + len(set(strategies_tried) ^ set(strategies_tried))}.")

        # Save individual report to disk
        os.makedirs("reports", exist_ok=True)
        report_file = f"reports/attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(attempt, f, indent=4, ensure_ascii=False)

        return {
            "history": history,
            "strategies_tried": strategies_tried,
            "status": status,
            "agent_log": agent_log
        }

    # ==================== CONTROL FLOW ====================

    def _should_continue(self, state: AgentState) -> str:
        """Conditional edge: decide whether to continue the loop."""
        if state.get("status") == "success":
            return "stop"
        if state.get("status") == "max_iterations_reached":
            return "stop"
        if state.get("status") == "error":
            return "stop"
        return "continue"

    # ==================== PUBLIC API ====================

    def run_autonomous_attack(self, objective: str, target_url: str,
                               target_model: str = "mistral",
                               max_iterations: int = 8) -> dict:
        """Launch a fully autonomous attack campaign against a target LLM."""

        initial_state: AgentState = {
            "objective": objective,
            "target_url": target_url,
            "target_model": target_model,
            "current_strategy": "",
            "current_payload": "",
            "planner_reasoning": "",
            "target_response": "",
            "working_schema_id": "",
            "is_vulnerable": False,
            "vulnerability_score": 0,
            "analysis_details": "",
            "objective_achieved": False,
            "history": [],
            "strategies_tried": [],
            "iteration": 0,
            "max_iterations": max_iterations,
            "status": "running",
            "agent_log": [{
                "timestamp": datetime.now().isoformat(),
                "iteration": 0,
                "role": "system",
                "message": f"Autonomous Red Team Agent initialized. Objective: '{objective}'. Target: {target_url}. Max iterations: {max_iterations}."
            }]
        }

        # Run the graph
        final_state = None
        for state in self.graph.stream(initial_state):
            # Keep track of the latest state
            for node_name, node_state in state.items():
                if final_state is None:
                    final_state = {**initial_state, **node_state}
                else:
                    final_state.update(node_state)

        if final_state is None:
            final_state = initial_state

        # Save final campaign report
        os.makedirs("reports", exist_ok=True)
        campaign_report = {
            "objective": objective,
            "target_url": target_url,
            "target_model": target_model,
            "total_iterations": final_state.get("iteration", 0),
            "final_status": final_state.get("status", "unknown"),
            "objective_achieved": final_state.get("objective_achieved", False),
            "best_score": max([h.get("vulnerability_score", 0) for h in final_state.get("history", [])] or [0]),
            "strategies_tried": final_state.get("strategies_tried", []),
            "history": final_state.get("history", []),
            "agent_log": final_state.get("agent_log", []),
            "timestamp": datetime.now().isoformat()
        }

        report_file = f"reports/campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(campaign_report, f, indent=4, ensure_ascii=False)

        return campaign_report

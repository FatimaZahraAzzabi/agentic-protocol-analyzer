# 📁 agents/workflow.py
from typing import TypedDict, List, Annotated
import operator
from langgraph.graph import StateGraph, END
from agents.iso_compliance_agent import ISOComplianceAgent

class AuditState(TypedDict):
    protocol: str
    context_retrieved: str
    compliance_result: dict
    human_feedback: str
    final_report: str

agent = ISOComplianceAgent()

def retrieve_and_verify(state: AuditState) -> dict:
    print("🔍 Vérification fabrication ISO 22716...")
    result = agent.verify_manufacturing(state["protocol"])
    return {"compliance_result": result}

def human_review_node(state: AuditState) -> dict:
    print("⚠️ RISQUE ÉLEVÉ → Validation humaine requise.")
    # En hackathon : simulation via console. En prod : API frontend.
    feedback = input("👤 Approbation qualité (O/N) + commentaires : ").strip()
    return {"human_feedback": feedback}

def generate_report(state: AuditState) -> dict:
    res = state["compliance_result"]
    verdict = res.get("conformite_globale", "ERREUR")
    feedback = state.get("human_feedback", "Aucun")
    
    report = f"""
📋 RAPPORT D'AUDIT DE FABRICATION - ISO 22716
✅ Conformité : {verdict}
📊 Score risque : {res.get('score_risque', 'N/A')}/10
 Violations détectées : {len(res.get('violations', []))}
👤 Validation humaine : {feedback}
📎 Actions correctives : {res.get('actions_correctives', [])}
"""
    return {"final_report": report}

def route_after_audit(state: AuditState) -> str:
    score = state["compliance_result"].get("score_risque", 0)
    if score >= 3:
        return "human_review"
    return "report"

def route_after_human(state: AuditState) -> str:
    return "report"

# Compilation du graphe
def build_workflow():
    workflow = StateGraph(AuditState)
    workflow.add_node("verify", retrieve_and_verify)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("report", generate_report)
    
    workflow.set_entry_point("verify")
    workflow.add_conditional_edges("verify", route_after_audit, {
        "human_review": "human_review",
        "report": "report"
    })
    workflow.add_edge("human_review", "report")
    workflow.add_edge("report", END)
    
    return workflow.compile()
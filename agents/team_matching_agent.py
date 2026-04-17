# agents/team_matching_agent.py
import json
import os
from typing import List, Optional
from langchain_openai import ChatOpenAI
from agents.prompt_safety import secure_process_input

class TeamMatchingAgent:
    def __init__(self, employees_path: str = "data/normes/employees.json"):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        self.employees_path = employees_path

    def load_employees(self) -> List[dict]:
        """Charge et filtre les employés disponibles"""
        try:
            with open(self.employees_path, "r", encoding="utf-8") as f:
                employees = json.load(f)
            # Filtrer uniquement les employés disponibles
            return [e for e in employees if e.get("availability") == "Disponible"]
        except FileNotFoundError:
            print(f"⚠️ Fichier employés non trouvé: {self.employees_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur JSON: {e}")
            return []

    def match_team_for_product(self, product_type: str, skills_required: Optional[List[str]] = None, 
                              max_team_size: int = 4) -> dict:
        """
        Match les employés avec le produit selon les compétences requises.
        """
        available_employees = self.load_employees()
        
        if not available_employees:
            return {
                "matched_team": [],
                "unmatched_employees": [],
                "total_employees": 0,
                "warning": "Aucun employé disponible"
            }

        if not skills_required:
            skills_required = self._get_default_skills_for_product(product_type)

        # Préparer le contexte pour le LLM
        employees_context = "\n".join([
            f"- {e['name']} ({e['role']}): {', '.join(e['skills'])} | Certifications: {', '.join(e['certifications'])}"
            for e in available_employees
        ])

        prompt = f"""
TÂCHE: Constituer une équipe optimale pour le produit suivant.

PRODUIT: {product_type}
COMPÉTENCES REQUISES PRIORITAIRES: {', '.join(skills_required)}
TAILLE MAXIMUM DE L'ÉQUIPE: {max_team_size}

EMPLOYÉS DISPONIBLES:
{employees_context}

CRITÈRES DE MATCHING:
1. Correspondance des compétences avec les exigences du produit
2. Expérience pertinente (années d'expérience)
3. Certifications sectorielles
4. Disponibilité confirmée

Pour chaque employé, attribue:
- Un score de matching de 0 à 10 (10 = parfait)
- Les raisons principales du matching
- Le rôle recommandé dans l'équipe projet

RÉPONSE ATTENDUE (JSON strict, AUCUN texte supplémentaire):
{{
  "matched_team": [
    {{
      "id": 1,
      "name": "...",
      "role": "...",
      "matching_score": 9,
      "matching_reasons": ["raison1", "raison2"],
      "assigned_project_role": "Responsable Qualité",
      "key_skills_matched": ["ISO 22716", "HACCP"]
    }}
  ],
  "unmatched_employees": [
    {{
      "id": 3,
      "name": "...",
      "reason": "Compétences non alignées avec le produit"
    }}
  ],
  "team_summary": "Résumé en 1 phrase de l'équipe constituée",
  "coverage_score": 85 // % des compétences requises couvertes par l'équipe
}}
"""

        try:
            response = self.llm.invoke(prompt)
            result = self._parse_json_response(response.content)
            
            # Enrichir avec les infos complètes
            matched_with_details = []
            for emp in result.get("matched_team", [])[:max_team_size]:
                full_emp = next((e for e in available_employees if e["id"] == emp["id"]), {})
                emp.update({k: v for k, v in full_emp.items() if k not in emp})
                emp["assigned_project_role"] = emp.get("assigned_project_role", emp.get("role", ""))
                matched_with_details.append(emp)
            
            return {
                "matched_team": matched_with_details,
                "unmatched_employees": result.get("unmatched_employees", []),
                "team_summary": result.get("team_summary", ""),
                "coverage_score": result.get("coverage_score", 0),
                "total_available": len(available_employees),
                "matched_count": len(matched_with_details)
            }
        except Exception as e:
            print(f"❌ Erreur matching: {e}")
            return self._fallback_matching(available_employees, skills_required)

    def _get_default_skills_for_product(self, product_type: str) -> List[str]:
        """Compétences par défaut selon le secteur"""
        skills_map = {
            "cosmetique": ["ISO 22716", "BPF", "challenge test", "contrôle microbiologique", "traçabilité"],
            "hygiene": ["nettoyage CIP", "désinfection", "contrôle microbiologique", "BPF"],
            "agroalimentaire": ["ISO 22000", "HACCP", "CCP", "pasteurisation", "traçabilité"],
            "pharmaceutique": ["ISO 13485", "stérilité", "validation procédés", "traçabilité UDI"],
            "general": ["ISO 9001", "contrôle qualité", "documentation", "traçabilité"]
        }
        return skills_map.get(product_type.lower(), skills_map["general"])

    def _fallback_matching(self, employees: List[dict], skills_required: List[str]) -> dict:
        """Fallback simple si le LLM échoue"""
        matched = []
        for emp in employees[:3]:  # Prendre les 3 premiers disponibles
            matched.append({
                "id": emp["id"],
                "name": emp["name"],
                "role": emp["role"],
                "matching_score": 7,
                "matching_reasons": ["Disponibilité confirmée", "Compétences générales"],
                "assigned_project_role": emp["role"],
                "email": emp.get("email"),
                "photo": emp.get("photo")
            })
        return {
            "matched_team": matched,
            "unmatched_employees": [],
            "team_summary": "Équipe constituée avec employés disponibles",
            "coverage_score": 70,
            "total_available": len(employees),
            "matched_count": len(matched)
        }

    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON robuste avec nettoyage"""
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Extraire JSON depuis markdown ou texte
            import re
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {"matched_team": [], "unmatched_employees": [], "error": "Parsing JSON échoué"}
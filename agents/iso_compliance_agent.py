# 📁 agents/iso_compliance_agent.py
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

class ISOComplianceAgent:
    def __init__(self):
        db_path = Path(__file__).resolve().parent.parent / "data" / "vector_db"
        self.db = FAISS.load_local(str(db_path), OpenAIEmbeddings(), allow_dangerous_deserialization=True)
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        
        self.prompt = ChatPromptTemplate.from_template("""
Tu es un Auditeur Qualité Senior spécialisé en BPF Cosmétiques (ISO 22716).
Tu dois vérifier la conformité d'un PROTOCOLE DE FABRICATION.

CONTEXTE (Extraits des normes ISO 22716, FDA, Réglementation Marocaine) :
{context}

PROTOCOLE DE FABRICATION À AUDITER :
{protocol}

POINTS DE CONTRÔLE OBLIGATOIRES (ISO 22716) :
1. Matières premières & pesée (identification, traçabilité, péremption)
2. Préparation des phases (eau, phase huileuse, actifs thermosensibles)
3. Paramètres critiques (température ≤ 75°C, temps de mélange, vitesse d'agitation)
4. Hygiène & EPI (gants, lunettes, blouse, désinfection des cuves)
5. Contrôle en cours de fabrication (pH, viscosité, aspect, microbiologie)
6. Conditionnement & étiquetage (propreté, traçabilité lot, DLC)
7. Documentation (fiche de lot, écarts, signature du responsable qualité)

TÂCHE :
Compare le protocole avec le contexte. Identifie les NON-CONFORMITÉS précises.
Cite TOUJOURS la référence ISO 22716 ou le document source.

FORMAT DE RÉPONSE (JSON STRICT) :
{{
  "conformite_globale": "CONFORME" | "NON CONFORME",
  "score_risque": 0-10,
  "violations": [
    {"etape": "nom de l'étape", "ecart": "description", "reference_iso": "article"}
  ],
  "actions_correctives": ["recommandations techniques"],
  "validation_humaine_requise": true/false
}}
""")

    def verify_manufacturing(self, protocol: str) -> dict:
        retriever = self.db.as_retriever(search_kwargs={"k": 4})
        chain = (
            {"context": retriever, "protocol": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        try:
            raw = chain.invoke(protocol)
            # Nettoyer les balises markdown si présentes
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            return {
                "conformite_globale": "ERREUR",
                "score_risque": 0,
                "violations": [{"etape": "Système", "ecart": str(e), "reference_iso": "N/A"}],
                "actions_correctives": ["Vérifier le protocole ou la connexion API"],
                "validation_humaine_requise": True
            }
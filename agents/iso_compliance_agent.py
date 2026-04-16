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

        def verify_manufacturing(self, protocol: str, sector: str = "cosmetique", product_type: str = "produit", norme_checked: str = "ISO 22716:2007") -> dict:
        retriever = self.db.as_retriever(search_kwargs={"k": 4})
        
        chain = (
            {"context": retriever, "protocol": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
        try:
            raw = chain.invoke(protocol)
            raw = raw.replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)
            
            # 🌟 Appel dynamique au LLM pour les normes complémentaires
            result["normes_complementaires"] = self.get_complementary_standards(sector, product_type, norme_checked)
            return result
            
        except Exception as e:
            return {
                "conformite_globale": "ERREUR",
                "score_risque": 0,
                "violations": [{"etape": "Système", "ecart": str(e), "reference_iso": "N/A"}],
                "actions_correctives": ["Vérifier le protocole ou la connexion API"],
                "validation_humaine_requise": True,
                "normes_complementaires": []
            }

    def get_complementary_standards(self, sector: str, product_type: str, checked_standard: str) -> list:
        """
        Demande au LLM de recommander 3 normes ISO complémentaires pertinentes,
        en excluant strictement la norme déjà auditée.
        """
        prompt = f"""
Tu es un expert senior en conformité industrielle et certification ISO.
Contexte : Un protocole de fabrication pour le secteur "{sector}" (produit : {product_type}) vient d'être audité selon la norme "{checked_standard}".

TÂCHE : Recommande exactement 3 normes ISO/IEC complémentaires pertinentes pour ce secteur/produit.
⛔ RÈGLE ABSOLUE : N'inclus JAMAIS "{checked_standard}" dans ta réponse.

Pour chaque norme, retourne :
- "norme" : numéro officiel (ex: "ISO 9001:2015")
- "titre" : titre court officiel
- "pertinence" : pourquoi cette norme est utile pour ce produit/secteur (1 phrase)
- "avantages" : liste de 2 à 3 bénéfices concrets (certification, marché, qualité, sécurité, environnement, coûts...)

FORMAT DE SORTIE STRICT (JSON valide uniquement, AUCUN texte supplémentaire, AUCUN markdown) :
[
  {{"norme": "...", "titre": "...", "pertinence": "...", "avantages": ["...", "..."]}},
  {{"norme": "...", "titre": "...", "pertinence": "...", "avantages": ["...", "..."]}},
  {{"norme": "...", "titre": "...", "pertinence": "...", "avantages": ["...", "..."]}}
]
"""
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Nettoyer le markdown si le LLM en ajoute malgré la consigne
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            standards = json.loads(content)
            return standards[:3]  # Garder max 3 recommandations
            
        except Exception as e:
            print(f"⚠️ Erreur recommandation LLM: {e}")
            return self._fallback_standards(sector)

    def _fallback_standards(self, sector: str) -> list:
        """Fallback statique si le LLM échoue ou renvoie un JSON invalide"""
        fallbacks = {
            "cosmetique": [
                {"norme": "ISO 9001:2015", "titre": "Management de la qualité", "pertinence": "Standard transversal pour optimiser tes processus", "avantages": ["Amélioration continue", "Satisfaction client", "Reconnaissance internationale"]},
                {"norme": "ISO 14001:2015", "titre": "Management environnemental", "pertinence": "Réduire l'impact écologique de ta production", "avantages": ["Conformité réglementaire", "Image RSE", "Optimisation ressources"]}
            ],
            "agroalimentaire": [
                {"norme": "ISO 22002-1:2009", "titre": "Prérequis pour la sécurité des aliments", "pertinence": "Complément technique aux BPH et PRP", "avantages": ["Audit facilité", "Bonnes pratiques standardisées", "Réduction risques contamination"]},
                {"norme": "ISO 9001:2015", "titre": "Management de la qualité", "pertinence": "Optimiser la qualité globale au-delà de la sécurité", "avantages": ["Efficacité processus", "Satisfaction client", "Amélioration continue"]}
            ],
            "medical": [
                {"norme": "ISO 14971:2019", "titre": "Gestion des risques dispositifs médicaux", "pertinence": "Obligatoire pour compléter ISO 13485", "avantages": ["Sécurité patients", "Conformité UE MDR/FDA", "Vigilance proactive"]},
                {"norme": "ISO 13485:2016", "titre": "SMQ Dispositifs Médicaux", "pertinence": "Référence qualité sectorielle", "avantages": ["Accès marchés régulés", "Traçabilité renforcée", "Confiance autorités"]}
            ],
            "general": [
                {"norme": "ISO 9001:2015", "titre": "Management de la qualité", "pertinence": "Socle qualité universel", "avantages": ["Reconnaissance mondiale", "Processus optimisés", "Satisfaction client"]}
            ]
        }
        return fallbacks.get(sector, fallbacks["general"])
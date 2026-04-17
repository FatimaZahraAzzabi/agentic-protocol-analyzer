# agents/email_notification_agent.py
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI

class EmailNotificationAgent:
    def __init__(self, smtp_config: Optional[Dict] = None):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        
        # Configuration SMTP (valeurs par défaut sécurisées)
        self.smtp_config = smtp_config or {
            "server": "smtp.gmail.com",
            "port": 587,
            "sender": "noreply@compliance.local",
            "password": "",  # À définir via variables d'environnement
            "use_tls": True
        }
        
    def generate_email_draft(self, product_info: Dict, team: List[Dict], 
                           launch_details: Dict) -> Dict:
        """Génère un draft d'email professionnel pour lancer la production"""
        
        team_summary = "\n".join([
            f"• {m['name']} ({m.get('assigned_project_role', m['role'])}): {m.get('email', 'N/A')}"
            for m in team
        ])
        
        prompt = f"""
TÂCHE: Générer un email professionnel pour lancer la production.

PRODUIT:
{json.dumps(product_info, indent=2, ensure_ascii=False)[:1500]}

ÉQUIPE ASSIGNÉE:
{team_summary}

DÉTAILS DU LANCEMENT (champs à compléter):
{json.dumps({k: v for k, v in launch_details.items() if k not in ['team']}, indent=2, ensure_ascii=False)}

Génère un email avec:
1. Sujet clair et actionnable
2. Introduction personnalisée mentionnant le produit et son importance
3. Rôles et responsabilités de chaque membre
4. Dates/délais clés avec [PLACEHOLDER] pour les champs variables
5. Appel à l'action clair
6. Contacts pour questions

FORMAT DE RÉPONSE (JSON strict):
{{
  "subject": "Sujet professionnel",
  "email_body": "Corps avec [PLACEHOLDER] pour: [START_DATE], [END_DATE], [BATCH_NUMBER], etc.",
  "placeholders_to_fill": [
    {{"name": "START_DATE", "label": "Date de début production", "type": "date", "required": true}},
    {{"name": "BATCH_NUMBER", "label": "Numéro de lot", "type": "text", "required": true}}
  ],
  "recipient_count": {len(team)},
  "team_roles_mentioned": ["Responsable Qualité", "Chef de Production"],
  "priority": "high" // low/medium/high
}}
"""

        try:
            response = self.llm.invoke(prompt)
            return self._parse_json_response(response.content)
        except Exception as e:
            return {
                "error": str(e),
                "subject": f"Lancement: {product_info.get('name', 'Produit')}",
                "email_body": "Email généré en mode fallback.",
                "placeholders_to_fill": []
            }

    def send_email_to_team(self, email_content: Dict, team_members: List[Dict], 
                          filled_values: Optional[Dict] = None, 
                          simulate_only: bool = True) -> Dict:
        """
        Envoie (ou simule) les emails aux membres de l'équipe.
        
        Args:
            simulate_only: Si True, ne pas envoyer réellement (mode démo/dev)
        """
        if filled_values is None:
            filled_values = {}
        
        # Remplacer les placeholders
        email_body = email_content.get("email_body", "")
        for key, value in filled_values.items():
            email_body = email_body.replace(f"[{key}]", str(value))
        
        email_subject = email_content.get("subject", "Lancement Production")
        
        results = {
            "total_recipients": len(team_members),
            "successful": 0,
            "failed": 0,
            "simulated": 0,
            "details": []
        }
        
        for member in team_members:
            member_email = member.get("email")
            member_name = member.get("name", "Collègue")
            
            if not member_email or member_email == "N/A":
                results["details"].append({
                    "name": member_name,
                    "status": "skipped",
                    "reason": "Email non disponible"
                })
                continue
            
            try:
                # Personnaliser le message
                personalized_body = self._personalize_email(email_body, member_name, member.get("assigned_project_role", ""))
                
                if simulate_only or not self.smtp_config.get("password"):
                    # Mode simulation (recommandé pour démo)
                    results["simulated"] += 1
                    status = "simulated"
                    reason = "Mode démo - email généré mais non envoyé"
                else:
                    # Envoi réel via SMTP
                    status, reason = self._send_via_smtp(
                        to_email=member_email,
                        subject=email_subject,
                        body=personalized_body
                    )
                    if status == "sent":
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                
                results["details"].append({
                    "name": member_name,
                    "email": member_email,
                    "status": status,
                    "reason": reason
                })
                
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "name": member_name,
                    "email": member_email,
                    "status": "error",
                    "reason": str(e)
                })
        
        return results

    def _personalize_email(self, body: str, name: str, role: str) -> str:
        """Personnalise le corps de l'email pour un destinataire"""
        personalized = body.replace("[TEAM_MEMBER_NAME]", name)
        personalized = personalized.replace("[TEAM_MEMBER_ROLE]", role)
        return personalized

    def _send_via_smtp(self, to_email: str, subject: str, body: str) -> tuple:
        """Envoie l'email via SMTP (à activer en production)"""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_config["sender"]
            msg["To"] = to_email
            
            # Version HTML
            html_body = body.replace("\n\n", "</p><p>").replace("\n", "<br>")
            html_part = MIMEText(f"<html><body><p>{html_body}</p></body></html>", "html")
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"]) as server:
                if self.smtp_config.get("use_tls"):
                    server.starttls()
                if self.smtp_config.get("password"):
                    server.login(self.smtp_config["sender"], self.smtp_config["password"])
                server.send_message(msg)
            
            return "sent", "Email envoyé avec succès"
        except Exception as e:
            return "failed", f"Erreur SMTP: {str(e)}"

    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON robuste"""
        import re
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {"error": "Parsing JSON échoué", "email_body": "", "placeholders_to_fill": []}
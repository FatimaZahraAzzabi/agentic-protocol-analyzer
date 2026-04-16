# 📁 agents/guardrails.py
import re

class AuditGuardrails:
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Bloque les injections de prompt courantes"""
        dangerous = [r"ignore previous", r"system prompt", r"<script>", r"DROP TABLE", r"eval\("]
        for pattern in dangerous:
            text = re.sub(pattern, "[BLOQUÉ]", text, flags=re.I)
        return text.strip()

    @staticmethod
    def validate_output(data: dict) -> bool:
        """Vérifie la structure JSON attendue"""
        required = ["conformite_globale", "score_risque", "violations"]
        return all(k in data for k in required) and isinstance(data["score_risque"], (int, float))
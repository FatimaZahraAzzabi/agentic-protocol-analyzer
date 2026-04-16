# 📁 api/views.py - STRUCTURE CORRECTE
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# 1. Charger .env AVANT tout
load_dotenv()

# 2. Ajouter la racine au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 3. Imports Flask
from flask import Flask, request, jsonify, send_from_directory

# 4. Imports de tes agents
from agents.rag_manager import DynamicRAGManager

# 5. ⚠️ CRÉER L'INSTANCE FLASK ICI (avant les @app.route !)
flask_app = Flask(__name__, 
                  static_folder='../ui/static', 
                  template_folder='../ui')

# 6. Initialiser le RAG Manager
rag_manager = DynamicRAGManager(db_path="data/vector_db")

# ==================== ROUTES ====================

# Route: Page d'accueil
@flask_app.route('/')
def index():
    return send_from_directory('../ui', 'index.html')

# Route: Upload norme (Admin)
@flask_app.route('/api/upload-norme', methods=['POST'])
def upload_norme():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Aucun fichier PDF"}), 400
    
    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return jsonify({"error": "Nom de fichier vide"}), 400
    
    norme_name = request.form.get('norme_name', 'Norme Personnalisée')
    
    upload_folder = "data/normes_uploaded"
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, secure_filename(pdf_file.filename))
    pdf_file.save(filepath)
    
    try:
        result = rag_manager.upload_norme(
            norme_name=norme_name,
            pdf_file_path=filepath,
            description=request.form.get('description', ''),
            category=request.form.get('category', 'interne')
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# Route: Liste des normes
@flask_app.route('/api/list-normes', methods=['GET'])
def list_normes():
    try:
        normes = rag_manager.get_indexed_normes()
        stats = rag_manager.get_stats()
        return jsonify({"normes": normes, **stats}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route: Audit fabrication
@flask_app.route('/api/audit-fabrication', methods=['POST'])
def audit_fabrication():
    if 'protocol_pdf' not in request.files:
        return jsonify({"error": "Aucun PDF de protocole"}), 400
    
    pdf_file = request.files['protocol_pdf']
    norme_ref = request.form.get('norme_reference')
    
    if pdf_file.filename == '' or not pdf_file.filename.endswith('.pdf'):
        return jsonify({"error": "Fichier PDF invalide"}), 400
    
    # Sauvegarde temporaire
    import uuid
    temp_path = f"data/temp_protocol_{uuid.uuid4().hex}.pdf"
    os.makedirs("data", exist_ok=True)
    pdf_file.save(temp_path)
    
    try:
        # 1. Extraction texte du PDF protocole
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(temp_path)
        protocol_text = "\n".join([doc.page_content for doc in loader.load()]).lower()
        
        # 2. Recherche RAG filtrée par norme
        context_docs = rag_manager.search(
            query="hygiène EPI température documentation contrôle qualité ISO 22716",
            k=6,
            norme_filter=norme_ref
        )
        context_text = "\n\n".join([d.page_content for d in context_docs])
        
        # 3. Détection intelligente des violations (règles métier)
        violations = []
        score_risque = 0
        
        # Vérification 1: EPI & Hygiène (ISO 22716 Section 7.2)
        if not any(mot in protocol_text for mot in ['epi', 'gants', 'lunettes', 'blouse', 'hygiène', 'désinfection']):
            violations.append({
                "etape": "Hygiène & EPI",
                "ecart": "Aucune mention des Équipements de Protection Individuelle (gants, lunettes, blouse) ni procédure d'hygiène",
                "reference_iso": "ISO 22716:2007 - Section 7.2 (Personnel & Hygiène)"
            })
            score_risque += 3
        
        # Vérification 2: Température critique (ISO 22716 Section 8.2)
        if 'température' not in protocol_text and '°c' not in protocol_text and 'degré' not in protocol_text:
            violations.append({
                "etape": "Paramètres de Production",
                "ecart": "Température de chauffe non spécifiée (risque de dégradation >75°C)",
                "reference_iso": "ISO 22716:2007 - Section 8.2 (Contrôle des opérations)"
            })
            score_risque += 2
        
        # Vérification 3: Documentation & Traçabilité (ISO 22716 Section 12)
        if not any(mot in protocol_text for mot in ['fiche de lot', 'traçabilité', 'enregistrement', 'documentation', 'batch']):
            violations.append({
                "etape": "Documentation",
                "ecart": "Absence de procédure de traçabilité et fiche de lot",
                "reference_iso": "ISO 22716:2007 - Section 12 (Documentation)"
            })
            score_risque += 2
        
        # Vérification 4: Contrôle microbiologique (ISO 22716 Section 9.3)
        if 'challenge test' in protocol_text or 'microbiolog' in protocol_text:
            if not any(mot in protocol_text for mot in ['critère', 'acceptation', 'limite', 'norme']):
                violations.append({
                    "etape": "Contrôle Qualité Microbiologique",
                    "ecart": "Challenge test mentionné sans critères d'acceptation définis",
                    "reference_iso": "ISO 22716:2007 - Section 9.3 (Contrôles microbiologiques)"
                })
                score_risque += 1
        
        # Actions correctives dynamiques
        actions_correctives = []
        if any(v['etape'] == 'Hygiène & EPI' for v in violations):
            actions_correctives.append("Ajouter une section 'Hygiène & EPI' avec procédure de désinfection des cuves et port obligatoire de gants/lunettes/blouse")
        if any(v['etape'] == 'Paramètres de Production' for v in violations):
            actions_correctives.append("Spécifier température max 75°C et durée max de chauffe dans le procédé")
        if any(v['etape'] == 'Documentation' for v in violations):
            actions_correctives.append("Créer un template de fiche de lot avec traçabilité complète des matières premières")
        if any(v['etape'] == 'Contrôle Qualité Microbiologique' for v in violations):
            actions_correctives.append("Définir critères d'acceptation pour le challenge test (log reduction ≥ 3)")
        
        # Détermination du statut
        conformite_globale = "CONFORME" if score_risque < 3 else "NON CONFORME"
        
        result = {
            "conformite_globale": conformite_globale,
            "score_risque": min(score_risque, 10),
            "violations": violations,
            "actions_correctives": actions_correctives
        }
        
        return jsonify({"compliance_result": result}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
# Route: Health check
@flask_app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "API running"}), 200


# Pour la génération PDF backend
@flask_app.route('/api/generate-report-pdf', methods=['POST'])
def generate_report_pdf():
    from agents.report_agent import ReportAgent
    from flask import send_file
    from datetime import datetime
    
    data = request.json
    audit_result = data.get('compliance_result', {})
    protocol_text = data.get('protocol_text', '')
    norme_ref = data.get('norme_reference', 'ISO 22716:2007')
    
    report_agent = ReportAgent()
    pdf_buffer = report_agent.generate_pdf(audit_result, protocol_text, norme_ref)
    
    filename = f"Rapport_Audit_{norme_ref.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    print("🚀 Serveur démarré sur http://localhost:5000")
    flask_app.run(debug=True, host="0.0.0.0", port=5000)
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
@flask_app.route('/api/audit-fabrication', methods=['POST'])
def audit_fabrication():
    if 'protocol_pdf' not in request.files:
        return jsonify({"error": "Aucun PDF de protocole"}), 400
    
    pdf_file = request.files['protocol_pdf']
    norme_ref = request.form.get('norme_reference', 'ISO 22716:2007')
    # 🔑 NOUVEAU: Récupérer le secteur choisi par l'utilisateur
    sector = request.form.get('sector', 'cosmetique') 
    
    if pdf_file.filename == '' or not pdf_file.filename.endswith('.pdf'):
        return jsonify({"error": "Fichier PDF invalide"}), 400
    
    import uuid
    temp_path = f"data/temp_protocol_{uuid.uuid4().hex}.pdf"
    os.makedirs("data", exist_ok=True)
    pdf_file.save(temp_path)
    
    try:
        # 1. Extraction du texte (identique à avant)
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(temp_path)
        protocol_text = "\n".join([doc.page_content for doc in loader.load()])
        
        # 2. APPEL À L'AGENT (C'est lui qui fait tout le travail maintenant)
        from agents.iso_compliance_agent import ISOComplianceAgent
        agent = ISOComplianceAgent()
        
        # L'agent va :
        # 1. Chercher dans RAG
        # 2. Comparer via LLM
        # 3. Générer les recommandations de normes complémentaires
        result = agent.verify_manufacturing(
            protocol=protocol_text, 
            norme_ref=norme_ref, 
            sector=sector
        )
        
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
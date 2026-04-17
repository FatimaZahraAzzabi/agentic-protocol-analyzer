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

try:
    from langchain_community.document_loaders import PyPDFLoader
except ImportError:
    PyPDFLoader = None

# 5. ⚠️ CRÉER L'INSTANCE FLASK ICI (avant les @app.route !)
flask_app = Flask(__name__, 
                  static_folder='../ui/static', 
                  template_folder='../ui')

# 6. Initialiser le RAG Manager
try:
    rag_manager = DynamicRAGManager(db_path="data/vector_db")
except ImportError as e:
    rag_manager = None
    rag_error = str(e)
else:
    rag_error = None

# ==================== ROUTES ====================

# Route: Page d'accueil
@flask_app.route('/')
def index():
    return send_from_directory('../ui', 'index.html')

# Route: Upload norme (Admin)
@flask_app.route('/api/upload-norme', methods=['POST'])
def upload_norme():
    if rag_manager is None:
        return jsonify({"error": f"Impossible de charger le RAG Manager: {rag_error}"}), 500

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
            category=request.form.get('category', 'interne'),
            sector=request.form.get('sector', 'autre')
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
    if rag_manager is None:
        return jsonify({"error": f"Impossible de charger le RAG Manager: {rag_error}"}), 500

    try:
        normes = rag_manager.get_indexed_normes()
        stats = rag_manager.get_stats()
        return jsonify({"normes": normes, **stats}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route: Audit fabrication
@flask_app.route('/api/audit-fabrication', methods=['POST'])
def audit_fabrication():
    norme_ref = 'ISO 22716:2007'
    sector = 'cosmetique'
    protocol_text = None

    if 'protocol_pdf' in request.files:
        pdf_file = request.files['protocol_pdf']
        if pdf_file.filename == '':
            return jsonify({"error": "Fichier PDF vide"}), 400

        norme_ref = request.form.get('norme_reference', norme_ref)
        sector = request.form.get('sector', sector)

        upload_folder = "data/normes_uploaded"
        os.makedirs(upload_folder, exist_ok=True)
        temp_path = os.path.join(upload_folder, secure_filename(pdf_file.filename))
        pdf_file.save(temp_path)

        if PyPDFLoader is None:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({"error": "Le module langchain_community n'est pas installé. Installez-le pour pouvoir extraire le contenu du PDF."}), 500

        try:
            loader = PyPDFLoader(temp_path)
            protocol_text = "\n".join([doc.page_content for doc in loader.load()])
        except Exception as e:
            return jsonify({"error": f"Impossible d'extraire le PDF: {str(e)}"}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    else:
        data = request.get_json(silent=True) or {}
        protocol_text = data.get('protocol')
        norme_ref = data.get('norme_reference', norme_ref)
        sector = data.get('sector', sector)

        if not protocol_text:
            return jsonify({"error": "Aucun protocole fourni dans le corps JSON."}), 400

    try:
        from agents.iso_compliance_agent import ISOComplianceAgent
        agent = ISOComplianceAgent()
    except Exception as e:
        return jsonify({"error": f"Impossible de charger l'agent de conformité: {str(e)}"}), 500
    
    result = agent.verify_manufacturing(
        protocol=protocol_text,
        norme_ref=norme_ref,
        sector=sector,
        product_type="produit"
    )
    
    # Générer automatiquement le protocole corrigé
    corrected_protocol = agent.generate_corrected_protocol(
        original_protocol=protocol_text,
        violations=result.get('violations', []),
        actions_correctives=result.get('actions_correctives', []),
        norme_ref=norme_ref,
        sector=sector,
        product_type="produit"
    )
    
    return jsonify({
        "compliance_result": result,
        "corrected_protocol": corrected_protocol,
        "original_protocol": protocol_text
    }), 200

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


@flask_app.route('/api/generate-diagnostic-pdf', methods=['POST'])
def generate_diagnostic_pdf():
    """Génère le PDF de diagnostic de l'ancien protocole (erreurs et risques)"""
    from agents.report_agent import ReportAgent
    from flask import send_file
    from datetime import datetime
    
    data = request.json
    audit_result = data.get('compliance_result', {})
    protocol_text = data.get('protocol_text', '')
    norme_ref = data.get('norme_reference', 'ISO 22716:2007')
    
    report_agent = ReportAgent()
    pdf_buffer = report_agent.generate_diagnostic_pdf(audit_result, protocol_text, norme_ref)
    
    filename = f"Diagnostic_{norme_ref.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@flask_app.route('/api/generate-corrected-pdf', methods=['POST'])
def generate_corrected_pdf():
    """Génère le PDF du protocole corrigé"""
    from agents.report_agent import ReportAgent
    from flask import send_file
    from datetime import datetime
    
    data = request.json
    audit_result = data.get('compliance_result', {})
    corrected_protocol = data.get('corrected_protocol', '')
    norme_ref = data.get('norme_reference', 'ISO 22716:2007')
    
    report_agent = ReportAgent()
    pdf_buffer = report_agent.generate_corrected_protocol_pdf(corrected_protocol, norme_ref)
    
    filename = f"Protocole_Corrige_{norme_ref.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@flask_app.route('/api/suggest-employees', methods=['POST'])
def suggest_employees():
    """Retourne les employés matchés selon les exigences du protocole audité"""
    data = request.json
    # On utilise les violations + contexte pour construire la requête de matching
    requirements = data.get('requirements', '')
    
    if not requirements:
        return jsonify({"error": "Aucune exigence fournie"}), 400
        
    try:
        suggestions = rag_manager.search_employees(requirements, k=3)
        return jsonify({"employees": suggestions}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    print("🚀 Serveur démarré sur http://localhost:5000")
    flask_app.run(debug=True, host="0.0.0.0", port=5000)
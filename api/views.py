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
        # Extraction texte du PDF protocole
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(temp_path)
        protocol_text = "\n".join([doc.page_content for doc in loader.load()])
        
        # Recherche RAG filtrée par norme
        context_docs = rag_manager.search(
            query=protocol_text[:500],
            k=4,
            norme_filter=norme_ref
        )
        context_text = "\n\n".join([d.page_content for d in context_docs])
        
        # Mock de résultat pour la démo (remplace par ton vrai agent)
        result = {
            "conformite_globale": "NON CONFORME" if "85" in protocol_text else "CONFORME",
            "score_risque": 7 if "85" in protocol_text else 2,
            "violations": [
                {"etape": "Chauffage", "ecart": "Température > 75°C", "reference_iso": norme_ref}
            ] if "85" in protocol_text else [],
            "actions_correctives": ["Réduire température à 70°C max"] if "85" in protocol_text else []
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

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    print("🚀 Serveur démarré sur http://localhost:5000")
    flask_app.run(debug=True, host="0.0.0.0", port=5000)
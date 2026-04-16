import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# 📍 Configuration des chemins (Automatique peu importe où tu lances le script)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # Remonte d'un cran vers 'agentic-protocol-analyzer'

# 🔑 Chargement de la clé API
load_dotenv(PROJECT_ROOT / ".env")

if not os.getenv("OPENAI_API_KEY"):
    print("❌ ERREUR : OPENAI_API_KEY non trouvée dans le fichier .env")
    sys.exit(1)

def build_knowledge_base():
    print("🚀 DÉBUT DE L'INDEXATION RAG")
    
    # 📂 Chemin vers les normes
    pdf_folder = PROJECT_ROOT / "data" / "normes"
    output_path = PROJECT_ROOT / "data" / "vector_db"
    
    if not pdf_folder.exists():
        print(f"❌ Dossier non trouvé : {pdf_folder}")
        return

    print(f"📖 Lecture des PDFs dans : {pdf_folder}")
    documents = []
    
    # 1. Charger les PDFs
    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf"):
            filepath = pdf_folder / filename
            try:
                loader = PyPDFLoader(str(filepath))
                docs = loader.load()
                documents.extend(docs)
                print(f"   ✅ Lu : {filename} ({len(docs)} pages)")
            except Exception as e:
                print(f"   ⚠️ Erreur lecture {filename} : {e}")
    
    if not documents:
        print("❌ Aucun document trouvé. Vérifie le dossier data/normes.")
        return

    # 2. Créer la base vectorielle
    print(f"\n🧠 Création des embeddings ({len(documents)} chunks)...")
    try:
        embeddings = OpenAIEmbeddings()
        db = FAISS.from_documents(documents, embeddings)
        
        # 3. Sauvegarder
        output_path.mkdir(parents=True, exist_ok=True)
        db.save_local(str(output_path))
        print(f"✅ SUCCÈS : Base RAG sauvegardée dans {output_path}")
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE : {e}")

if __name__ == "__main__":
    build_knowledge_base()
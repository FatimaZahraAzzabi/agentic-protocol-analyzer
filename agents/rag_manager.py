# 📁 agents/rag_manager.py
"""
Dynamic RAG Manager - Gestion de la base de connaissances normative
Permet l'upload dynamique de PDF et la recherche avec filtrage par métadonnées
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    FAISS = None
    PyPDFLoader = None
    OpenAIEmbeddings = None
from langchain_core.documents import Document

class DynamicRAGManager:
    """Gestionnaire RAG dynamique pour l'indexation et la recherche de normes"""
    
    def __init__(self, db_path: str = "data/vector_db"):
        """
        Initialise le manager RAG
        
        Args:
            db_path: Chemin vers le dossier de sauvegarde de la base FAISS
        """
        if FAISS is None or PyPDFLoader is None or OpenAIEmbeddings is None:
            raise ImportError(
                "Il manque les dépendances LangChain. Installez langchain_community et langchain_openai."
            )

        self.db_path = Path(db_path)
        self.embeddings = OpenAIEmbeddings()
        self.db = None
        self._load_or_create_db()
    
    def _load_or_create_db(self):
        """Charge la base existante ou crée une nouvelle base vide"""
        try:
            if self.db_path.exists():
                self.db = FAISS.load_local(
                    str(self.db_path), 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                print(f"Base RAG chargée depuis {self.db_path}")
            else:
                # Crée une base vide avec un document placeholder
                placeholder = Document(page_content="", metadata={"init": True})
                self.db = FAISS.from_documents([placeholder], self.embeddings)
                self.db_path.mkdir(parents=True, exist_ok=True)
                self.db.save_local(str(self.db_path))
                print(f"Nouvelle base RAG créée: {self.db_path}")
        except Exception as e:
            print(f"Erreur chargement base: {e}")
            # Fallback: base vide
            placeholder = Document(page_content="", metadata={"init": True})
            self.db = FAISS.from_documents([placeholder], self.embeddings)
    
    def upload_norme(
        self, 
        norme_name: str, 
        pdf_file_path: str,
        description: str = "",
        category: str = "interne",
        sector: str = "autre",
        user_id: str = "admin",
        project_id: str = "conformite_cosmetique"
    ) -> Dict:
        """
        Upload et indexation d'une nouvelle norme PDF
        
        Args:
            norme_name: Nom de la norme (ex: "ISO 22716:2007")
            pdf_file_path: Chemin vers le fichier PDF
            description: Description optionnelle
            category: Catégorie (international/national/guide/interne)
            user_id: ID de l'utilisateur qui upload
            project_id: ID du projet associé
            
        Returns:
            Dict avec statut et nombre de chunks créés
        """
        # Charger le PDF
        loader = PyPDFLoader(pdf_file_path)
        docs = loader.load()
        
        # Métadonnées communes à tous les chunks de ce document
        base_metadata = {
            "user_id": user_id,
            "project_id": project_id,
            "norme_name": norme_name,
            "sector": sector,
            "description": description,
            "category": category,
            "filename": os.path.basename(pdf_file_path),
            "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "doc_id": str(uuid.uuid4())
        }
        
        # Attacher les métadonnées à chaque chunk
        for doc in docs:
            doc.metadata.update(base_metadata)
        
        # Ajouter à la base vectorielle
        self.db.add_documents(docs)
        
        # Sauvegarder sur disque
        self.db.save_local(str(self.db_path))
        
        return {
            "status": "success",
            "chunks_added": len(docs),
            "norme_name": norme_name,
            "filename": base_metadata["filename"]
        }
    
    def search(
        self, 
        query: str, 
        k: int = 4,
        user_id: Optional[str] = None,
        norme_filter: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[Document]:
        """
        Recherche dans la base RAG avec filtrage optionnel
        
        Args:
            query: Texte de la requête
            k: Nombre de résultats à retourner
            user_id: Filtrer par utilisateur (optionnel)
            norme_filter: Filtrer par nom de norme (optionnel)
            category_filter: Filtrer par catégorie (optionnel)
            
        Returns:
            Liste de documents LangChain pertinents
        """
        # Construire le filtre FAISS
        filter_dict = {}
        if user_id:
            filter_dict["user_id"] = user_id
        if norme_filter:
            filter_dict["norme_name"] = norme_filter
        if category_filter:
            filter_dict["category"] = category_filter
        
        # Recherche avec filtrage
        if filter_dict:
            results = self.db.similarity_search(query, k=k, filter=filter_dict)
        else:
            results = self.db.similarity_search(query, k=k)
        
        return results
    
    def get_indexed_normes(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Retourne la liste des normes indexées avec leurs métadonnées
        
        Args:
            user_id: Filtrer par utilisateur (optionnel)
            
        Returns:
            Liste de dictionnaires avec infos sur chaque norme
        """
        # Récupérer un large échantillon pour extraire les métadonnées uniques
        all_docs = self.db.similarity_search("", k=10000)
        
        # Grouper par norme_name
        normes_map = {}
        for doc in all_docs:
            meta = doc.metadata
            name = meta.get("norme_name")

            # Skip le document placeholder d'initialisation
            if meta.get("init"):
                continue

            # Ignorer les documents sans nom de norme valide
            if not name or not str(name).strip():
                continue

            if name not in normes_map:
                normes_map[name] = {
                    "name": name,
                    "description": meta.get("description", ""),
                    "category": meta.get("category", "interne"),
                    "sector": meta.get("sector", "autre"),
                    "filename": meta.get("filename", ""),
                    "upload_date": meta.get("upload_date", ""),
                    "user_id": meta.get("user_id", "unknown"),
                    "chunks": 0
                }
            normes_map[name]["chunks"] += 1
        
        # Filtrer par user si spécifié
        result = list(normes_map.values())
        if user_id:
            result = [n for n in result if n.get("user_id") == user_id]
        
        # Trier par date d'upload (plus récent en premier)
        result.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
        
        return result
    
    def delete_norme(self, norme_name: str, user_id: str = "admin") -> bool:
        """
        Supprime une norme de la base (feature optionnelle)
        
        Note: FAISS ne supporte pas nativement la suppression par filtre.
        Cette méthode recrée la base sans les documents à supprimer.
        """
        # Récupérer tous les documents
        all_docs = self.db.similarity_search("", k=10000)
        
        # Filtrer ceux à garder
        docs_to_keep = [
            doc for doc in all_docs 
            if doc.metadata.get("norme_name") != norme_name 
            or doc.metadata.get("user_id") != user_id
        ]
        
        # Recréer la base
        if docs_to_keep:
            self.db = FAISS.from_documents(docs_to_keep, self.embeddings)
        else:
            # Base vide avec placeholder
            placeholder = Document(page_content="", metadata={"init": True})
            self.db = FAISS.from_documents([placeholder], self.embeddings)
        
        self.db.save_local(str(self.db_path))
        return True
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques sur la base"""
        all_docs = self.db.similarity_search("", k=10000)
        
        # Compter par catégorie
        categories = {}
        for doc in all_docs:
            if doc.metadata.get("init"):
                continue
            cat = doc.metadata.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_chunks": len([d for d in all_docs if not d.metadata.get("init")]),
            "total_normes": len(self.get_indexed_normes()),
            "categories": categories
        }
    
    import json

def index_employees(self, employees_json_path: str = "data/employees.json"):
    """Indexe les profils employés dans FAISS"""
    with open(employees_json_path, 'r', encoding='utf-8') as f:
        employees = json.load(f)
        
    docs = []
    for emp in employees:
        # On crée un "document texte" riche pour le matching sémantique
        text = (
            f"{emp['name']} - {emp['role']} | "
            f"Compétences: {', '.join(emp['skills'])} | "
            f"Certifications: {', '.join(emp['certifications'])} | "
            f"Expérience: {emp['experience']} ans | "
            f"Disponibilité: {emp['availability']}"
        )
        # On attache TOUTES les métadonnées pour les retourner plus tard
        docs.append(Document(page_content=text, metadata={"type": "employee", **emp}))
        
    self.db.add_documents(docs)
    self.db.save_local(str(self.db_path))
    print(f"✅ {len(docs)} profils employés indexés dans FAISS")

def search_employees(self, requirements: str, k: int = 3) -> list:
    """Retourne les employés les plus匹配 aux exigences du protocole"""
    # FAISS retourne (Document, distance). Distance faible = forte similarité
    results = self.db.similarity_search_with_score(
        requirements, 
        k=k, 
        filter={"type": "employee"}
    )
    
    suggestions = []
    for doc, distance in results:
        meta = doc.metadata
        # Conversion distance → score % (plus la distance est faible, plus le score est haut)
        match_score = round(max(0, (1 - distance) * 100), 1)
        
        suggestions.append({
            "name": meta["name"],
            "role": meta["role"],
            "match_score": match_score,
            "skills": meta["skills"][:3],  # Top 3 compétences
            "certifications": meta["certifications"],
            "experience": meta["experience"],
            "availability": meta["availability"],
            "photo": meta.get("photo", "https://i.pravatar.cc/150?img=12")
        })
    return suggestions
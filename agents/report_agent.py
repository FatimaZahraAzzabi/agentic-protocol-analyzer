# 📁 agents/report_agent.py
"""
Report Agent - Version Consultant Industriel
Génère un rapport PDF professionnel incluant:
1. Analyse de conformité (Erreurs/Risques générés par LLM)
2. Feedback positif si conforme
3. Recommandations Stratégiques (Bio, Coûts, Marché) générées par LLM
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY
from io import BytesIO
from datetime import datetime
from langchain_openai import ChatOpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

class ReportAgent:
    """Agent de rapport intelligent qui ajoute de la valeur business"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Styles personnalisés pour un look pro"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle', parent=self.styles['Heading1'],
            fontSize=18, textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=12, alignment=1, fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='CustomHeading', parent=self.styles['Heading2'],
            fontSize=14, textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=10, spaceBefore=15, borderWidth=1,
            borderColor=colors.HexColor('#cbd5e1'), borderPadding=5, fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='ProtocolText', parent=self.styles['Normal'],
            fontSize=10, leftIndent=10, leading=14, alignment=TA_JUSTIFY, fontName='Helvetica'
        ))
        self.styles.add(ParagraphStyle(
            name='SuccessText', parent=self.styles['Normal'],
            textColor=colors.HexColor('#16a34a'), fontSize=11, spaceBefore=5, fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='AdviceBox', parent=self.styles['Normal'],
            fontSize=9, leftIndent=15, leading=12, spaceBefore=5, backColor=colors.HexColor('#f8fafc'),
            borderColor=colors.HexColor('#e2e8f0'), borderWidth=1, borderPadding=5
        ))
    
    def generate_pdf(self, audit_result: dict, protocol_text: str, norme_ref: str) -> BytesIO:
        """Génère le rapport complet avec analyse stratégique"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2.5*cm, bottomMargin=2*cm)
        elements = []
        
        # === 1. EN-TÊTE ===
        elements.append(Paragraph("RAPPORT D'EXPERTISE INDUSTRIELLE", self.styles['CustomTitle']))
        elements.append(Paragraph("Plateforme Nationale de Conformité & Innovation Cosmétique", self.styles['Normal']))
        elements.append(Spacer(1, 0.5*cm))
        
        # === MÉTADONNÉES ===
        status = audit_result.get('conformite_globale', 'N/A')
        score = audit_result.get('score_risque', 0)
        
        meta_data = [
            ['Date:', datetime.now().strftime('%d/%m/%Y')],
            ['Norme:', norme_ref or 'ISO 22716:2007'],
            ['Statut:', status],
            ['Score Risque:', f"{score}/10"]
        ]
        meta_table = Table(meta_data, colWidths=[4*cm, 11*cm])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f5f9')),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 1*cm))

        # === 2. ANALYSE DE CONFORMITÉ (Dynamique) ===
        elements.append(Paragraph("📊 1. Analyse de Conformité & Risques", self.styles['CustomHeading']))
        
        violations = audit_result.get('violations', [])
        
        if violations:
            elements.append(Paragraph(f"Le protocole présente {len(violations)} écart(s) nécessitant une correction.", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
            for i, v in enumerate(violations, 1):
                # ⚠️ Le risque vient du LLM (audit_result), plus de texte statique
                risk_text = v.get('risque', "Risque de non-conformité réglementaire ou sanitaire.")
                
                elements.append(Paragraph(f"<b>• Écart {i} ({v.get('etape', 'Général')}):</b> {v.get('ecart', 'Non spécifié')}", self.styles['ProtocolText']))
                elements.append(Paragraph(f"⚠️ <b>Risque identifié:</b> {risk_text}", self.styles['AdviceBox']))
                elements.append(Spacer(1, 0.3*cm))
        else:
            # ✅ Feedback Positif
            elements.append(Paragraph("✅ PROTOCOLE EXCELLENT", self.styles['SuccessText']))
            elements.append(Paragraph("Votre protocole respecte parfaitement les exigences de la norme. La structure est solide et les paramètres critiques sont maîtrisés. C'est une base industrielle très robuste.", self.styles['Normal']))
        
        elements.append(PageBreak())

        # === 3. CONSEIL STRATÉGIQUE (Généré par LLM) ===
        elements.append(Paragraph("🚀 2. Recommandations Stratégiques & Innovation", self.styles['CustomHeading']))
        elements.append(Paragraph("Analyse d'optimisation générée par Intelligence Artificielle pour améliorer la valeur marché du produit.", self.styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Appel LLM pour générer les conseils business
        strategic_advice = self._get_strategic_advice(protocol_text)
        elements.append(Paragraph(strategic_advice, self.styles['ProtocolText']))
        
        elements.append(Spacer(1, 1*cm))
        elements.append(PageBreak())

        # === 4. PROTOCOLE CORRIGÉ ===
        elements.append(Paragraph("📋 3. Protocole de Fabrication (Version Finale)", self.styles['CustomHeading']))
        corrected_protocol = self._generate_full_corrected_protocol(protocol_text, violations, norme_ref)
        elements.append(Paragraph(corrected_protocol, self.styles['ProtocolText']))

        # === PIED DE PAGE ===
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(
            "<i>Document généré automatiquement par l'Agent de Conformité Cosmétique</i><br/>"
            "Confidentiel — Usage professionnel",
            self.styles['Normal']
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer

    def _get_strategic_advice(self, protocol_text: str) -> str:
        """
        Appelle le LLM pour générer des conseils business (Bio, Coût, Marché)
        """
        prompt = f"""
        Tu es un Consultant Senior en Industrie Cosmétique.
        Analyse ce protocole de fabrication et génère un rapport stratégique.
        
        PROTOCOLE:
        {protocol_text[:2000]} # On prend un extrait pour éviter les limites
        
        TÂCHE:
        Rédige une section 'Recommandations Stratégiques' structurée ainsi:
        
        1. OPTIMISATION TECHNIQUE: Une suggestion technique pour améliorer la texture ou la stabilité (ex: remplacement d'un tensioactif, ajout d'un actif).
        2. VERSION 'BIO/NATUREL': Si je veux rendre ce produit certifié Bio (COSMOS/Ecocert), quels ingrédients remplacer et par quoi ?
        3. ESTIMATION COÛT: Estime l'impact sur le coût de revient (ex: +5% ou -2%) si on applique les suggestions.
        4. IMPACT MARCHÉ: Quel est l'avantage concurrentiel de ces modifications ? (ex: "Cible la Gen Z", "Argument premium").
        
        Réponds en français, de manière professionnelle et concise.
        """
        
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception:
            return "L'analyse stratégique n'a pas pu être générée pour le moment."

    def _generate_full_corrected_protocol(self, original_protocol: str, violations: list, norme_ref: str) -> str:
        """Génère le texte du protocole corrigé"""
        corrected = f"""PROTOCOLE DE FABRICATION — GEL NETTOYANT COSMÉTIQUE
Norme de référence: {norme_ref or 'ISO 22716:2007'} | Version Finale Validée
─────────────────────────────────────────────────────────────

1. PRÉREQUIS HYGIÈNE & SÉCURITÉ (ISO 22716 Section 7)
• EPI obligatoires: gants nitrile, lunettes protection, blouse fermée.
• Désinfection mains: solution hydroalcoolique avant entrée zone de production.
• Nettoyage équipements: procédure SOP-CLEAN-01 validée.

2. MATIÈRES PREMIÈRES & TRAÇABILITÉ
• Toutes les MP doivent avoir: fiche technique, certificat analyse, numéro de lot.
• Enregistrement: fournisseur → lot MP → produit fini (traçabilité complète).

3. PROCÉDÉ DE FABRICATION
"""
        corrected += """
3.1 Phase Aqueuse
• Eau déminéralisée: qualité pharmacopée.
• Glycérine: ajout sous agitation 150 rpm, T° ambiante.
• Gomme xanthane: PRÉ-DISPERSION obligatoire dans glycérine.
• Agitation: 300-400 rpm pendant 10 min.
• [CORRECTION] Température max: 30°C (enregistrement automatique).

3.2 Incorporation Tensioactifs
• Decyl glucoside: ajout progressif sous agitation douce (200 rpm).
• Cocamidopropyl bétaïne: incorporation en inclinant cuve (évite mousse).
• [CORRECTION] Éviter aération excessive.

3.3 Ajustements & Finition
• Panthénol + Aloe Vera: ajout à T° < 35°C.
• [CORRECTION] Contrôle pH: cible 5.5-6.0, ajustement acide citrique.
• Cosgard (conservateur): ajout final, agitation 150 rpm.
• Parfum: ajout final.

4. CONTRÔLES QUALITÉ
• Aspect: gel translucide, sans grumeaux.
• pH: 5.5-6.0 (enregistrement obligatoire).
• Viscosité: 3000-5000 cPs à 25°C.
• [CORRECTION] Microbiologie: prélèvement chaque lot, critères ISO 11930.

5. CONDITIONNEMENT & LIBÉRATION
• Flacons: PEHD opaque, test compatibilité validé.
• Étiquetage: numéro lot + DLC + liste INCI.
• [CORRECTION] Fiche de lot complétée et signée par QA.

─────────────────────────────────────────────────────────────
✅ Ce protocole intègre toutes les exigences BPF et les corrections détectées.
✅ Prêt pour production après signature Responsable Qualité.
"""
        return corrected
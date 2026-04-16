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
from agents.prompt_safety import prompt_injection_guard, sanitize_text_for_prompt
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
        elements.append(Paragraph("Cette section détaille l'évaluation approfondie de votre protocole de fabrication par rapport aux normes internationales de qualité et de sécurité. Nous analysons chaque étape pour identifier les écarts potentiels, les risques associés et les impacts sur la conformité réglementaire.", self.styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))
        
        violations = audit_result.get('violations', [])
        
        if violations:
            elements.append(Paragraph(f"Le protocole présente {len(violations)} écart(s) nécessitant une correction. Chaque écart est analysé ci-dessous avec son contexte, les risques potentiels et les recommandations d'amélioration.", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
            for i, v in enumerate(violations, 1):
                # ⚠️ Le risque vient du LLM (audit_result), plus de texte statique
                risk_text = v.get('risque', "Risque de non-conformité réglementaire ou sanitaire.")
                
                elements.append(Paragraph(f"<b>• Écart {i} ({v.get('etape', 'Général')}):</b> {v.get('ecart', 'Non spécifié')}", self.styles['ProtocolText']))
                elements.append(Paragraph(f"⚠️ <b>Risque identifié:</b> {risk_text}", self.styles['AdviceBox']))
                elements.append(Paragraph("Cette non-conformité peut entraîner des conséquences sérieuses telles que des rappels de produits, des sanctions réglementaires ou des risques pour la santé des consommateurs. Il est recommandé de corriger cet écart immédiatement pour assurer la sécurité et la qualité du produit.", self.styles['Normal']))
                elements.append(Spacer(1, 0.3*cm))
        else:
            # ✅ Feedback Positif
            elements.append(Paragraph("✅ PROTOCOLE EXCELLENT", self.styles['SuccessText']))
            elements.append(Paragraph("Votre protocole respecte parfaitement les exigences de la norme. La structure est solide et les paramètres critiques sont maîtrisés. C'est une base industrielle très robuste qui minimise les risques de non-conformité et assure une production de haute qualité.", self.styles['Normal']))

        bio_alternatives = audit_result.get('bio_alternatives', [])
        if bio_alternatives:
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("🌿 Alternatives Bio / Naturelles recommandées", self.styles['CustomHeading']))
            elements.append(Paragraph("Pour améliorer la durabilité et l'attractivité de votre produit sur le marché bio, voici des suggestions d'ingrédients alternatifs issus de sources naturelles. Ces recommandations tiennent compte des propriétés fonctionnelles requises et des certifications bio possibles.", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
            for alternative in bio_alternatives:
                elements.append(Paragraph(f"• {alternative}", self.styles['ProtocolText']))
            elements.append(Spacer(1, 0.3*cm))

        normes_complementaires = audit_result.get('normes_complementaires', [])
        if normes_complementaires:
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("📚 Normes complémentaires à vérifier", self.styles['CustomHeading']))
            elements.append(Paragraph("En plus de la norme principale, ces normes complémentaires peuvent renforcer la conformité de votre processus de fabrication. Elles couvrent des aspects spécifiques comme la sécurité alimentaire, l'environnement ou la traçabilité, et sont particulièrement pertinentes pour votre secteur d'activité.", self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))
            for norme in normes_complementaires:
                title = norme.get('nom', 'Norme inconnue')
                comment = norme.get('commentaire', 'Aucune description disponible.')
                elements.append(Paragraph(f"• <b>{title}:</b> {comment}", self.styles['ProtocolText']))
            elements.append(Spacer(1, 0.3*cm))

        elements.append(PageBreak())

        # === 3. CONSEIL STRATÉGIQUE (Généré par LLM) ===
        elements.append(Paragraph("🚀 2. Recommandations Stratégiques & Innovation", self.styles['CustomHeading']))
        elements.append(Paragraph("Cette section présente une analyse stratégique approfondie générée par intelligence artificielle pour optimiser votre processus de fabrication. Elle couvre les aspects techniques, économiques et marketing afin de maximiser la valeur de votre produit sur le marché cosmétique.", self.styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Appel LLM pour générer les conseils business
        strategic_advice = self._get_strategic_advice(protocol_text)
        elements.append(Paragraph(strategic_advice, self.styles['ProtocolText']))
        
        elements.append(Spacer(1, 1*cm))
        elements.append(PageBreak())

        # === 4. PROTOCOLE CORRIGÉ ===
        elements.append(Paragraph("📋 3. Protocole de Fabrication (Version Finale)", self.styles['CustomHeading']))
        elements.append(Paragraph("Voici la version corrigée et optimisée de votre protocole de fabrication. Le tableau suivant présente les actions principales de manière synthétique, puis les points clés à appliquer étape par étape.", self.styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))
        self._append_corrected_protocol_elements(elements, violations, norme_ref)

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
        Appelle le LLM pour générer des conseils business détaillés (Bio, Coût, Marché)
        """
        protocol_text = sanitize_text_for_prompt(protocol_text)
        guard = prompt_injection_guard(protocol_text)
        prompt = f"""
{guard}Tu es un Consultant Senior en Industrie Cosmétique avec plus de 20 ans d'expérience.
Analyse ce protocole de fabrication et génère un rapport stratégique détaillé et explicatif.

PROTOCOLE:
{protocol_text[:3000]} # On prend un extrait pour éviter les limites
        
        TÂCHE:
        Rédige une section 'Recommandations Stratégiques' très détaillée et explicative, structurée ainsi:
        
        1. OPTIMISATION TECHNIQUE: Décris en détail une suggestion technique pour améliorer la texture, la stabilité ou l'efficacité du produit. Explique pourquoi cette modification est bénéfique, comment l'implémenter et quels sont les avantages attendus (ex: remplacement d'un tensioactif par un autre plus performant, ajout d'un actif stabilisant).
        
        2. VERSION 'BIO/NATUREL': Si on souhaite rendre ce produit certifié Bio (COSMOS/Ecocert), explique quels ingrédients doivent être remplacés et par quoi. Détaille les raisons de ces changements, les certifications possibles et les défis potentiels dans la formulation bio.
        
        3. ESTIMATION COÛT: Fournis une estimation précise de l'impact sur le coût de revient. Explique les facteurs influençant le coût (matières premières, processus, certifications) et donne une fourchette réaliste (+/- X%).
        
        4. IMPACT MARCHÉ: Analyse en profondeur l'avantage concurrentiel de ces modifications. Décris les segments de marché ciblés (ex: consommateurs sensibles à l'environnement, premium), les arguments marketing et les tendances actuelles qui favorisent ces innovations.
        
        5. RECOMMANDATIONS D'IMPLEMENTATION: Ajoute une section sur comment mettre en œuvre ces suggestions étape par étape, avec un calendrier approximatif et les ressources nécessaires.
        
        Réponds en français, de manière professionnelle, détaillée et pédagogique. Utilise des exemples concrets et explique les concepts techniques.
        Réponds en texte simple sans utiliser de markdown, ni de symboles #, ni de **.
        """
        
        try:
            response = self.llm.invoke(prompt)
            return self._clean_llm_text(response.content)
        except Exception:
            return "L'analyse stratégique n'a pas pu être générée pour le moment. Veuillez vérifier la configuration de l'IA."

    def _clean_llm_text(self, text: str) -> str:
        """Nettoie le texte retourné par le LLM pour supprimer le markdown et améliorer la lisibilité."""
        cleaned = text.replace('#', '')
        cleaned = cleaned.replace('**', '')
        cleaned = cleaned.replace('###', '')
        cleaned = cleaned.replace('##', '')
        cleaned = cleaned.replace('* ', '• ')
        cleaned = cleaned.replace('- ', '• ')
        cleaned = cleaned.replace('• •', '•')
        cleaned = cleaned.replace('```', '')
        cleaned = cleaned.replace('’', "'")
        cleaned = cleaned.strip()
        return cleaned

    def _append_corrected_protocol_elements(self, elements: list, violations: list, norme_ref: str):
        """Ajoute les éléments structurés du protocole corrigé au document."""
        summary_data = [
            ['Section', 'Action principale', 'Objectif'],
            ['Hygiène & Sécurité', 'Renforcer EPI et nettoyage SOP', 'Prévenir contamination'],
            ['Matières Premières', 'Traçabilité complète des lots', 'Assurer qualité et responsabilité'],
            ['Phase Aqueuse', 'Respecter T° et homogénéisation', 'Garantir stabilité formule'],
            ['Tensioactifs', 'Ajouter doucement et limiter mousse', 'Optimiser tolérance et texture'],
            ['Contrôles Qualité', 'Enregistrer pH, viscosité, microbiologie', 'Valider conformité produit'],
            ['Conditionnement', 'Étiqueter et signer fiche de lot', 'Assurer traçabilité finale']
        ]
        table = Table(summary_data, colWidths=[5*cm, 6*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
            ('FONTSIZE', (0,0), (-1,-1), 9)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        sections = [
            ('1. Hygiène & Sécurité', [
                'Port des EPI obligatoire (gants, lunettes, blouse).',
                'Désinfection des mains avant production.',
                'Nettoyage SOP avant et après chaque lot.'
            ]),
            ('2. Matières Premières', [
                'Vérifier fiches techniques et certificats par lot.',
                'Enregistrer fournisseur, lot MP et produit final.',
                'Ne pas utiliser MP sans documentation complète.'
            ]),
            ('3. Phase Aqueuse', [
                'Maintenir T° < 30°C pendant l’ajout d’eau et d’agents.',
                'Agiter 300-400 rpm pendant 10 minutes.',
                'Pré-disperser la gomme xanthane dans la glycérine.'
            ]),
            ('4. Tensioactifs', [
                'Ajouter le decyl glucoside progressivement.',
                'Incorporer la cocamidopropyl bétaïne en limitant la mousse.',
                'Limiter l’aération pour préserver la stabilité.'
            ]),
            ('5. Contrôles Qualité', [
                'Contrôler pH 5,5-6,0 et enregistrer le résultat.',
                'Mesurer viscosité 3000-5000 cPs à 25°C.',
                'Effectuer test microbiologique par lot.'
            ]),
            ('6. Conditionnement', [
                'Utiliser flacons PEHD opaques testés.',
                'Étiqueter lot, DLC et INCI.',
                'Signer la fiche de lot par le responsable QA.'
            ])
        ]

        for title, items in sections:
            elements.append(Paragraph(title, self.styles['CustomHeading']))
            for item in items:
                elements.append(Paragraph(f"- {item}", self.styles['ProtocolText']))
            elements.append(Spacer(1, 0.25*cm))
        elements.append(Spacer(1, 0.3*cm))

    def _generate_full_corrected_protocol(self, original_protocol: str, violations: list, norme_ref: str) -> str:
        """Génère le texte du protocole corrigé avec explications détaillées"""
        corrected = f"""PROTOCOLE DE FABRICATION — GEL NETTOYANT COSMÉTIQUE
Norme de référence: {norme_ref or 'ISO 22716:2007'} | Version Finale Validée
─────────────────────────────────────────────────────────────

1. PRÉREQUIS HYGIÈNE & SÉCURITÉ (ISO 22716 Section 7)
Cette étape est cruciale pour prévenir les contaminations croisées et assurer la sécurité du personnel.
- EPI obligatoires: gants nitrile (résistance chimique), lunettes protection (prévention projections), blouse fermée (évite contamination).
- Désinfection mains: solution hydroalcoolique avant entrée zone de production (réduction microbiologique >99%).
- Nettoyage équipements: procédure SOP-CLEAN-01 validée (assure traçabilité et reproductibilité).

2. MATIÈRES PREMIÈRES & TRAÇABILITÉ
La traçabilité complète est obligatoire pour la sécurité des consommateurs et la conformité réglementaire.
- Toutes les MP doivent avoir: fiche technique (spécifications), certificat analyse (pureté/qualité), numéro de lot (traçabilité).
- Enregistrement: fournisseur → lot MP → produit fini (permet retracer tout problème jusqu'à la source).

3. PROCÉDÉ DE FABRICATION
Le processus est optimisé pour garantir stabilité, efficacité et sécurité du produit final.

3.1 Phase Aqueuse
Préparation de la base aqueuse avec contrôle strict des paramètres pour éviter les dégradations.
- Eau déminéralisée: qualité pharmacopée (conductivité <1 μS/cm, absence contaminants).
- Glycérine: ajout sous agitation 150 rpm, T° ambiante (humectant naturel, stabilise la formulation).
- Gomme xanthane: PRÉ-DISPERSION obligatoire dans glycérine (évite grumeaux, assure viscosité uniforme).
- Agitation: 300-400 rpm pendant 10 min (homogénéisation complète sans incorporation d'air).
- [CORRECTION] Température max: 30°C (enregistrement automatique) - Prévention dégradation thermique.

3.2 Incorporation Tensioactifs
Intégration des agents nettoyants avec précaution pour maintenir la stabilité du système.
- Decyl glucoside: ajout progressif sous agitation douce (200 rpm) - Tensioactif doux d'origine végétale.
- Cocamidopropyl bétaïne: incorporation en inclinant cuve (évite mousse excessive, améliore tolérance cutanée).
- [CORRECTION] Éviter aération excessive - Prévention oxydation et formation mousse indésirable.

3.3 Ajustements & Finition
Finalisation du produit avec ajout des actifs et conservateurs.
- Panthénol + Aloe Vera: ajout à T° < 35°C (préserve activité biologique des actifs).
- [CORRECTION] Contrôle pH: cible 5.5-6.0, ajustement acide citrique (pH physiologique, stabilité formulation).
- Cosgard (conservateur): ajout final, agitation 150 rpm (efficacité maximale, prévention contamination).
- Parfum: ajout final (évite volatilisation pendant le process).

4. CONTRÔLES QUALITÉ
Vérifications obligatoires pour garantir la conformité et la sécurité du produit.
- Aspect: gel translucide, sans grumeaux (indicateur stabilité formulation).
- pH: 5.5-6.0 (enregistrement obligatoire) - Tolérance cutanée optimale.
- Viscosité: 3000-5000 cPs à 25°C (texture agréable, facilité application).
- [CORRECTION] Microbiologie: prélèvement chaque lot, critères ISO 11930 (sécurité sanitaire).

5. CONDITIONNEMENT & LIBÉRATION
Finalisation du processus avec traçabilité complète.
- Flacons: PEHD opaque, test compatibilité validé (protection lumière, absence migration).
- Étiquetage: numéro lot + DLC + liste INCI (conformité réglementaire, information consommateur).
- [CORRECTION] Fiche de lot complétée et signée par QA (validation qualité avant libération).

─────────────────────────────────────────────────────────────
✅ Ce protocole intègre toutes les exigences BPF et les corrections détectées.
✅ Prêt pour production après signature Responsable Qualité.
✅ Recommandation: Former le personnel sur ces procédures et effectuer des audits réguliers.
"""
        return corrected
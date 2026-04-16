# 📁 agents/report_agent.py
"""
Report Agent - Génération de rapports PDF professionnels
Prend en entrée le résultat de ISOComplianceAgent et produit un livrable industriel
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from io import BytesIO
from datetime import datetime
import os

class ReportAgent:
    """Agent spécialisé dans la génération de rapports d'audit PDF"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configure les styles personnalisés pour le rapport"""
        # Style titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=12,
            alignment=1  # Center
        ))
        
        # Style sous-titre
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=10,
            spaceBefore=12,
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=5
        ))
        
        # Style pour les violations (rouge)
        self.styles.add(ParagraphStyle(
            name='ViolationText',
            parent=self.styles['Normal'],
            textColor=colors.HexColor('#dc2626'),
            leftIndent=10
        ))
        
        # Style pour les actions (vert)
        self.styles.add(ParagraphStyle(
            name='ActionText',
            parent=self.styles['Normal'],
            textColor=colors.HexColor('#16a34a'),
            leftIndent=10
        ))
    
    def generate_pdf(self, audit_result: dict, protocol_text: str, norme_ref: str) -> BytesIO:
        """
        Génère un rapport PDF professionnel
        
        Args:
            audit_result: Résultat de l'audit (sortie de ISOComplianceAgent)
            protocol_text: Texte du protocole analysé
            norme_ref: Norme de référence utilisée
            
        Returns:
            BytesIO contenant le PDF généré
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        
        # === EN-TÊTE INSTITUTIONNEL ===
        elements.append(Paragraph("RAPPORT D'AUDIT ISO 22716", self.styles['CustomTitle']))
        elements.append(Paragraph(
            "Plateforme Nationale de Conformité Cosmétique<br/>"
            "<i>Ministère de l'Industrie et du Commerce | Direction Qualité</i>",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 0.5*cm))
        
        # === MÉTADONNÉES ===
        meta_data = [
            ['Date de génération:', datetime.now().strftime('%d/%m/%Y %H:%M')],
            ['Norme de référence:', norme_ref or 'ISO 22716:2007'],
            ['Statut:', audit_result.get('conformite_globale', 'N/A')],
            ['Score de risque:', f"{audit_result.get('score_risque', 0)}/10"]
        ]
        
        meta_table = Table(meta_data, colWidths=[5*cm, 10*cm])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 1*cm))
        
        # === SCORE DE RISQUE VISUEL ===
        score = audit_result.get('score_risque', 0)
        score_color = colors.green if score < 3 else colors.orange if score < 7 else colors.red
        score_label = "Faible" if score < 3 else "Modéré" if score < 7 else "Élevé"
        
        elements.append(Paragraph("📊 Évaluation du Risque", self.styles['CustomHeading']))
        elements.append(Paragraph(
            f"<b>Score:</b> {score}/10 &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Niveau:</b> <font color='{score_color.hexval()}'>{score_label}</font>",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 0.5*cm))
        
        # === VIOLATIONS DÉTECTÉES ===
        elements.append(Paragraph("🔴 Non-Conformités Détectées", self.styles['CustomHeading']))
        violations = audit_result.get('violations', [])
        
        if violations:
            for i, v in enumerate(violations, 1):
                etape = v.get('etape', 'Général')
                ecart = v.get('ecart', 'Non spécifié')
                ref = v.get('reference_iso', norme_ref)
                
                elements.append(Paragraph(
                    f"<b>{i}. {etape}</b><br/>{ecart}<br/>"
                    f"<i>Référence: {ref}</i>",
                    self.styles['ViolationText']
                ))
                elements.append(Spacer(1, 0.3*cm))
        else:
            elements.append(Paragraph("✅ Aucune violation détectée", self.styles['ActionText']))
        
        elements.append(Spacer(1, 0.5*cm))
        
        # === ACTIONS CORRECTIVES ===
        elements.append(Paragraph("🟢 Actions Correctives Recommandées", self.styles['CustomHeading']))
        actions = audit_result.get('actions_correctives', [])
        
        if actions:
            for i, action in enumerate(actions, 1):
                elements.append(Paragraph(f"{i}. {action}", self.styles['ActionText']))
                elements.append(Spacer(1, 0.2*cm))
        else:
            elements.append(Paragraph("Aucune action corrective requise", self.styles['Normal']))
        
        elements.append(Spacer(1, 1*cm))
        
        # === PROTOCOLE CORRIGÉ (Généré par raisonnement agentique) ===
        elements.append(Paragraph("📋 Recommandations de Mise en Conformité", self.styles['CustomHeading']))
        corrected_protocol = self._generate_corrected_protocol(violations, norme_ref)
        elements.append(Paragraph(corrected_protocol, self.styles['Normal']))
        elements.append(Spacer(1, 1*cm))
        
        # === RÉSUMÉ EXÉCUTIF (Pour la direction) ===
        elements.append(Paragraph("📝 Résumé Exécutif", self.styles['CustomHeading']))
        summary = self._generate_executive_summary(audit_result, norme_ref)
        elements.append(Paragraph(summary, self.styles['Normal']))
        
        # === PIED DE PAGE / SIGNATURE ===
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(
            "<i>Document généré automatiquement par l'Agent de Conformité Cosmétique</i><br/>"
            f"Norme de référence: {norme_ref or 'ISO 22716:2007'}<br/>"
            "Ce rapport est confidentiel et destiné à un usage professionnel.",
            self.styles['Normal']
        ))
        
        # === GÉNÉRATION FINALE ===
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def _generate_corrected_protocol(self, violations: list, norme_ref: str) -> str:
        """
        Génère un texte de protocole corrigé basé sur les violations détectées
        C'est ici que l'Agent "raisonne" pour proposer des corrections
        """
        if not violations:
            return "✅ Le protocole soumis est conforme aux exigences de la norme sélectionnée. Aucune modification requise."
        
        corrected = "RECOMMANDATIONS POUR MISE EN CONFORMITÉ :\n\n"
        
        for i, v in enumerate(violations, 1):
            text = f"{v.get('etape', 'Général')}: {v.get('ecart', '')}".lower()
            
            # Raisonnement basé sur le type de violation
            if 'epi' in text or 'hygiène' in text or 'gants' in text or 'lunettes' in text:
                corrected += f"{i}. HYGIÈNE & EPI (ISO 22716 Section 7.2):\n"
                corrected += "   • Ajouter: port obligatoire de gants en nitrile, lunettes de protection, blouse fermée\n"
                corrected += "   • Procédure: désinfection des mains avec solution hydroalcoolique avant entrée en zone\n"
                corrected += "   • Enregistrement: feuille de présence EPI signée par opérateur\n\n"
                
            elif 'température' in text or 'chauffe' in text or '75' in text or 'degré' in text:
                corrected += f"{i}. PARAMÈTRES DE PRODUCTION (ISO 22716 Section 8.2):\n"
                corrected += "   • Spécifier température max: 75°C avec tolérance ±2°C\n"
                corrected += "   • Enregistrer les températures dans la fiche de lot avec horodatage automatique\n"
                corrected += "   • Mettre en place un système d'alarme en cas de dépassement\n"
                corrected += "   • Validation: signature responsable production après chaque batch\n\n"
                
            elif 'documentation' in text or 'traçabilité' in text or 'fiche' in text or 'lot' in text:
                corrected += f"{i}. DOCUMENTATION & TRAÇABILITÉ (ISO 22716 Section 12):\n"
                corrected += "   • Créer une fiche de lot standardisée avec: numéro batch, dates, signatures opérateur/QA\n"
                corrected += "   • Assurer traçabilité complète: fournisseur → lot MP → produit fini → distribution\n"
                corrected += "   • Archiver les enregistrements pendant 5 ans minimum (conformité réglementaire)\n"
                corrected += "   • Audit interne: vérification trimestrielle de la complétude des dossiers\n\n"
                
            elif 'microbiolog' in text or 'challenge' in text or 'cosgard' in text or 'conservat' in text:
                corrected += f"{i}. CONTRÔLE MICROBIOLOGIQUE (ISO 22716 Section 9.3 + ISO 11930):\n"
                corrected += "   • Définir critères d'acceptation: réduction ≥ 3 log à J+7 pour bactéries\n"
                corrected += "   • Valider l'efficacité du conservateur dans la matrice finale (challenge test)\n"
                corrected += "   • Effectuer des tests de stabilité microbiologique sur 3 lots consécutifs\n"
                corrected += "   • Surveillance: contrôle mensuel des produits finis en stockage\n\n"
                
            elif 'viscosité' in text or 'rhéologie' in text or 'sel' in text or 'épais' in text:
                corrected += f"{i}. CONTRÔLE RHÉOLOGIQUE:\n"
                corrected += "   • Établir une courbe de viscosité en fonction de la concentration en sel\n"
                corrected += "   • Définir plage d'acceptation: 3000-5000 cPs à 25°C (Brookfield, spindle RV6)\n"
                corrected += "   • Contrôler la viscosité sur chaque lot de production avant libération\n"
                corrected += "   • Documentation: enregistrement des paramètres d'agitation et temps de mélange\n\n"
                
            elif 'ph' in text or 'acide' in text or 'bas' in text:
                corrected += f"{i}. CONTRÔLE DU pH:\n"
                corrected += "   • Spécifier plage cible: 5.5-6.0 avec ajustement par acide citrique\n"
                corrected += "   • Étalonnage quotidien du pH-mètre avec tampons certifiés\n"
                corrected += "   • Enregistrement: valeur pH mesurée + opérateur + horodatage\n\n"
        
        corrected += "🔄 Après application de ces corrections, relancer l'audit pour validation finale."
        return corrected
    
    def _generate_executive_summary(self, audit_result: dict, norme_ref: str) -> str:
        """
        Génère un résumé exécutif pour la direction
        L'Agent synthétise les résultats pour prise de décision
        """
        status = audit_result.get('conformite_globale', 'N/A')
        score = audit_result.get('score_risque', 0)
        violations_count = len(audit_result.get('violations', []))
        
        if status == 'CONFORME':
            return (
                f"Le protocole a été évalué selon la norme {norme_ref or 'ISO 22716:2007'}. "
                f"Aucune non-conformité critique n'a été détectée. "
                f"Le score de risque de {score}/10 indique un niveau de maîtrise satisfaisant. "
                f"✅ Le protocole peut être validé pour production après approbation du Responsable Qualité."
            )
        elif score >= 7:
            return (
                f"Le protocole présente {violations_count} non-conformité(s) selon la norme {norme_ref or 'ISO 22716:2007'}. "
                f"Le score de risque élevé ({score}/10) nécessite une revue approfondie. "
                f"⚠️ Les actions correctives listées doivent être implémentées avant toute validation. "
                f"Une nouvelle soumission est recommandée après corrections et re-test."
            )
        else:
            return (
                f"Le protocole présente {violations_count} point(s) d'amélioration selon la norme {norme_ref or 'ISO 22716:2007'}. "
                f"Le score de risque modéré ({score}/10) indique une conformité partielle. "
                f"📋 Les actions correctives proposées permettront d'atteindre la conformité totale. "
                f"Validation possible sous réserve d'application des recommandations et contrôle de suivi."
            )
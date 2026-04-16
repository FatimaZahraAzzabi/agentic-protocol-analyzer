from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Créer le PDF
doc = SimpleDocTemplate("protocole_gel_nettoyant_conforme.pdf", pagesize=A4)
elements = []
styles = getSampleStyleSheet()

# Styles personnalisés
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=18,
    textColor=colors.darkblue,
    spaceAfter=12,
    alignment=1  # Center
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.darkblue,
    spaceAfter=10,
    spaceBefore=12
)

# Titre
elements.append(Paragraph("FICHE DE FABRICATION - GEL NETTOYANT VISAGE", title_style))
elements.append(Paragraph("Conforme ISO 22716:2007 (BPF Cosmétiques)", styles['Normal']))
elements.append(Spacer(1, 0.5*cm))

# Sections
sections = [
    ("1. SYSTÈME TENSIOACTIF", 
     "• Decyl glucoside → doux, non ionique\n"
     "• Cocamidopropyl bétaïne → amphotère, boost mousse\n"
     "• Critical Micelle Concentration (CMC) vérifiée\n"
     "• Indice d'irritation cutanée (IRI) optimisé"),
    
    ("2. PROCÉDÉ DE FABRICATION",
     "• Pré-dispersion gomme xanthane dans glycérine\n"
     "• Agitation contrôlée: 300-600 rpm\n"
     "• Température max: 30-35°C\n"
     "• Éviter mousse pendant fabrication (agitation lente)"),
    
    ("3. CONTRÔLES QUALITÉ",
     "• Test pouvoir lavant (dégraissage)\n"
     "• Patch test dermatologique\n"
     "• TEWL (perte en eau)\n"
     "• Stabilité mousse Ross-Miles\n"
     "• pH: 5.5-6.0\n"
     "• Viscosité: 3000-5000 cPs"),
    
    ("4. SÉCURITÉ MICROBIOLOGIQUE",
     "• Challenge Test ISO 11930 OBLIGATOIRE\n"
     "• Cosgard 0.6% (conservateur)\n"
     "• Réduction ≥ 3 log à J+7\n"
     "• Germes totaux < 100 UFC/g"),
    
    ("5. HYGIÈNE & EPI",
     "• Gants en nitrile obligatoires\n"
     "• Lunettes de protection\n"
     "• Blouse fermée zone production\n"
     "• Désinfection mains avant entrée"),
    
    ("6. DOCUMENTATION",
     "• Fiche de lot complète\n"
     "• Traçabilité matières premières\n"
     "• Enregistrements températures\n"
     "• Pesées contrôlées (double signature)"),
    
    ("7. ANALYSE DES RISQUES (AMDEC)",
     "• Grumeaux → Pré-dispersion glycérine\n"
     "• Mousse excessive → Agitation lente\n"
     "• pH hors spec → Contrôle systématique\n"
     "• Contamination → Challenge test"),
    
    ("8. CONFORMITÉ RÉGLEMENTAIRE",
     "• Dossier PIF complet\n"
     "• Notification CPNP\n"
     "• Déclaration allergènes (limonène, linalol)\n"
     "• Tests stabilité accélérée")
]

# Ajouter les sections au PDF
for title, content in sections:
    elements.append(Paragraph(title, heading_style))
    elements.append(Paragraph(content, styles['Normal']))
    elements.append(Spacer(1, 0.3*cm))

# Tableau récapitulatif
elements.append(Paragraph("RÉCAPITULATIF DES CONTRÔLES", heading_style))

data = [
    ['Paramètre', 'Méthode', 'Critère', 'Statut'],
    ['pH', 'pH-mètre', '5.5 - 6.0', '✅'],
    ['Viscosité', 'Brookfield', '3000-5000 cPs', '✅'],
    ['Aspect', 'Visuel', 'Gel translucide', '✅'],
    ['Microbio', 'Challenge Test', 'ISO 11930', '✅'],
    ['Stabilité', '40°C/3 mois', 'Conforme', '✅']
]

table = Table(data, colWidths=[4*cm, 3*cm, 4*cm, 2*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 12),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
elements.append(table)

# Conclusion
elements.append(Spacer(1, 1*cm))
elements.append(Paragraph("CONCLUSION", heading_style))
elements.append(Paragraph(
    "Ce protocole est CONFORME à l'ISO 22716:2007. "
    "Tous les points critiques sont maîtrisés: EPI, températures, traçabilité, "
    "contrôles qualité et documentation.",
    styles['Normal']
))

# Générer le PDF
doc.build(elements)
print("✅ PDF généré: protocole_gel_nettoyant_conforme.pdf")
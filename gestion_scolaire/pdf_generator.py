"""
Générateur de bulletins PDF - Version améliorée
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime


def generate_bulletin_pdf(pdf_path, student_data, grades_part1, grades_part2, summary_data):
    """
    Génère un bulletin de notes au format PDF professionnel.
    
    Args:
        pdf_path: Chemin où sauvegarder le PDF
        student_data: Dict contenant les infos de l'école et de l'élève
            - name: Nom complet de l'élève
            - class: Nom de la classe
            - period: Période (1ère Période, 2e Période, etc.)
            - school_name: Nom de l'école
        grades_part1: Liste des notes pour les matières principales
            Chaque élément: {subject, moy_cl, n_compo, coef, mg, moy_coef, appreciation}
        grades_part2: Liste des notes pour les matières secondaires
        summary_data: Dict contenant les totaux et moyennes
            - total_points: Total des points coefficientés
            - total_coef: Total des coefficients
            - general_average: Moyenne générale
            - appreciation: Appréciation globale
    """
    doc = SimpleDocTemplate(
        pdf_path, 
        pagesize=A4,
        rightMargin=15*mm, 
        leftMargin=15*mm,
        topMargin=15*mm, 
        bottomMargin=15*mm
    )
    
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=colors.black
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=4
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading3'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=6,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # ========== EN-TÊTE ==========
    school_name = student_data.get('school_name', 'Lycée Michel ALLAIRE')
    header_data = [
        [Paragraph(f"<b>{school_name}</b>", header_style)],
        [Paragraph("BP: 580 - Ségou, Mali", header_style)],
        [Paragraph("Tél: 21-32-11-20 / 79 07 03 60", header_style)]
    ]
    header_table = Table(header_data, colWidths=[180*mm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # Ligne de séparation
    line_table = Table([['']]) 
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 2, colors.darkblue),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 10))
    
    # ========== TITRE DU BULLETIN ==========
    period = student_data.get('period', '1ère Période')
    story.append(Paragraph(f"<b>BULLETIN DE NOTES - {period}</b>", title_style))
    story.append(Spacer(1, 8))
    
    # ========== INFORMATIONS ÉLÈVE ==========
    student_info_data = [
        ['Élève:', student_data.get('name', 'N/A'), 'Classe:', student_data.get('class', 'N/A')],
        ['Année scolaire:', '2024-2025', 'Date:', datetime.now().strftime('%d/%m/%Y')]
    ]
    student_table = Table(student_info_data, colWidths=[25*mm, 65*mm, 25*mm, 65*mm])
    student_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 12))
    
    # ========== FONCTION POUR CRÉER UN TABLEAU DE NOTES ==========
    def create_grades_table(grades_list, title):
        """Crée un tableau de notes formaté"""
        section_elements = []
        section_elements.append(Paragraph(f"<b>{title}</b>", section_style))
        section_elements.append(Spacer(1, 4))
        
        # En-têtes
        headers = ['MATIÈRE', 'MOY.CL', 'N.COMPO', 'M.G.', 'COEF', 'MOY×COEF', 'APPRÉCIATION']
        data = [headers]
        
        total_mg = 0
        total_coef = 0
        total_weighted = 0
        
        for grade in grades_list:
            moy_cl = grade.get('moy_cl', '-')
            n_compo = grade.get('n_compo', '-')
            mg = grade.get('mg', '-')
            coef = grade.get('coef', '-')
            moy_coef = grade.get('moy_coef', '-')
            
            # Formater les nombres
            if isinstance(moy_cl, (int, float)):
                moy_cl_str = f"{moy_cl:.2f}"
                total_mg += moy_cl
            else:
                moy_cl_str = str(moy_cl)
            
            if isinstance(n_compo, (int, float)):
                n_compo_str = f"{n_compo:.2f}"
            else:
                n_compo_str = str(n_compo)
            
            if isinstance(mg, (int, float)):
                mg_str = f"{mg:.2f}"
            else:
                mg_str = str(mg)
            
            if isinstance(coef, (int, float)):
                coef_str = str(int(coef))
                total_coef += coef
            else:
                coef_str = str(coef)
            
            if isinstance(moy_coef, (int, float)):
                moy_coef_str = f"{moy_coef:.2f}"
                total_weighted += moy_coef
            else:
                moy_coef_str = str(moy_coef)
            
            row = [
                grade.get('subject', 'N/A'),
                moy_cl_str,
                n_compo_str,
                mg_str,
                coef_str,
                moy_coef_str,
                grade.get('appreciation', '-')
            ]
            data.append(row)
        
        # Ligne de total
        if total_coef > 0:
            section_avg = total_weighted / total_coef
            data.append(['TOTAL/MOYENNE', '', '', f"{section_avg:.2f}", str(int(total_coef)), f"{total_weighted:.2f}", ''])
        
        # Créer le tableau
        table = Table(data, colWidths=[35*mm, 18*mm, 18*mm, 15*mm, 12*mm, 22*mm, 60*mm])
        table.setStyle(TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Corps
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 1), (-2, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (-1, 1), (-1, -1), 'LEFT'),
            
            # Alternance de couleurs
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            
            # Ligne de total
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.85, 0.85, 0.85)),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        section_elements.append(table)
        return section_elements
    
    # ========== TABLEAUX DES NOTES ==========
    if grades_part1:
        for elem in create_grades_table(grades_part1, "MATIÈRES PRINCIPALES"):
            story.append(elem)
        story.append(Spacer(1, 10))
    
    if grades_part2:
        for elem in create_grades_table(grades_part2, "MATIÈRES SECONDAIRES"):
            story.append(elem)
        story.append(Spacer(1, 10))
    
    # ========== RÉSUMÉ GÉNÉRAL ==========
    story.append(Paragraph("<b>RÉSUMÉ GÉNÉRAL</b>", section_style))
    story.append(Spacer(1, 4))
    
    summary_table_data = [
        ['Total des Points', f"{summary_data.get('total_points', 0):.2f}"],
        ['Total des Coefficients', str(summary_data.get('total_coef', 0))],
        ['Moyenne Générale', f"{summary_data.get('general_average', 0):.2f} / 20"],
        ['Appréciation', summary_data.get('appreciation', '-')],
        ['Rang', summary_data.get('rank', '-')],
    ]
    
    summary_table = Table(summary_table_data, colWidths=[50*mm, 50*mm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        # Mise en évidence de la moyenne générale
        ('BACKGROUND', (0, 2), (-1, 2), colors.Color(0.9, 0.95, 1)),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))
    
    # ========== SIGNATURES ==========
    story.append(Paragraph("<b>SIGNATURES</b>", section_style))
    story.append(Spacer(1, 10))
    
    signature_data = [
        ['Le Professeur Principal', 'Le Parent/Tuteur', 'Le Proviseur'],
        ['', '', ''],
        ['', '', ''],
        ['', '', ''],
        ['_____________________', '_____________________', '_____________________']
    ]
    
    signature_table = Table(signature_data, colWidths=[60*mm, 60*mm, 60*mm])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(signature_table)
    story.append(Spacer(1, 15))
    
    # ========== PIED DE PAGE ==========
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - {school_name}",
        footer_style
    ))
    
    # Construire le PDF
    doc.build(story)
    
    return pdf_path


def generate_class_report(pdf_path, class_data, students_data, period):
    """
    Génère un rapport de classe complet.
    
    Args:
        pdf_path: Chemin du fichier PDF
        class_data: Informations sur la classe
        students_data: Liste des données des élèves avec leurs moyennes
        period: Période concernée
    """
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.darkblue
    )
    
    story = []
    
    # Titre
    story.append(Paragraph(f"<b>RAPPORT DE CLASSE - {period}</b>", title_style))
    story.append(Paragraph(f"Classe: {class_data.get('name', 'N/A')}", styles['Heading2']))
    story.append(Spacer(1, 15))
    
    # Tableau des résultats
    headers = ['Rang', 'Nom de l\'élève', 'Moyenne', 'Appréciation']
    data = [headers]
    
    # Trier par moyenne décroissante
    sorted_students = sorted(students_data, key=lambda x: x.get('average', 0), reverse=True)
    
    for rank, student in enumerate(sorted_students, 1):
        data.append([
            str(rank),
            student.get('name', 'N/A'),
            f"{student.get('average', 0):.2f}",
            student.get('appreciation', '-')
        ])
    
    table = Table(data, colWidths=[15*mm, 80*mm, 30*mm, 55*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 15))
    
    # Statistiques
    if sorted_students:
        averages = [s.get('average', 0) for s in sorted_students]
        class_avg = sum(averages) / len(averages)
        highest = max(averages)
        lowest = min(averages)
        
        stats_data = [
            ['Statistiques de la classe'],
            [f"Moyenne de classe: {class_avg:.2f}"],
            [f"Meilleure moyenne: {highest:.2f}"],
            [f"Plus basse moyenne: {lowest:.2f}"],
            [f"Nombre d'élèves: {len(sorted_students)}"]
        ]
        
        stats_table = Table(stats_data, colWidths=[100*mm])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BOX', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(stats_table)
    
    doc.build(story)
    return pdf_path

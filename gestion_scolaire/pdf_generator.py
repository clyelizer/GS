import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime

def generate_bulletin_pdf(pdf_path, student_data, grades_part1, grades_part2, summary_data):
    """
    Generate a PDF report card (bulletin) with the provided data.
    
    Args:
        pdf_path: Path where the PDF should be saved
        student_data: Dict containing school and student information
        grades_part1: List of grades for subjects part 1
        grades_part2: List of grades for subjects part 2
        summary_data: Dict containing calculated averages and statistics
    """
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                          rightMargin=20*mm, leftMargin=20*mm,
                          topMargin=20*mm, bottomMargin=20*mm)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.black
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=8
    )
    
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=6,
        textColor=colors.black
    )
    
    # Story (content elements)
    story = []
    
    # Header information
    header_text = f"""
    <b>{student_data.get('school_name', 'Lycée Michel ALLAIRE')}</b><br/>
    BP: {student_data.get('school_bp', '580')}<br/>
    Tél: {student_data.get('school_tel', '21-32-11-20')} - {student_data.get('school_tel_alt', '79 07 03 60')}<br/>
    Email: {student_data.get('school_email', 'michelallaire2007@yahoo.fr')}
    """
    story.append(Paragraph(header_text, header_style))
    story.append(Spacer(1, 10))
    
    # Bulletin title
    title_text = f"<b>BULLETIN DE NOTES</b><br/>Période: {student_data.get('academic_period', '')}"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 15))
    
    # Student information
    student_info = f"""
    <b>Nom:</b> {student_data.get('student_name', '')}<br/>
    <b>Classe:</b> {student_data.get('class_name', '')}<br/>
    <b>Période:</b> {student_data.get('academic_period', '')}
    """
    story.append(Paragraph(student_info, bold_style))
    story.append(Spacer(1, 15))
    
    # Grades table for part 1
    if grades_part1:
        story.append(Paragraph("<b>MATIÈRES PRINCIPALES</b>", styles['Heading3']))
        story.append(Spacer(1, 8))
        
        # Table headers
        data_part1 = [['MATIÈRE', 'MOY. CL.', 'N. COMPO.', 'COEF.', 'APPRECIATION']]
        
        for grade in grades_part1:
            data_part1.append([
                grade.get('subject', 'N/A'),
                f"{grade.get('moy_cl', 0):.2f}" if grade.get('moy_cl') else '0.00',
                f"{grade.get('n_compo', 0):.2f}" if grade.get('n_compo') else '0.00',
                str(grade.get('coef', 0)),
                grade.get('appreciation', 'N/A')
            ])
        
        # Add part 1 average
        data_part1.append(['', '', '', '', ''])
        data_part1.append(['MOYENNE P1', '', '', '', summary_data.get('moy_p1_overall', '0.00 /20')])
        
        # Create table
        table_part1 = Table(data_part1, colWidths=[40*mm, 25*mm, 25*mm, 15*mm, 55*mm])
        table_part1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('FONTNAME', (0, -2), (-1, -2), 'Helvetica-Bold'),
            ('ALIGN', (0, -2), (0, -1), 'LEFT'),
            ('FONTNAME', (1, -2), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('GRID', (0, -2), (-1, -1), 2, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table_part1)
        story.append(Spacer(1, 15))
    
    # Grades table for part 2
    if grades_part2:
        story.append(Paragraph("<b>MATIÈRES SECONDAIRES</b>", styles['Heading3']))
        story.append(Spacer(1, 8))
        
        # Table headers
        data_part2 = [['MATIÈRE', 'MOY. CL.', 'N. COMPO.', 'COEF.', 'APPRECIATION']]
        
        for grade in grades_part2:
            data_part2.append([
                grade.get('subject', 'N/A'),
                f"{grade.get('moy_cl', 0):.2f}" if grade.get('moy_cl') else '0.00',
                f"{grade.get('n_compo', 0):.2f}" if grade.get('n_compo') else '0.00',
                str(grade.get('coef', 0)),
                grade.get('appreciation', 'N/A')
            ])
        
        # Add part 2 average
        data_part2.append(['', '', '', '', ''])
        data_part2.append(['MOYENNE P2', '', '', '', summary_data.get('moy_p2_overall', '0.00 /20')])
        
        # Create table
        table_part2 = Table(data_part2, colWidths=[40*mm, 25*mm, 25*mm, 15*mm, 55*mm])
        table_part2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('FONTNAME', (0, -2), (-1, -2), 'Helvetica-Bold'),
            ('ALIGN', (0, -2), (0, -1), 'LEFT'),
            ('FONTNAME', (1, -2), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('GRID', (0, -2), (-1, -1), 2, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table_part2)
        story.append(Spacer(1, 15))
    
    # Summary section
    story.append(Paragraph("<b>RÉSUMÉ</b>", styles['Heading3']))
    story.append(Spacer(1, 8))
    
    summary_info = f"""
    <b>Moyenne annuelle:</b> {summary_data.get('moy_annuelle', '0.00 /20')}<br/>
    <b>Appréciation globale:</b> {summary_data.get('appr_globale', 'N/A')}<br/>
    <b>Rang:</b> {summary_data.get('rank', 'N/A')} 1er: {summary_data.get('rank_1_moy', 'N/A')}<br/>
    <b>Date:</b> {summary_data.get('date_generated', datetime.now().strftime('%d/%m/%Y'))}
    """
    story.append(Paragraph(summary_info, bold_style))
    story.append(Spacer(1, 20))
    
    # Signature section
    signature_text = f"""
    Fait à Ségou, le {summary_data.get('date_generated', datetime.now().strftime('%d/%m/%Y'))}<br/><br/>
    Le Proviseur<br/><br/><br/><br/>
    ________________________
    """
    story.append(Paragraph(signature_text, styles['Normal']))
    
    # Build the PDF
    doc.build(story)
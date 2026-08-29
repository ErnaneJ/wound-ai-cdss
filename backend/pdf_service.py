import os
from datetime import datetime
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as PDFImage
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import Patient, Chat, Image, ChatMessage
import re
from PIL import Image as PILImage

METRICAS_MODELO = {
    'BG': {'precision': 0.9600, 'recall': 0.9600, 'f1-score': 0.9600},
    'D': {'precision': 0.8500, 'recall': 0.7391, 'f1-score': 0.7909},
    'N': {'precision': 0.8333, 'recall': 1.0, 'f1-score': 0.9091},
    'P': {'precision': 0.6154, 'recall': 0.2353, 'f1-score': 0.3404},
    'S': {'precision': 0.6000, 'recall': 0.6429, 'f1-score': 0.6207},
    'V': {'precision': 0.7037, 'recall': 0.9194, 'f1-score': 0.7973}
}

traducoes = {
    'BG': 'Background',
    'D': 'Diabetic Ulcer', 
    'N': 'Normal Skin',
    'P': 'Pressure Ulcer',
    'S': 'Surgical Wound',
    'V': 'Venous Ulcer'
}

def get_gemini_client():
    """Returns the Gemini client"""
    try:
        from google import genai
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError("google-genai library not installed")

def extract_probabilities_from_analysis(db: Session, image_hash: str, chat_id: int) -> dict:
    """
    Extracts the actual probabilities from the Gemini analysis message
    """
    try:
        message = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat_id,
            ChatMessage.message_type == "analysis",
            ChatMessage.content.like(f'%{image_hash}%')
        ).order_by(ChatMessage.created_at.desc()).first()
        
        if not message:
            return {}
        
        client = get_gemini_client()
        
        prompt = f"""
        Analyze the following medical analysis text and extract ONLY the classification probabilities in EXACT format: {{'CLASS': 'X.XX%', 'CLASS': 'X.XX%', ...}}
        
        TEXT TO ANALYZE:
        {message.content}
        
        Rules:
        1. Extract only the probabilities in Python dictionary format.
        2. Use the classes: BG, D, N, P, S, V.
        3. Keep the exact values ​​with two decimal places and percentage symbol.
        4. If no probabilities are found, return {{}}.
        5. Do not add any explanatory text, only the dictionary.
        6. Only those that are in the text; you don't need to return all classes if they are not present.
        
        Example 1 of expected output:
        {{'BG': '0.01%', 'D': '84.28%', 'N': '0.00%', 'P': '10.50%', 'S': '1.00%', 'V': '4.21%'}}
        
        Example 2 of expected output:
        {{'D': '84.28%', 'P': '10.50%', 'S': '1.00%'}}
        """
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        
        import ast
        try:
            probabilities = ast.literal_eval(response.text.replace('`', '').replace('json', '').strip())
            return probabilities
        except:
            return {}
            
    except Exception as e:
        print(f"❌ Error extracting probabilities: {e}")
        return {}

def get_formal_analysis(image_path: str, classification_data: dict) -> str:
    """
    Uses Gemini to generate a formal analysis for the PDF
    """
    try:
        client = get_gemini_client()
        
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        classe_predita = classification_data.get('classe_predita', 'Desconhecida')
        classe_traduzida = classification_data.get('classe_traduzida', 'Desconhecida')
        confianca = classification_data.get('confianca_predita_percentual', 'N/A')
        probabilidades = classification_data.get('probabilidades_completas', {})
        
        prompt = f"""
        You are a medical expert creating a formal clinical report for documentation.

        CLASSIFICATION DATA:
        - Predicted Class: {classe_predita} ({classe_traduzida})
        - Model Confidence: {confianca}
        - Probabilities: {probabilidades}

        Create a formal and technical description for inclusion in a PDF medical report. The description should:

        1. Be concise (maximum 150 words)
        2. Use formal medical language
        3. Describe relevant visual characteristics
        4. Mention the level of confidence in the classification
        5. Include considerations about differential diagnoses based on probabilities
        6. Maintain a professional and objective tone

        Format the response in short paragraphs, without markers. Do not use markdown, only plain text.
        """
        
        from google.genai import types
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_data,
                    mime_type='image/jpeg'
                )
            ]
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ Error generating formal analysis: {e}")
        return "Formal analysis not available at this time."

def create_metrics_table() -> Table:
    """Creates a table with the model's metrics"""
    data = [
        ['Class', 'Description', 'Precision', 'Recall', 'F1-Score']
    ]
    
    for classe, metrics in METRICAS_MODELO.items():
        data.append([
            classe,
            traducoes.get(classe, classe),
            f"{metrics['precision']:.3f}",
            f"{metrics['recall']:.3f}",
            f"{metrics['f1-score']:.3f}"
        ])
    
    table = Table(data, colWidths=[2*cm, 4*cm, 2*cm, 2*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5A88')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    return table

def create_image_metrics_table(probabilities: dict) -> Table:
    """Creates a table with image-specific metrics using the actual probabilities"""
    sorted_probs = sorted(probabilities.items(), 
                         key=lambda x: float(x[1].rstrip('%')), 
                         reverse=True)
    
    data = [['Classification', 'Probability', 'Description']]
    
    for classe, prob in sorted_probs:
        try:
            prob_value = float(prob.rstrip('%'))
            prob_formatted = f"{prob_value:.2f}%"
        except:
            prob_formatted = prob
        
        data.append([
            classe,
            prob_formatted,
            traducoes.get(classe, classe)
        ])
    
    table = Table(data, colWidths=[2.5*cm, 2.5*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E5A88')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F8FF')]),
    ]))
    
    return table

def resize_image_for_pdf(image_path: str, max_width: int = 200) -> str:
    """Resizes an image for the PDF and returns the temporary path"""
    try:
        with PILImage.open(image_path) as img:
            width_percent = max_width / float(img.size[0])
            new_height = int(float(img.size[1]) * float(width_percent))
            
            img_resized = img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
            
            temp_path = f"/tmp/{os.path.basename(image_path)}"
            img_resized.save(temp_path, "JPEG", quality=85)
            
            return temp_path
    except Exception as e:
        print(f"❌ Error resizing image: {e}")
        return image_path

def create_pdf_report(db: Session, paciente_id: int, output_path: str) -> str:
    """
    Creates a professional PDF report for the patient
    """
    try:
        patient = db.query(Patient).filter(Patient.id == paciente_id).first()
        if not patient:
            raise ValueError("Patient not found")

        chat = db.query(Chat).filter(Chat.patient_id == paciente_id).first()
        if not chat:
            raise ValueError("Chat not found")

        images = db.query(Image).filter(Image.chat_id == chat.id).all()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            title=f"Preliminary Report - {patient.name}",
            author="AI-CDSS Wound Analysis System",
            subject=f"Lesion analysis for patient {patient.name}",
            creator="AI-Assisted Analysis System",
            keywords=f"Lesion, pressure, diabetes,{patient.name}, preliminary-report"
        )
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2E5A88'),
            spaceAfter=12,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2E5A88'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=10,
            textColor=colors.HexColor('#455A64'),
            spaceAfter=8,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=8,
            leading=13
        )
        
        small_style = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            spaceAfter=6,
            leading=11
        )
        
        story = []
        
        header_text = """
        <b>PRELIMINARY MEDICAL REPORT - LESION ANALYSIS</b><br/>
        <i>AI-CDSS - Artificial Intelligence Clinical Decision Support System</i>
        """
        story.append(Paragraph(header_text, title_style))
        story.append(Spacer(1, 10))
        
        data_emissao = f"""
        <b>Issue date:</b> {datetime.now().strftime('%m/%d/%Y at %H:%M')}<br/><br/>
        """
        story.append(Paragraph(data_emissao, small_style))
        
        story.append(Paragraph("1. PATIENT INFORMATION", heading_style))
        
        patient_info = f"""
        <b>Name:</b> {patient.name}<br/>
        <b>Age:</b> {patient.age} years old<br/>
        <b>Sex:</b> {patient.sex}<br/>
        <b>Diabetes Type:</b> {patient.diabetes_type}<br/>
        <b>Document:</b> {patient.document or 'Not informed'}<br/>
        <b>Medical History:</b> {patient.medical_history or 'Not informed'}<br/>
        <b>Medications:</b> {patient.medications or 'Not informed'}<br/>
        <b>Allergies:</b> {patient.allergies or 'Not informed'}
        """
        story.append(Paragraph(patient_info, normal_style))
        
        if images:
            story.append(Paragraph("2. LESION ANALYSIS", heading_style))
            
            for i, img in enumerate(images, 1):
                story.append(Paragraph(f"<b>2.{i} Lesion {i}:</b>", subheading_style))
                
                try:
                    if os.path.exists(img.image_path):
                        temp_image_path = resize_image_for_pdf(img.image_path, 400)
                        pdf_image = PDFImage(temp_image_path, width=8*cm, height=6*cm)
                        story.append(pdf_image)
                        story.append(Spacer(1, 10))
                except Exception as e:
                    print(f"❌ Error adding image: {e}")
                
                img_basic_info = f"""
                <b>Classification:</b> {img.classification} - {img.description}<br/>
                <b>File:</b> {img.filename}<br/>
                <b>Probability Distribution:</b>
                """
                story.append(Paragraph(img_basic_info, normal_style))
                
                if img.classification != "Pending" and img.classification != "ERROR":
                    image_hash = os.path.basename(img.image_path).split('.')[0]
                    
                    probabilities = extract_probabilities_from_analysis(db, image_hash, chat.id)
                    
                    if not probabilities:
                        if '(' in img.description and ')' in img.description:
                            confianca = img.description.split('(')[-1].rstrip(')')
                            probabilities = {
                                img.classification: confianca,
                                **{classe: '0.00%' for classe in ['BG', 'D', 'N', 'P', 'S', 'V'] 
                                   if classe != img.classification}
                            }
                        else:
                            probabilities = {img.classification: img.description.split('(')[1].split(')')[0]}
                    
                    metrics_table = create_image_metrics_table(probabilities)
                    story.append(metrics_table)
                    story.append(Spacer(1, 10))
                
                if img.classification != "Pending" and img.classification != "ERROR":
                    story.append(Paragraph("<b>Formal Analysis:</b>", normal_style))
                    
                    classification_data = {
                        'classe_predita': img.classification,
                        'classe_traduzida': img.description.split('(')[0].strip() if '(' in img.description else img.description,
                        'confianca_predita_percentual': img.description.split('(')[-1].rstrip(')') if '(' in img.description else 'N/A',
                        'probabilidades_completas': {img.classification: '100%'}
                    }
                    
                    formal_analysis = get_formal_analysis(img.image_path, classification_data)
                    story.append(Paragraph(formal_analysis, small_style))
        else:
            story.append(Paragraph("No analyzed images available.", normal_style))
        
        story.append(Paragraph("3. SYSTEM INFORMATION", heading_style))
        
        story.append(Paragraph("<b>Performance of the Classification Model:</b>", subheading_style))
        
        metrics_explanation = """
        <b>Glossary of Metrics:</b><br/>
        • <b>Precision</b>: Accuracy in positive predictions (precision)<br/>
        • <b>Recall</b>: Ability to find all positive cases (sensitivity)<br/>
        • <b>F1-Score</b>: Harmonic mean between Precision and Recall<br/>
        • <b>Values</b>: 0.000 (worst) to 1.000 (best)
        """
        story.append(Paragraph(metrics_explanation, small_style))
        story.append(Spacer(1, 10))
        
        metrics_table = create_metrics_table()
        story.append(metrics_table)
        story.append(Spacer(1, 15))
        
        model_info = """
        <b>Classification System:</b> VGG16 Fine-Tuned Convolutional Neural Network<br/>
        <b>Purpose:</b> Auxiliary clinical decision support for initial lesion screening<br/>
        <b>Training:</b> Dataset specialized in skin lesions<br/>
        <b>Processing:</b> Automatic visual feature analysis
        """
        story.append(Paragraph(model_info, normal_style))
        
        story.append(Paragraph("4. OBSERVATIONS AND RECOMMENDATIONS", heading_style))
        
        observacoes = """
        • This document constitutes a <b>PRELIMINARY REPORT</b> generated by an Artificial Intelligence system;<br/>
        • <b>Does not replace</b> the evaluation of a qualified healthcare professional;<br/>
        • For pressure ulcers (Class P), the system has <b>limited sensitivity</b> (recall: 23.53%).<br/>
        """
        story.append(Paragraph(observacoes, normal_style))
        
        story.append(Spacer(1, 30))
        footer_text = f"""
        <i>Document generated automatically - Wound Analysis System<br/>
        Patient: {patient.name} | ID: {patient.id} | Generated on: {datetime.now().strftime('%m/%d/%Y %H:%M')}<br/><br/>
        </i>
        """
        story.append(Paragraph(footer_text, small_style))
        
        doc.build(story)
        
        for img in images:
            try:
                temp_path = f"/tmp/{os.path.basename(img.image_path)}"
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
                
        return output_path
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        raise

def generate_report_for_patient(db: Session, paciente_id: int) -> str:
    """
    Generates the PDF report and returns the file path
    """
    reports_dir = "/app/bucket/reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"preliminary_report_{paciente_id}_{timestamp}.pdf"
    output_path = os.path.join(reports_dir, filename)
    
    create_pdf_report(db, paciente_id, output_path)
    
    return output_path
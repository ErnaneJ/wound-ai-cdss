from PIL import Image as PILImage
import streamlit as st
from datetime import datetime
import os
import sys
import pandas as pd
import time
import re

if '/app/backend' not in sys.path:
    sys.path.append('/app/backend')

from backend.database_operations import (
    create_patient_with_chat,
    search_pacientes,
    get_paciente_with_chat,
    get_chat_status,
    get_db,
    classify_all_images_in_chat
)
from backend.models import Chat, ChatMessage, Image

import base64
import streamlit as st
from datetime import datetime
import os
import sys
import pandas as pd
import time

from backend.database_operations import (
    create_patient_with_chat,
    search_pacientes,
    get_paciente_with_chat,
    get_chat_status,
    add_images_to_chat,
    get_db
)
from backend.models import Chat, ChatMessage

st.set_page_config(
    page_title="Pressure Wound Analysis System",
    page_icon="🏥",
    layout="wide"
)

def stream_response(text: str):
    """Simulates text streaming"""
    for word in text.split():
        yield word + " "
        time.sleep(0.03)

def render_message_with_images(message_content: str, container, streaming=False):
    """
    Renders a message with support for image placeholders @@IMAGE:HASH@@
    """
    db = next(get_db())
    
    try:
        cursor = 0
        for match in re.finditer(r"@@IMAGE:([a-f0-9]+)@@", message_content):
            start, end = match.span()
            image_hash = match.group(1)

            before_text = message_content[cursor:start].strip()
            if before_text:
                if streaming:
                    container.write_stream(stream_response(before_text))
                else:
                    container.write(before_text)

            try:
                image = db.query(Image).filter(Image.image_path.like(f'%{image_hash}%')).first()
                if image and os.path.exists(image.image_path):
                    pil_image = PILImage.open(image.image_path)
                    container.image(
                        pil_image, 
                        caption=f"📷 {image.filename} - {image.classification}",
                        width=250
                    )
                else:
                    container.warning(f"❌ Image not found (Hash: {image_hash})")
            except Exception as img_error:
                container.error(f"❌ Error loading image: {str(img_error)}")

            cursor = end

        after_text = message_content[cursor:].strip() + "\n\n---\n\n***LLM:** Gemini | **Classification:** Authorial.*"
        if after_text:
            if streaming:
                container.write_stream(stream_response(after_text))
            else:
                container.write(after_text)

    except Exception as e:
        container.error(f"❌ Error rendering message: {str(e)}")
    finally:
        db.close()
        
def init_session_state():
    """Initializes session state"""
    if 'show_form' not in st.session_state:
        st.session_state.show_form = False

    if "temp_images" not in st.session_state:
        st.session_state.temp_images = []

def show_patient_form():
    """Shows the patient registration form"""
    st.subheader("📝 Register New Patient")
    
    with st.form("patient_form", clear_on_submit=True):
        with st.expander("👤 Patient Information", expanded=True):
            inputNomeContainer, inputDocumentContainer = st.columns(2)
            nome = inputNomeContainer.text_input("Full name (*)", placeholder="Ernane Ferreira")
            documento = inputDocumentContainer.text_input("Document", placeholder="000.000.000-00")

            inputAgeContainer, inputGenderContainer, inputDiabetesTypeContainer = st.columns(3)
            idade = inputAgeContainer.number_input("Age (*)", min_value=0, max_value=120, value=0)
            sexo = inputGenderContainer.selectbox("Gender (*)", ["", "M", "F"], format_func=lambda x: {"": "Select", "M": "Male", "F": "Female"}[x])
            diabetes_tipo = inputDiabetesTypeContainer.selectbox("Diabetes Type (*)", 
                ["", "Type 1", "Type 2", "Gestational", "Prediabetes", "Other"],
                format_func=lambda x: {"": "Select", "Type 1": "Diabetes Type 1", "Type 2": "Diabetes Type 2", 
                                        "Gestational": "Gestational Diabetes", "Prediabetes": "Prediabetes", 
                                        "Other": "Other"}[x])
            inputMedicamentosContainer, inputAlergiasContainer = st.columns(2)
            medicamentos = inputMedicamentosContainer.text_area("Current Medications", placeholder="List of current medications")
            alergias = inputAlergiasContainer.text_area("Known Allergies", placeholder="Known allergies to medications, foods, etc.")
            
            historico_medico = st.text_area("Medical History", placeholder="Pre-existing diseases, surgeries, etc.")

        with st.expander("📸 Images of the Wounds", expanded=False):
            uploaded_files = st.file_uploader(
                "Select images of the lesions.",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                help="Upload images of pressure injuries. You can upload multiple images at once or take a photo using your device's camera."
            )
        
            st.write("**Or take a photo:**")
            _, cameraInput, _ = st.columns([1, 1, 1])
            camera_image = cameraInput.camera_input("Integrated Camera", width=1080)
            
        col1, col2 = st.columns(2)
        cancel_submitted = col1.form_submit_button("❌ Cancel", width='stretch')
        submitted = col2.form_submit_button("💾 Save Patient and Process Analysis", width='stretch')
        
        if cancel_submitted:
            st.session_state.show_form = False
            st.rerun()
        
        if submitted:
            if not nome or not idade or not sexo or not diabetes_tipo:
                st.error("Please fill in all required fields (*)")
                st.stop()
            
            images_data = []
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    images_data.append({
                        'data': uploaded_file.getvalue(),
                        'filename': uploaded_file.name
                    })
            
            if camera_image:
                images_data.append({
                    'data': camera_image.getvalue(),
                    'filename': f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                })
            
            try:
                if len(images_data) == 0:
                    raise Exception("No images uploaded. At least one image of the lesion is required.")
                
                db = next(get_db())
                _ = create_patient_with_chat(
                    db, 
                    {
                        'nome': nome,
                        'idade': idade,
                        'sexo': sexo,
                        'diabetes_tipo': diabetes_tipo,
                        'historico_medico': historico_medico or '',
                        'documento': documento or '',
                        'medicamentos': medicamentos or '',
                        'alergias': alergias or ''
                    },
                    images_data
                )
                
                st.success(f"✅ Patient {nome} registered successfully!")
                if images_data:
                    st.info(f"📷 {len(images_data)} image(s) sent for analysis")
                
                st.session_state.show_form = False
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error saving patient: {str(e)}")

def show_chat_view(patient_id):
    """Shows the chat view for a specific patient"""
    db = next(get_db())
    patient_data = get_paciente_with_chat(db, patient_id)

    if not patient_data:
        st.error("Patient not found")
        return

    patient = patient_data['paciente']
    chat = patient_data['chat']
    images = patient_data['images']

    with st.sidebar:
        st.subheader(f"💬 Patient: {patient.name}")
        if st.button("👈🏼 Back", width='stretch'):
            st.query_params.clear()
            st.rerun()

        if st.button("🔄 Re-Classify All", type="primary", width='stretch'):
            classify_all_images_in_chat(db, chat.id)
            st.success("✅ All images were re-sent for classification!")
            time.sleep(3)
            st.rerun()

        if st.button("📄 Generate Pre-Laud PDF", type="primary", width='stretch', use_container_width=True):
            with st.spinner("Generating PDF report..."):
                try:
                    from backend.database_operations import generate_pdf_report
                    pdf_path = generate_pdf_report(db, patient.id)

                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()

                    st.success("✅ PDF report generated successfully!")
                    st.download_button(
                        label="📥 Download the Pre-Laud PDF",
                        data=pdf_bytes,
                        file_name=f"pre_laudo_{patient.name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")


        st.divider()

        with st.expander("👤 Patient Information", expanded=True):
            st.write("#### 📋 Personal Data")
            st.write(f"""
                    - **Name:** {patient.name}
                    - **Doc:** {patient.document if patient.document else "*Not informed*"}
                    - **Age:** {patient.age} years old
                    - **Sex:** {patient.sex}
                    - **Diabetes:** {patient.diabetes_type}
                    """)
            st.write("#### 🗄️ Medical History")
            if patient.medical_history:
                st.write(f"{(patient.medical_history[:500]).strip()}..." if len(patient.medical_history) > 500 else patient.medical_history)
            else:
                st.write("*Not informed*")

            st.write("#### 💊 Medications and Allergies")
            if patient.medications:
                st.write(f"- **Medications:** {patient.medications}")
            if patient.allergies:
                st.write(f"- **Allergies:** {patient.allergies}")
        
        with st.expander("📸 Wounds", expanded=False):
            new_uploaded_files = st.file_uploader(
                "Add New Images",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key=f"new_images_{patient_id}",
                    help="Upload new images for analysis. You can upload multiple images at once or take a photo using your device's camera."
                )
            
            if new_uploaded_files:
                if st.button("📤 Send New Images", key=f"send_new_images_{patient_id}", type="primary", width='stretch'):
                    try:
                        images_data = []
                        for uploaded_file in new_uploaded_files:
                            images_data.append({
                                'data': uploaded_file.getvalue(),
                                'filename': uploaded_file.name
                            })
                        
                        saved_images = add_images_to_chat(db, chat.id, images_data)
                        
                        st.success(f"✅ {len(saved_images)} new image(s) sent for analysis!")
                        time.sleep(1)
                        st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Error saving new images: {str(e)}")
            
            st.divider()
            if images:
                for idx, img in enumerate(images):
                    status_emoji = "" if img.classification != "Pending" else "⏳"
                    
                    try:
                        if os.path.exists(img.image_path):
                            pil_image = PILImage.open(img.image_path)
                            
                            st.caption(status_emoji + img.description)
                            
                            st.image(
                                pil_image,
                                caption=f"{status_emoji} {img.filename} - {img.classification}",
                                width='stretch'
                            )
                        
                        else:
                            st.warning(f"📄 File not found: {img.filename}")
                            
                    except Exception as e:
                        st.error(f"❌ Error loading image: {img.filename}")
                        st.code(f"Error: {str(e)}")
            else:
                st.info("📝 No images registered yet.")
        
        st.divider()
    
    with st.container(border=False, key="chat-content"):
        chat_messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).order_by(ChatMessage.created_at).all()
        
        if not chat_messages:
            st.info("💡 Start a conversation about the patient's wounds")
        
        for msg in chat_messages:
            if msg.is_user:
                with st.chat_message("user"):
                    st.write(msg.content)
            else:
                with st.chat_message("assistant"):
                    render_message_with_images(msg.content, st, streaming=False)
        
    user_input = st.chat_input("Type your message about the wounds...")
    
    if user_input:
        user_message = ChatMessage(
            chat_id=chat.id,
            content=user_input,
            is_user=True,
            message_type="text"
        )
        db.add(user_message)
        db.commit()
        
        with st.chat_message("user"):
            st.write(user_input)
        
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            with st.spinner("Analyzing your question..."):
                from backend.chat_service import generate_chat_response
                full_response = generate_chat_response(db, chat.id, user_input)
        
            displayed_response = ""
            for chunk in stream_response(full_response):
                displayed_response += chunk
                response_placeholder.write(displayed_response)
            
            ai_response = ChatMessage(
                chat_id=chat.id,
                content=full_response,
                is_user=False,
                message_type="text"
            )
            db.add(ai_response)
            db.commit()
        
        st.rerun()
            
def main():
    init_session_state()
    
    query_params = st.query_params
    patient_id = query_params.get("patient_id", [None])[0]
    
    if patient_id:
        show_chat_view(int(patient_id))
        return
    
    st.markdown(
        """
        <div style="text-align: center;">
            <h1>🏥 Wounds Analysis System</h1>
            <p>AI-assisted analysis for lesions in patients</p>
            <br/>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.session_state.show_form:
        show_patient_form()
    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_term = st.text_input(
                "🔍 Search for Patient:",
                placeholder="Enter the patient's name or document number...",
                key="search_input",
            )
        
        with col2:
            if st.button("➕ New Patient", type="primary", width='stretch', key="new_patient_button"):
                st.session_state.show_form = True
                st.rerun()
            st.markdown("<style>.st-key-new_patient_button {margin-top: 26.5px;}</style>", unsafe_allow_html=True)
                
        try:
            db = next(get_db())
            pacientes = search_pacientes(db, search_term)
            
            if pacientes:
                st.subheader(f"📋 Patients ({len(pacientes)})")
                
                df_data = []
                for p in pacientes:
                    chat = db.query(Chat).filter(Chat.patient_id == p.id).first()
                    status = get_chat_status(chat)

                    df_data.append({
                        "id": p.id,
                        "acesso": f"/?patient_id={p.id}",
                        "nome": p.name,
                        "documento": "••••••" + p.document[-6:] if len(p.document) > 6 else p.document,
                        "idade": p.age,
                        "sexo": p.sex,
                        "diabetes_tipo": p.diabetes_type,
                        "status": status,
                        "historico_medico": p.medical_history if len(p.medical_history) <= 80 else p.medical_history[:80-1].rstrip() + "…",
                        "medicamentos": p.medications if len(p.medications) <= 80 else p.medications[:80-1].rstrip() + "…",
                        "alergias": p.allergies if len(p.allergies) <= 80 else p.allergies[:80-1].rstrip() + "…",
                        "created_at": p.created_at,
                    })
                
                df = pd.DataFrame(df_data)
                
                st.dataframe(
                    df,
                    width='stretch',
                    column_config = {
                        "id": st.column_config.NumberColumn(
                            "ID",
                            help="Patient ID",
                            format="%d",
                            width="small"
                        ),
                        "acesso": st.column_config.LinkColumn(
                            "Quick Access",
                            help="Click to open the patient chat.",
                            width="small"
                        ),
                        "nome": st.column_config.TextColumn(
                            "Name",
                            help="Click 'Open' in the right-hand column to open the patient.",
                            width="large"
                        ),
                        "idade": st.column_config.NumberColumn(
                            "Age",
                            help="Age in years",
                            format="%.0f",
                            width="small"
                        ),
                        "sexo": st.column_config.ListColumn(
                            "Sex",
                            help="M / F / -",
                            width="extra_small"
                        ),
                        "documento": st.column_config.TextColumn(
                            "Document",
                            help="Patient Document",
                            width="small"
                        ),
                        "diabetes_tipo": st.column_config.ListColumn(
                            "Diabetes",
                            help="Type of diabetes",
                            width="small"
                        ),
                        "status": st.column_config.ListColumn(
                            "Analysis Status",
                            help="Current status of image processing.",
                            width="small"
                        ),
                        "historico_medico": st.column_config.TextColumn(
                            "History",
                            help="Click 'View' for details (use individual detail)",
                            width="xxl"
                        ),
                        "medicamentos": st.column_config.TextColumn(
                            "Medications",
                            help="Main medications",
                            width="large"
                        ),
                        "alergias": st.column_config.TextColumn(
                            "Allergies",
                            help="Known allergies",
                            width="large"
                        ),
                        "created_at": st.column_config.DatetimeColumn(
                            "Created in",
                            help="Creation date",
                            format="MM/DD/YYYY HH:mm",
                            width="small"
                        ),
                    }
                )
            
            else:
                if search_term:
                    st.info(f"🔍 No patients found for '{search_term}'")
                else:
                    st.info("📝 No patients registered yet. Click on 'New Patient' to begin.")
        
        except Exception as e:
            st.error(f"Error connecting to the database: {str(e)}")

if __name__ == "__main__":
    main()
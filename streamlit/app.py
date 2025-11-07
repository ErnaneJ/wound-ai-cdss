import streamlit as st
from datetime import datetime
import os
import sys
import pandas as pd
import time

if '/app/backend' not in sys.path:
    sys.path.append('/app/backend')

from backend.database_operations import (
    create_paciente_with_chat, 
    search_pacientes, 
    get_paciente_with_chat,
    get_chat_status,
    get_db,
    classify_all_images_in_chat
)
from backend.models import Chat, ChatMessage

import base64
import streamlit as st
from datetime import datetime
import os
import sys
import pandas as pd
import time

from backend.database_operations import (
    create_paciente_with_chat, 
    search_pacientes, 
    get_paciente_with_chat,
    get_chat_status,
    add_images_to_chat,
    get_db
)
from backend.models import Chat, ChatMessage

st.set_page_config(
    page_title="Sistema de Análise de Lesões por Pressão",
    page_icon="🏥",
    layout="wide"
)

def init_session_state():
    """Inicializa estados da sessão"""
    if 'show_form' not in st.session_state:
        st.session_state.show_form = False

    if "temp_images" not in st.session_state:
        st.session_state.temp_images = []

def show_patient_form():
    """Mostra formulário de cadastro de paciente"""
    st.subheader("📝 Cadastrar Novo Paciente")
    
    with st.form("patient_form", clear_on_submit=True):
        with st.expander("👤 Informações do Paciente", expanded=True):
            inputNomeContainer, inputDocumentContainer = st.columns(2)
            nome = inputNomeContainer.text_input("Nome completo (*)", placeholder="João Silva")
            documento = inputDocumentContainer.text_input("Documento (CPF/RG)", placeholder="000.000.000-00")

            inputAgeContainer, inputGenderContainer, inputDiabetesTypeContainer = st.columns(3)
            idade = inputAgeContainer.number_input("Idade (*)", min_value=0, max_value=120, value=0)
            sexo = inputGenderContainer.selectbox("Sexo (*)", ["", "M", "F"], format_func=lambda x: {"": "Selecione", "M": "Masculino", "F": "Feminino"}[x])
            diabetes_tipo = inputDiabetesTypeContainer.selectbox("Tipo de Diabetes (*)", 
                ["", "Tipo 1", "Tipo 2", "Gestacional", "Pré-diabetes", "Outro"],
                format_func=lambda x: {"": "Selecione", "Tipo 1": "Diabetes Tipo 1", "Tipo 2": "Diabetes Tipo 2", 
                                        "Gestacional": "Diabetes Gestacional", "Pré-diabetes": "Pré-diabetes", 
                                        "Outro": "Outro"}[x])
            inputMedicamentosContainer, inputAlergiasContainer = st.columns(2)
            medicamentos = inputMedicamentosContainer.text_area("Medicamentos em Uso", placeholder="Lista de medicamentos atuais")
            alergias = inputAlergiasContainer.text_area("Alergias Conhecidas", placeholder="Alergias a medicamentos, alimentos, etc.")
            
            historico_medico = st.text_area("Histórico Médico", placeholder="Doenças pré-existentes, cirurgias, etc.")

        with st.expander("📸 Imagens das Lesões", expanded=False):
            # Upload por arquivo
            uploaded_files = st.file_uploader(
                "Selecione imagens das lesões",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                help="Faça upload das imagens das lesões por pressão"
            )
        
            # Upload por câmera
            st.write("**Ou tire uma foto:**")
            _, cameraInput, _ = st.columns([1, 1, 1])
            camera_image = cameraInput.camera_input("Câmera Integrada", width=1080)
            
        col1, col2 = st.columns(2)
        cancel_submitted = col1.form_submit_button("❌ Cancelar", width='stretch')
        submitted = col2.form_submit_button("💾 Salvar Paciente e Processar Análise", width='stretch')
        
        if cancel_submitted:
            st.session_state.show_form = False
            st.rerun()
        
        if submitted:
            if not nome or not idade or not sexo or not diabetes_tipo:
                st.error("Por favor, preencha todos os campos obrigatórios (*)")
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
                    raise Exception("Nenhuma imagem enviada. É necessário ao menos uma imagem da lesão.")
                
                db = next(get_db())
                _ = create_paciente_with_chat(
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
                
                st.success(f"✅ Paciente {nome} cadastrado com sucesso!")
                if images_data:
                    st.info(f"📷 {len(images_data)} imagem(s) enviada(s) para análise")
                
                st.session_state.show_form = False
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao salvar paciente: {str(e)}")

def show_chat_view(patient_id):
    """Mostra a view do chat para um paciente específico"""
    db = next(get_db())
    paciente_data = get_paciente_with_chat(db, patient_id)
    
    if not paciente_data:
        st.error("Paciente não encontrado")
        return
    
    paciente = paciente_data['paciente']
    chat = paciente_data['chat']
    images = paciente_data['images']

    with st.sidebar:
        st.subheader(f"💬 Chat {paciente.nome}")
        if st.button("👈🏼 Voltar", width='stretch'):
            st.query_params.clear()
            st.rerun()
        
        if st.button("🔄 Ré-Classificar Tudo", type="primary", width='stretch'):
            classify_all_images_in_chat(db, chat.id)
            st.success("✅ Todas as imagens foram reenviadas para classificação!")
            time.sleep(3)
            st.rerun()
        
        # if st.button("📊 Relatório", type="primary", width='stretch'):
        #     st.info("📋 Funcionalidade de relatório em desenvolvimento")
            
        st.divider()

        with st.expander("👤 Informações do Paciente", expanded=True):
            st.write("#### 📋 Dados Pessoais")
            st.write(f"""
                    - **Nome:** {paciente.nome}
                    - **Documento:** {paciente.documento if paciente.documento else "*Não informado*"}
                    - **Idade:** {paciente.idade} anos
                    - **Sexo:** {paciente.sexo}
                    - **Diabetes:** {paciente.diabetes_tipo}
                    """)
            st.write("#### 🗄️ Histórico Médico")
            if paciente.historico_medico:
                st.write(f"{(paciente.historico_medico[:500]).strip()}..." if len(paciente.historico_medico) > 500 else paciente.historico_medico)
            else:
                st.write("*Não informado*")

            st.write("#### 💊 Medicamentos & Alergias")
            if paciente.medicamentos:
                st.write(f"- **Medicamentos:** {paciente.medicamentos}")
            if paciente.alergias:
                st.write(f"- **Alergias:** {paciente.alergias}")
        
        with st.expander("📸 Lesões", expanded=False):
            new_uploaded_files = st.file_uploader(
                "Adicionar Novas Imagens",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key=f"new_images_{patient_id}",
                help="Faça upload de novas imagens para análise"
            )
            
            if new_uploaded_files:
                if st.button("📤 Enviar Novas Imagens", key=f"send_new_images_{patient_id}", type="primary", width='stretch'):
                    try:
                        images_data = []
                        for uploaded_file in new_uploaded_files:
                            images_data.append({
                                'data': uploaded_file.getvalue(),
                                'filename': uploaded_file.name
                            })
                        
                        saved_images = add_images_to_chat(db, chat.id, images_data)
                        
                        st.success(f"✅ {len(saved_images)} nova(s) imagem(ns) enviada(s) para análise!")
                        time.sleep(1)
                        st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar novas imagens: {str(e)}")
            
            st.divider()
            if images:
                for idx, img in enumerate(images):
                    status_emoji = "" if img.classification != "Pendente" else "⏳"
                    
                    try:
                        if os.path.exists(img.image_path):
                            from PIL import Image as PILImage
                            pil_image = PILImage.open(img.image_path)
                            
                            st.caption(status_emoji + img.description)
                            
                            st.image(
                                pil_image,
                                caption=f"{status_emoji} {img.filename} - {img.classification}",
                                width='stretch'
                            )
                        
                        else:
                            st.warning(f"📄 Arquivo não encontrado: {img.filename}")
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao carregar imagem: {img.filename}")
                        st.code(f"Erro: {str(e)}")
            else:
                st.info("📝 Nenhuma imagem cadastrada ainda.")
        
        st.divider()
    
    # Área principal do chat (mantida igual)
    with st.container(border=False, key="chat-content"):
        chat_messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).order_by(ChatMessage.created_at).all()
        
        if not chat_messages:
            st.info("💡 Inicie uma conversa sobre as lesões do paciente")
        
        for msg in chat_messages:
            if msg.is_user:
                with st.chat_message("user"):
                    st.write(msg.content)
            else:
                with st.chat_message("assistant"):
                    st.write(msg.content)
        
    # Input para nova mensagem
    user_input = st.chat_input("Digite sua mensagem...")
    
    if user_input:
        # Salva mensagem do usuário
        user_message = ChatMessage(
            chat_id=chat.id,
            content=user_input,
            is_user=True,
            message_type="text"
        )
        db.add(user_message)
        
        # TODO: Integrar com Gemini para resposta
        # Por enquanto, resposta mock
        ai_response = ChatMessage(
            chat_id=chat.id,
            content="Esta é uma resposta simulada da IA. A integração com Gemini será implementada em breve.",
            is_user=False,
            message_type="text"
        )
        db.add(ai_response)
        db.commit()
        
        st.rerun()
            
def main():
    init_session_state()
    
    # Verifica se tem patient_id na query string
    query_params = st.query_params
    patient_id = query_params.get("patient_id", [None])[0]
    
    if patient_id:
        show_chat_view(int(patient_id))
        return
    
    # Página principal - Lista de pacientes
    st.markdown(
        """
        <div style="text-align: center;">
            <h1>🏥 Sistema de Análise de Lesões por Pressão</h1>
            <p>Análise assistida por IA para pacientes diabéticos</p>
            <br/>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Mostrar formulário ou listagem
    if st.session_state.show_form:
        show_patient_form()
    else:
        # Barra de busca e botão novo
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_term = st.text_input(
                "🔍 Buscar Paciente:",
                placeholder="Digite o nome ou documento do paciente...",
                key="search_input",
            )
        
        with col2:
            if st.button("➕ Novo Paciente", type="primary", width='stretch', key="new_patient_button"):
                st.session_state.show_form = True
                st.rerun()
            st.markdown("<style>.st-key-new_patient_button {margin-top: 26.5px;}</style>", unsafe_allow_html=True)
                
        try:
            db = next(get_db())
            pacientes = search_pacientes(db, search_term)
            
            if pacientes:
                st.subheader(f"📋 Pacientes ({len(pacientes)})")
                
                # Cria dataframe com link para o chat
                df_data = []
                for p in pacientes:
                    chat = db.query(Chat).filter(Chat.paciente_id == p.id).first()
                    status = get_chat_status(chat)

                    df_data.append({
                        "id": p.id,
                        "acesso": f"/?patient_id={p.id}",
                        "nome": p.nome,
                        "documento": "••••••" + p.documento[-6:] if len(p.documento) > 6 else p.documento,
                        "idade": p.idade,
                        "sexo": p.sexo,
                        "diabetes_tipo": p.diabetes_tipo,
                        "status": status,
                        "historico_medico": p.historico_medico if len(p.historico_medico) <= 80 else p.historico_medico[:80-1].rstrip() + "…",
                        "medicamentos": p.medicamentos if len(p.medicamentos) <= 80 else p.medicamentos[:80-1].rstrip() + "…",
                        "alergias": p.alergias if len(p.alergias) <= 80 else p.alergias[:80-1].rstrip() + "…",
                        "created_at": p.created_at,
                    })
                
                df = pd.DataFrame(df_data)
                
                # Configura o dataframe para ter links clicáveis
                st.dataframe(
                    df,
                    width='stretch',
                    column_config = {
                        "id": st.column_config.NumberColumn(
                            "ID",
                            help="Identificador do paciente",
                            format="%d",
                            width="small"
                        ),
                        "acesso": st.column_config.LinkColumn(
                            "Acesso Rápido",
                            help="Clique para abrir o chat do paciente",
                            width="small"
                        ),
                        "nome": st.column_config.TextColumn(
                            "Nome",
                            help="Clique em 'Abrir' na coluna à direita para abrir o paciente",
                            width="large"
                        ),
                        "idade": st.column_config.NumberColumn(
                            "Idade (anos)",
                            help="Idade em anos",
                            format="%.0f",
                            width="small"
                        ),
                        "sexo": st.column_config.ListColumn(
                            "Sexo",
                            help="M / F / -",
                            width="extra_small"
                        ),
                        "documento": st.column_config.TextColumn(
                            "Documento",
                            help="Parcialmente mascarado",
                            width="small"
                        ),
                        "diabetes_tipo": st.column_config.ListColumn(
                            "Diabetes",
                            help="Tipo de diabetes",
                            width="small"
                        ),
                        "status": st.column_config.ListColumn(
                            "Status da Análise",
                            help="Status atual do processamento das imagens",
                            width="small"
                        ),
                        "historico_medico": st.column_config.TextColumn(
                            "Histórico",
                            help="Clique em 'Ver' para detalhes (usar detalhe individual)",
                            width="xxl"
                        ),
                        "medicamentos": st.column_config.TextColumn(
                            "Medicamentos",
                            help="Principais medicamentos",
                            width="large"
                        ),
                        "alergias": st.column_config.TextColumn(
                            "Alergias",
                            help="Alergias conhecidas",
                            width="large"
                        ),
                        "created_at": st.column_config.DatetimeColumn(
                            "Criado em",
                            help="Data de criação",
                            format="DD/MM/YYYY à\s HH:mm",
                            width="small"
                        ),
                    }
                )
            
            else:
                if search_term:
                    st.info(f"🔍 Nenhum paciente encontrado para '{search_term}'")
                else:
                    st.info("📝 Nenhum paciente cadastrado ainda. Clique em 'Novo Paciente' para começar.")
        
        except Exception as e:
            st.error(f"Erro ao conectar com o banco de dados: {str(e)}")

if __name__ == "__main__":
    main()
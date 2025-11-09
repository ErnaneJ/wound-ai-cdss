import tensorflow as tf
import numpy as np
from PIL import Image
import os
import pandas as pd
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Flatten, Dropout

MODELO_H5_PATH = '/Users/ernane/me/diabetes-lesion-analysis/backend/models/best_wound_classifier_FINETUNED.h5'
METRICAS_CSV_PATH = '/Users/ernane/me/diabetes-lesion-analysis/backend/models/wound_metrics_report_FINETUNED.csv'

CLASSES = ['BG', 'D', 'N', 'P', 'S', 'V']
IMG_SIZE = (224, 224)

MODELO = None
METRICAS_DF = None

def carregar_recursos():
    """Carrega modelo e métricas"""
    global MODELO, METRICAS_DF
    
    if MODELO is not None:
        return True

    try:
        print("📦 Carregando modelo...")
        
        base_model = VGG16(weights=None, include_top=False, input_shape=(224, 224, 3))
        for layer in base_model.layers:
            layer.trainable = False
        x = base_model.output
        x = Flatten()(x)
        x = Dense(512, activation='relu')(x)
        x = Dropout(0.5)(x)
        x = Dense(256, activation='relu')(x)
        x = Dropout(0.5)(x)
        predictions = Dense(len(CLASSES), activation='softmax')(x)
        MODELO = Model(inputs=base_model.input, outputs=predictions)
        
        MODELO.load_weights(MODELO_H5_PATH)
        print("✅ Modelo carregado")
        
        METRICAS_DF = pd.read_csv(METRICAS_CSV_PATH, index_col=0)
        print("✅ Métricas carregadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao carregar recursos: {e}")
        return False

def traduzir_classe(classe):
    traducoes = {
        'BG': 'Background',
        'D': 'Ulcera Diabetica', 
        'N': 'Pele Normal',
        'P': 'Ulcera por Pressao',
        'S': 'Ferida Cirurgica',
        'V': 'Ulcera Venosa'
    }
    return traducoes.get(classe, classe)

def classificar_imagem(image_path: str) -> dict:
    """
    Classifica uma imagem e retorna um dicionário estruturado com 
    probabilidades e métricas de risco para o LLM.
    """
    if not carregar_recursos():
        return {"status": "erro", "mensagem": "Falha ao carregar modelo ou métricas."}
    
    try:
        print(f"🔍 Processando: {os.path.basename(image_path)}")
        
        img = Image.open(image_path).convert('RGB')
        img = img.resize(IMG_SIZE)
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        predictions = MODELO.predict(img_array, verbose=0)[0] # Vetor de 6 probabilidades
        
        class_idx = np.argmax(predictions)
        classe_predita = CLASSES[class_idx]
        confianca_predita = float(predictions[class_idx])
        
        probabilidades = {c: f"{p*100:.2f}%" for c, p in zip(CLASSES, predictions)}
        
        recall_p = float(METRICAS_DF.loc['P', 'recall'])
        
        top_classes = np.argsort(predictions)[::-1] # Índices em ordem decrescente
        top_3_classes = [CLASSES[i] for i in top_classes[:3]]
        
        dados_analise = {
            "status": "sucesso",
            "classe_predita": classe_predita,
            "confianca_predita_percentual": f"{confianca_predita*100:.2f}%",
            "classe_traduzida": traduzir_classe(classe_predita),
            "probabilidades_completas": probabilidades,
            "top_3_classes": top_3_classes,
            "metrica_f1_classe_predita": float(METRICAS_DF.loc[classe_predita, 'f1-score']),
            "risco_p": {
                "Recall_P": recall_p,
                "Aviso_P": f"Recall histórico ({recall_p:.2f}) para Úlcera por Pressão é baixo. Cautela é necessária."
            }
        }
        
        print(f"✅ Resultado: {dados_analise['classe_predita']} ({dados_analise['confianca_predita_percentual']})")
        return dados_analise
        
    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        return {"status": "erro", "mensagem": str(e)}
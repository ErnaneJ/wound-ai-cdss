import tensorflow as tf
import numpy as np
from PIL import Image
import os
import pandas as pd
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Flatten, Dropout

# Configurações
MODELO_H5_PATH = '/app/backend/models/best_wound_classifier_FINETUNED.h5'
METRICAS_CSV_PATH = '/app/backend/models/wound_metrics_report_FINETUNED.csv'

CLASSES = ['BG', 'D', 'N', 'P', 'S', 'V']
IMG_SIZE = (224, 224)

# Cache
MODELO = None
METRICAS_DF = None

def carregar_recursos():
    """Carrega modelo e métricas"""
    global MODELO, METRICAS_DF
    
    if MODELO is not None:
        return True

    try:
        print("📦 Carregando modelo...")
        
        # Reconstruir arquitetura
        base_model = VGG16(weights=None, include_top=False, input_shape=(224, 224, 3))
        
        # Congelar camadas
        for layer in base_model.layers:
            layer.trainable = False

        # Construir cabeçalho
        x = base_model.output
        x = Flatten()(x)
        x = Dense(512, activation='relu')(x)
        x = Dropout(0.5)(x)
        x = Dense(256, activation='relu')(x)
        x = Dropout(0.5)(x)
        predictions = Dense(len(CLASSES), activation='softmax')(x)

        # Criar modelo final
        MODELO = Model(inputs=base_model.input, outputs=predictions)
        
        # Carregar pesos
        MODELO.load_weights(MODELO_H5_PATH)
        print("✅ Modelo carregado")
        
        # Carregar métricas
        METRICAS_DF = pd.read_csv(METRICAS_CSV_PATH, index_col=0)
        print("✅ Métricas carregadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao carregar recursos: {e}")
        return False

def classificar_imagem(image_path):
    """Classifica uma imagem"""
    if not carregar_recursos():
        return None
    
    try:
        print(f"🔍 Processando: {os.path.basename(image_path)}")
        
        # Carregar e pré-processar imagem
        img = Image.open(image_path).convert('RGB')
        img = img.resize(IMG_SIZE)
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        # Predição
        predictions = MODELO.predict(img_array, verbose=0)[0]
        class_idx = np.argmax(predictions)
        confidence = float(predictions[class_idx])
        
        resultado = {
            'classe': CLASSES[class_idx],
            'confianca': f"{confidence*100:.1f}%",
            'classe_traduzida': traduzir_classe(CLASSES[class_idx])
        }
        
        print(f"✅ Resultado: {resultado['classe']} ({resultado['confianca']})")
        return resultado
        
    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        return None

def traduzir_classe(classe):
    """Traduz código da classe para português"""
    traducoes = {
        'BG': 'Background',
        'D': 'Úlcera Diabética', 
        'N': 'Pele Normal',
        'P': 'Úlcera por Pressão',
        'S': 'Ferida Cirúrgica',
        'V': 'Úlcera Venosa'
    }
    return traducoes.get(classe, classe)
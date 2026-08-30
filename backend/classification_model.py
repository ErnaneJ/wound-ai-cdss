import tensorflow as tf
import numpy as np
from PIL import Image
import os
import pandas as pd
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Flatten, Dropout

MODELO_H5_PATH = '/app/backend/models/best_wound_classifier_FINETUNED.h5'
METRICAS_CSV_PATH = '/app/backend/models/wound_metrics_report_FINETUNED.csv'

CLASSES = ['BG', 'D', 'N', 'P', 'S', 'V']
IMG_SIZE = (224, 224)

MODELO = None
METRICAS_DF = None

def carregar_recursos():
    """Loads the model and metrics"""
    global MODELO, METRICAS_DF
    
    if MODELO is not None:
        return True

    try:
        print("📦  Loading Model....")
        
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
        print("✅ Model loaded")
        
        METRICAS_DF = pd.read_csv(METRICAS_CSV_PATH, index_col=0)
        print("✅ Metrics loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ Error to load model or metrics: {e}")
        return False

def traduzir_classe(classe):
    traducoes = {
        'BG': 'Background',
        'D': 'Diabetic Ulcer', 
        'N': 'Normal Skin',
        'P': 'Pressure Ulcer',
        'S': 'Surgical Wound',
        'V': 'Venous Ulcer'
    }
    return traducoes.get(classe, classe)

def classificar_imagem(image_path: str) -> dict:
    """
    Classifies an image and returns a structured dictionary with
    probabilities and risk metrics for the LLM.
    """
    if not carregar_recursos():
        return {"status": "erro", "mensagem": "Failed to load model or metrics."}
    
    try:
        print(f"🔍 Processing: {os.path.basename(image_path)}")
        
        img = Image.open(image_path).convert('RGB')
        img = img.resize(IMG_SIZE)
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        predictions = MODELO.predict(img_array, verbose=0)[0] # Vector of 6 probabilities
        
        class_idx = np.argmax(predictions)
        classe_predita = CLASSES[class_idx]
        confianca_predita = float(predictions[class_idx])
        
        probabilidades = {c: f"{p*100:.2f}%" for c, p in zip(CLASSES, predictions)}
        
        recall_p = float(METRICAS_DF.loc['P', 'recall'])
        
        top_classes = np.argsort(predictions)[::-1]
        top_3_classes = [CLASSES[i] for i in top_classes[:3]]
        
        dados_analise = {
            "status": "sucesso",
            "model_version": os.path.basename(MODELO_H5_PATH),
            "classe_predita": classe_predita,
            "confianca_predita_percentual": f"{confianca_predita*100:.2f}%",
            "classe_traduzida": traduzir_classe(classe_predita),
            "probabilidades_completas": probabilidades,
            "top_3_classes": top_3_classes,
            "metrica_f1_classe_predita": float(METRICAS_DF.loc[classe_predita, 'f1-score']),
            "risco_p": {
                "Recall_P": recall_p,
                "Aviso_P": f"Historical recall ({recall_p:.2f}) for Pressure Ulcer is low. Caution is advised."
            }
        }
        
        print(f"✅ Result: {dados_analise['classe_predita']} ({dados_analise['confianca_predita_percentual']})")
        return dados_analise
        
    except Exception as e:
        print(f"❌ Error in classification: {e}")
        return {"status": "erro", "mensagem": str(e)}
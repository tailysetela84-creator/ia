"""
feature_extractor.py
=====================
Responsável por transformar áudio (numpy array) num vetor numérico
("embedding") usando o modelo pré-treinado Wav2Vec2.

Este é o "modelo de reconhecimento de voz já existente" pedido no
requisito: usamo-lo como extrator de características (congelado, sem
re-treino), não como conversor de voz-para-texto completo.

O modelo é carregado apenas uma vez (padrão singleton) porque descarregar
e inicializar o Wav2Vec2 demora alguns segundos — não queremos repetir
isso a cada gravação.
"""

import numpy as np
import torch
from transformers import Wav2Vec2Processor, Wav2Vec2Model

MODEL_NAME = "facebook/wav2vec2-base"

_processor = None
_model = None
_device = "cuda" if torch.cuda.is_available() else "cpu"


def _load_model():
    """Carrega o processor e o modelo Wav2Vec2 uma única vez (lazy loading)."""
    global _processor, _model
    if _model is None:
        print("⏳ A carregar o modelo Wav2Vec2 (só acontece uma vez por execução)...")
        _processor = Wav2Vec2Processor.from_pretrained(MODEL_NAME)
        _model = Wav2Vec2Model.from_pretrained(MODEL_NAME)
        _model.to(_device)
        _model.eval()  # modo avaliação: desliga dropout, etc. Não vamos treinar isto.
        print(f"✅ Modelo carregado (dispositivo: {_device}).")
    return _processor, _model


def extract_embedding(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """
    Converte um array de áudio (mono, 16kHz, float32 em [-1,1]) num vetor
    de características de tamanho fixo (768 dimensões).

    Passos:
      1. Passa o áudio pelo Wav2Vec2 -> obtém uma sequência de vetores,
         um por "frame" temporal (aprox. 1 vetor a cada 20ms de áudio).
      2. Mean pooling ao longo do tempo -> resume a sequência inteira
         num único vetor de tamanho fixo, independente da duração do áudio.
      3. Normalização L2 -> torna o vetor comparável por similaridade de
         cosseno, que é invariante a diferenças de "volume" do embedding.
    """
    processor, model = _load_model()

    inputs = processor(audio, sampling_rate=sample_rate, return_tensors="pt")
    input_values = inputs.input_values.to(_device)

    with torch.no_grad():  # não precisamos de gradientes: o modelo está congelado
        outputs = model(input_values)
        hidden_states = outputs.last_hidden_state  # shape: (1, T, 768)

    # Mean pooling ao longo da dimensão temporal (T)
    embedding = hidden_states.mean(dim=1).squeeze(0).cpu().numpy()  # shape: (768,)

    # Normalização L2
    norm = np.linalg.norm(embedding)
    if norm > 1e-8:
        embedding = embedding / norm

    return embedding

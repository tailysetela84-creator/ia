"""
recognizer.py
=============
O "cérebro" do sistema: aprende palavras a partir de embeddings e
reconhece novas gravações.

Algoritmo: Prototypical Network (classificador por protótipos / nearest-centroid)
-----------------------------------------------------------------------------
- Para cada palavra, o "protótipo" é a média (centróide) dos embeddings de
  todos os exemplos gravados dessa palavra.
- Para reconhecer um novo áudio: calcula-se o seu embedding e compara-se,
  por similaridade de cosseno, com o protótipo de cada palavra conhecida.
  A palavra com maior similaridade é a resposta, desde que ultrapasse
  um limiar mínimo de confiança (caso contrário: "palavra não reconhecida").

Vantagens desta abordagem para o requisito do projeto:
  - Aprender uma palavra nova = recalcular uma média. Não é preciso
    re-treinar nenhuma rede neuronal, por isso é instantâneo.
  - Escala bem: adicionar a palavra 101 não torna mais lento reconhecer
    as outras 100.
  - Lida naturalmente com várias gravações da mesma palavra: mais
    exemplos -> protótipo mais robusto e representativo.

Também incluímos uma alternativa por k-NN (nos comentários/função
`recognize_knn`) para quem quiser comparar as duas abordagens.
"""

import numpy as np
from sklearn.neighbors import KNeighborsClassifier

from . import database
from .feature_extractor import extract_embedding

DEFAULT_THRESHOLD = 0.75  # similaridade mínima de cosseno para aceitar uma predição


class WordRecognizer:
    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold
        self.prototypes = {}  # { "Makonde": np.array([...]), ... }
        self._knn = None
        self._knn_labels = []

    # ------------------------------------------------------------------
    # Treino / atualização
    # ------------------------------------------------------------------
    def rebuild_from_database(self):
        """
        Recalcula todos os protótipos a partir dos embeddings já guardados
        na base de dados. Rápido mesmo com muitas palavras, porque os
        embeddings já estão pré-calculados (não é preciso reprocessar áudio).

        Chamar isto:
          - no arranque da aplicação;
          - depois de ensinar uma palavra nova;
          - depois de remover uma palavra.
        """
        samples_by_word = database.get_all_samples_with_embeddings()

        self.prototypes = {}
        embeddings_flat = []
        labels_flat = []

        for word, embeddings in samples_by_word.items():
            embeddings = np.array(embeddings)
            prototype = embeddings.mean(axis=0)
            # normaliza o protótipo para a similaridade de cosseno ficar correta
            norm = np.linalg.norm(prototype)
            if norm > 1e-8:
                prototype = prototype / norm
            self.prototypes[word] = prototype

            embeddings_flat.extend(embeddings)
            labels_flat.extend([word] * len(embeddings))

        # Também mantemos um k-NN pronto a usar como alternativa/validação cruzada
        if embeddings_flat:
            k = min(3, len(embeddings_flat))
            self._knn = KNeighborsClassifier(n_neighbors=k, metric="cosine")
            self._knn.fit(np.array(embeddings_flat), labels_flat)
            self._knn_labels = labels_flat
        else:
            self._knn = None

    def learn_word(self, word_name: str, audio_samples: list, audio_save_dir: str):
        """
        Ensina (ou reforça) uma palavra a partir de uma lista de gravações
        já pré-processadas (numpy arrays).
        `audio_save_dir` é a pasta onde os .wav desta palavra serão guardados.
        """
        import os
        from .audio_utils import save_wav

        os.makedirs(audio_save_dir, exist_ok=True)
        existing = len(database.get_all_samples_with_embeddings().get(word_name, []))

        for i, audio in enumerate(audio_samples, start=existing + 1):
            path = os.path.join(audio_save_dir, f"sample_{i}.wav")
            save_wav(audio, path)
            embedding = extract_embedding(audio)
            database.add_sample(word_name, path, embedding)

        # Atualiza os protótipos imediatamente para refletir os novos exemplos
        self.rebuild_from_database()

    # ------------------------------------------------------------------
    # Reconhecimento
    # ------------------------------------------------------------------
    def recognize(self, audio: np.ndarray):
        """
        Reconhece uma única palavra a partir de um áudio.
        Devolve (palavra_ou_None, confianca).
        """
        if not self.prototypes:
            return None, 0.0

        embedding = extract_embedding(audio)

        best_word = None
        best_score = -1.0
        for word, prototype in self.prototypes.items():
            # similaridade de cosseno (ambos os vetores já estão normalizados)
            score = float(np.dot(embedding, prototype))
            if score > best_score:
                best_score = score
                best_word = word

        if best_score >= self.threshold:
            return best_word, best_score
        return None, best_score

    def recognize_knn(self, audio: np.ndarray):
        """Alternativa de reconhecimento usando k-NN em vez de protótipos."""
        if self._knn is None:
            return None, 0.0
        embedding = extract_embedding(audio).reshape(1, -1)
        pred = self._knn.predict(embedding)[0]
        proba = self._knn.predict_proba(embedding).max()
        return pred, float(proba)

    def recognize_phrase(self, audio: np.ndarray):
        """
        Reconhece uma frase com várias palavras (ex: "Olá, computador"),
        segmentando primeiro por silêncio e depois reconhecendo cada
        segmento individualmente. Ver limitações no README.
        """
        from .audio_utils import split_into_words

        segments = split_into_words(audio)
        results = []
        for segment in segments:
            word, score = self.recognize(segment)
            results.append((word, score))
        return results

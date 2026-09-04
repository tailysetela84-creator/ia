"""
audio_utils.py (versão servidor)
=================================
Diferença em relação à versão desktop: aqui NÃO gravamos do microfone
local (o servidor não tem microfone do utilizador). Em vez disso,
recebemos bytes de áudio enviados pelo navegador (gravados lá com
MediaRecorder, normalmente em formato WebM/Opus ou WAV) e descodificamo-los
para um array numpy 16kHz mono, exatamente no mesmo formato que o
Wav2Vec2 espera.

A conversão de formato (WebM -> WAV/PCM) usa o `ffmpeg` via `pydub`,
por isso o `ffmpeg` tem de estar instalado no sistema/imagem Docker.
"""

import io
import os
import numpy as np
import soundfile as sf
import librosa
from pydub import AudioSegment

SAMPLE_RATE = 16000  # Wav2Vec2 espera 16kHz


def decode_uploaded_audio(raw_bytes: bytes) -> np.ndarray:
    """
    Recebe os bytes crus de um ficheiro de áudio enviado pelo navegador
    (qualquer formato que o ffmpeg reconheça: webm, ogg, wav, mp3...)
    e devolve um array numpy 1D, mono, 16kHz, float32 em [-1, 1].
    """
    audio_segment = AudioSegment.from_file(io.BytesIO(raw_bytes))
    audio_segment = audio_segment.set_frame_rate(SAMPLE_RATE).set_channels(1)

    samples = np.array(audio_segment.get_array_of_samples()).astype(np.float32)
    # Normaliza consoante a profundidade de bits original (ex: 16-bit -> 32768)
    max_val = float(1 << (8 * audio_segment.sample_width - 1))
    samples = samples / max_val
    return samples


def save_wav(audio: np.ndarray, path: str, sample_rate: int = SAMPLE_RATE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sf.write(path, audio, sample_rate)


def load_wav(path: str, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    audio, sr = librosa.load(path, sr=sample_rate, mono=True)
    return audio


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak < 1e-6:
        return audio
    return audio / peak


def trim_silence(audio: np.ndarray, top_db: int = 25) -> np.ndarray:
    trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
    if len(trimmed) == 0:
        return audio
    return trimmed


def preprocess(audio: np.ndarray) -> np.ndarray:
    audio = normalize_audio(audio)
    audio = trim_silence(audio)
    audio = normalize_audio(audio)
    return audio


def split_into_words(audio: np.ndarray, sample_rate: int = SAMPLE_RATE,
                      top_db: int = 30, min_silence_ms: int = 150) -> list:
    intervals = librosa.effects.split(audio, top_db=top_db)
    min_silence_samples = int((min_silence_ms / 1000) * sample_rate)

    merged = []
    for start, end in intervals:
        if merged and start - merged[-1][1] < min_silence_samples:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    segments = [audio[s:e] for s, e in merged if e - s > 0]
    return segments if segments else [audio]

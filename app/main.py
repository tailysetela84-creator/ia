"""
main.py (FastAPI)
==================
Backend web da aplicação "Voz IA". Substitui o gui.py (Tkinter) por uma
API HTTP consumida por uma página web (app/static/index.html) que grava
o áudio no NAVEGADOR do utilizador e o envia para aqui.

Endpoints:
  GET  /                    -> serve a página principal
  GET  /api/words           -> lista as palavras aprendidas
  POST /api/teach           -> recebe (word, audio) e regista mais um exemplo
  POST /api/train           -> recalcula os protótipos a partir da BD
  POST /api/recognize       -> recebe áudio e devolve a palavra reconhecida
  POST /api/remove          -> remove uma palavra e os seus áudios
"""

import os
import shutil

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from . import database
from .audio_utils import decode_uploaded_audio, preprocess, split_into_words
from .recognizer import WordRecognizer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # voz_ia_web/
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title="Voz IA")
recognizer = WordRecognizer()


@app.on_event("startup")
def startup():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    database.init_db()
    recognizer.rebuild_from_database()
    print("✅ Backend pronto. Palavras carregadas da base de dados.")


# ----------------------------------------------------------------------
# Página principal (frontend estático)
# ----------------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------
@app.get("/api/words")
def list_words():
    return {"words": database.get_all_words()}


@app.post("/api/teach")
async def teach(word: str = Form(...), audio: UploadFile = File(...)):
    word = word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="Palavra vazia.")

    raw_bytes = await audio.read()
    try:
        audio_array = decode_uploaded_audio(raw_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não foi possível ler o áudio: {e}")

    audio_array = preprocess(audio_array)
    save_dir = os.path.join(AUDIO_DIR, word)

    recognizer.learn_word(word, [audio_array], save_dir)

    total = len(database.get_all_samples_with_embeddings().get(word, []))
    return {"status": "ok", "word": word, "total_samples": total}


@app.post("/api/train")
def train():
    recognizer.rebuild_from_database()
    return {"status": "ok", "n_words": len(recognizer.prototypes)}


@app.post("/api/recognize")
async def recognize(audio: UploadFile = File(...)):
    raw_bytes = await audio.read()
    try:
        audio_array = decode_uploaded_audio(raw_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não foi possível ler o áudio: {e}")

    audio_array = preprocess(audio_array)

    if not recognizer.prototypes:
        return {"results": [], "message": "Ainda não há palavras aprendidas."}

    results = recognizer.recognize_phrase(audio_array)
    return {
        "results": [
            {"word": word, "score": round(score, 3)} for word, score in results
        ]
    }


@app.post("/api/remove")
def remove(word: str = Form(...)):
    word = word.strip()
    audio_paths = database.remove_word(word)
    for path in audio_paths:
        if os.path.exists(path):
            os.remove(path)
    word_dir = os.path.join(AUDIO_DIR, word)
    if os.path.isdir(word_dir):
        shutil.rmtree(word_dir, ignore_errors=True)

    recognizer.rebuild_from_database()
    return {"status": "ok"}


# Serve ficheiros estáticos (CSS/JS) em /static/*
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

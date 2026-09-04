# 🧠 Voz IA — Versão Web

Versão da aplicação **Voz IA** adaptada para correr num servidor e ser
acedida por qualquer navegador (telemóvel ou computador).

## O que mudou em relação à versão desktop

| | Desktop (Tkinter) | Web (esta versão) |
|---|---|---|
| Interface | Janela Tkinter | Página HTML/JS no navegador |
| Gravação do microfone | `sounddevice` no PC local | `MediaRecorder` no navegador do utilizador |
| Onde corre o ML (Wav2Vec2) | No próprio PC | No servidor |
| Base de dados/áudios | Pasta local | Pasta no servidor (idealmente num volume persistente) |

O **núcleo de Machine Learning é o mesmo**: Wav2Vec2 para extrair
embeddings + classificador por protótipos (nearest-centroid) para
reconhecer/aprender palavras. Só a camada de interface e a forma de
capturar áudio mudaram.

## Estrutura

```
voz_ia_web/
├── Dockerfile
├── requirements.txt
├── DEPLOY.md              # guia passo-a-passo para publicar no Railway
├── data/                   # BD + áudios (persistir com volume em produção)
└── app/
    ├── main.py              # FastAPI: rotas /api/...
    ├── database.py
    ├── audio_utils.py        # agora descodifica áudio enviado pelo navegador
    ├── feature_extractor.py
    ├── recognizer.py
    └── static/
        ├── index.html
        ├── app.js             # grava o microfone e chama a API
        └── style.css
```

## Correr localmente

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre `http://localhost:8000` (o microfone funciona em `localhost` mesmo
sem HTTPS — só em produção precisas de HTTPS).

Precisas de ter o **ffmpeg** instalado no sistema (usado pelo `pydub` para
descodificar o áudio webm do navegador):

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# Mac
brew install ffmpeg
```

## Publicar online

Ver **[DEPLOY.md](./DEPLOY.md)** para o guia completo (Railway, passo a passo).

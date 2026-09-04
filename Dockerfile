# Imagem base leve com Python
FROM python:3.11-slim

# ffmpeg é necessário para o pydub descodificar o áudio webm enviado pelo navegador
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pasta onde a BD e os áudios ficam guardados.
# Num serviço com "volume persistente" (Railway/Render/VPS), este caminho
# deve ser montado como um volume para os dados sobreviverem a reinícios.
RUN mkdir -p /app/data/audio

# Plataformas como Railway/Render definem a variável PORT automaticamente;
# localmente usa 8000 por defeito.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

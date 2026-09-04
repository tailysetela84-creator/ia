# 🚀 Colocar o Voz IA online (Railway — opção mais simples)

Este guia assume que **não tens servidor próprio** e queres a via mais direta:
o [Railway](https://railway.app) constrói a imagem Docker automaticamente a
partir do teu repositório e dá-te um URL público com HTTPS (obrigatório para
o navegador aceder ao microfone).

## Pré-requisitos

- Uma conta no [GitHub](https://github.com) (grátis).
- Uma conta no [Railway](https://railway.app) (grátis para começar; usa cartão
  ou GitHub para login. Tem um plano gratuito com créditos limitados por mês
  e planos pagos a partir de poucos dólares/mês para uso contínuo).

## Passo 1 — Colocar o código no GitHub

```bash
cd voz_ia_web
git init
git add .
git commit -m "Voz IA - versão web"
```

Cria um repositório novo em https://github.com/new (pode ser privado),
depois:

```bash
git remote add origin https://github.com/<o-teu-utilizador>/voz-ia.git
git branch -M main
git push -u origin main
```

## Passo 2 — Criar o projeto no Railway

1. Entra em [railway.app](https://railway.app) e faz login com GitHub.
2. Clica em **"New Project"** → **"Deploy from GitHub repo"**.
3. Escolhe o repositório `voz-ia` que acabaste de criar.
4. O Railway deteta automaticamente o `Dockerfile` e começa a construir a
   imagem. Isto demora alguns minutos na primeira vez (por causa do `torch`).

## Passo 3 — Adicionar armazenamento persistente

Por defeito, os ficheiros criados dentro do contentor (a base de dados
`words.db` e os `.wav`) **desaparecem sempre que o serviço reinicia ou faz
novo deploy**. Para os manter:

1. Dentro do projeto no Railway, abre o serviço → separador **"Volumes"**.
2. Clica **"New Volume"**.
3. Define o *mount path* como: `/app/data`
4. Guarda. O Railway vai reiniciar o serviço com o volume ligado — a partir
   daqui, as palavras aprendidas sobrevivem a reinícios e novos deploys.

## Passo 4 — Gerar o domínio público

1. No serviço, vai a **"Settings" → "Networking"**.
2. Clica **"Generate Domain"**.
3. O Railway atribui automaticamente um URL público em HTTPS, por exemplo:
   `https://voz-ia-production.up.railway.app`

Abre esse URL no telemóvel ou computador — o navegador vai pedir permissão
para usar o microfone (só funciona em HTTPS, por isso é importante usar o
domínio do Railway e não `http://`).

## Passo 5 — Testar

1. Abre o URL gerado.
2. Clica **"➕ Ensinar nova palavra"**, escreve um nome, grava 5 exemplos.
3. Clica **"🎤 Gravar e reconhecer"** e diz a palavra.

## Notas importantes

- **Primeira gravação lenta:** a primeira vez que alguém ensina ou fala,
  o servidor descarrega o modelo Wav2Vec2 (~360MB) da Hugging Face Hub.
  Isso demora ~30-60s. Pedidos seguintes são rápidos porque o modelo fica em
  cache (mas só até o serviço reiniciar, a não ser que também guardes o cache
  do modelo no volume — ver "Melhorias" abaixo).
- **Custo:** o plano gratuito do Railway tem créditos mensais limitados;
  para uso contínuo (24/7) precisarás de um plano pago (a partir de ~$5/mês).
  Alternativa equivalente e igualmente simples: [Render](https://render.com)
  (o mesmo `Dockerfile` funciona lá, com o mesmo processo de "Deploy from
  GitHub" e volumes de disco pagos).
- **Recursos:** o Wav2Vec2 corre em CPU nestas plataformas (sem GPU no plano
  base). Para uma app pessoal com poucos utilizadores em simultâneo, é
  perfeitamente utilizável; para muitos utilizadores simultâneos, considera
  planos com mais CPU/RAM.
- **Segurança:** esta versão não tem autenticação — qualquer pessoa com o
  link pode ensinar/remover palavras. Se for para uso pessoal, considera
  adicionar uma password simples (posso ajudar a implementar isso se quiseres).

## Melhoria opcional: cache do modelo no volume

Para evitar descarregar o modelo Wav2Vec2 (~360MB) a cada novo deploy,
podes redirecionar a cache da Hugging Face para dentro do volume persistente,
adicionando esta variável de ambiente no Railway (separador "Variables"):

```
HF_HOME=/app/data/hf_cache
```

Assim, uma vez descarregado, o modelo fica guardado no volume e é
reaproveitado em reinícios futuros.

## Correr localmente antes de publicar (recomendado)

Testa sempre localmente primeiro:

```bash
cd voz_ia_web
docker build -t voz-ia .
docker run -p 8000:8000 -v $(pwd)/data:/app/data voz-ia
```

Abre `http://localhost:8000` no navegador (funciona em HTTP porque é
localhost — só em produção é que precisas de HTTPS).

Sem Docker, também podes correr diretamente:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

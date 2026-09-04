// app.js
// ======
// Lida com a gravação do microfone diretamente no navegador (MediaRecorder)
// e comunica com o backend FastAPI (endpoints /api/...).
//
// IMPORTANTE: navegadores só permitem acesso ao microfone (getUserMedia) em
// contexto seguro: HTTPS, ou http://localhost durante desenvolvimento.

const logBox = document.getElementById("log");

function log(msg) {
  const time = new Date().toLocaleTimeString();
  logBox.textContent += `[${time}] ${msg}\n`;
  logBox.scrollTop = logBox.scrollHeight;
}

/**
 * Grava `durationMs` milissegundos de áudio do microfone e devolve um Blob.
 */
async function recordAudio(durationMs) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks = [];

  return new Promise((resolve, reject) => {
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      resolve(new Blob(chunks, { type: "audio/webm" }));
    };
    recorder.onerror = reject;

    recorder.start();
    setTimeout(() => recorder.stop(), durationMs);
  });
}

async function postAudio(url, blob, extraFields = {}) {
  const form = new FormData();
  Object.entries(extraFields).forEach(([k, v]) => form.append(k, v));
  form.append("audio", blob, "audio.webm");

  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------
// 🎤 Falar
// ---------------------------------------------------------------------
document.getElementById("btnFalar").addEventListener("click", async () => {
  const out = document.getElementById("resultadoFalar");
  try {
    log("🎤 A gravar 3s... fale agora.");
    const blob = await recordAudio(3000);
    log("⏳ A enviar áudio e a reconhecer...");
    const data = await postAudio("/api/recognize", blob);

    if (!data.results || data.results.length === 0) {
      out.textContent = data.message || "Nenhum som detetado.";
      return;
    }
    out.innerHTML = data.results
      .map((r) =>
        r.word
          ? `✅ ${r.word} (confiança: ${r.score})`
          : `❓ não reconhecido (confiança: ${r.score})`
      )
      .join("<br>");
    log("✅ Reconhecimento concluído.");
  } catch (err) {
    log("❌ Erro: " + err.message);
    out.textContent = "Erro ao reconhecer: " + err.message;
  }
});

// ---------------------------------------------------------------------
// ➕ Ensinar nova palavra
// ---------------------------------------------------------------------
document.getElementById("btnEnsinar").addEventListener("click", async () => {
  const word = document.getElementById("inputPalavra").value.trim();
  const out = document.getElementById("resultadoEnsinar");
  if (!word) {
    out.textContent = "Escreve o nome da palavra primeiro.";
    return;
  }
  try {
    log(`🎤 A gravar exemplo de "${word}" (2s)...`);
    const blob = await recordAudio(2000);
    log("⏳ A processar exemplo com Wav2Vec2...");
    const data = await postAudio("/api/teach", blob, { word });
    out.textContent = `📚 "${data.word}" agora tem ${data.total_samples} exemplo(s). Grava mais alguns para melhor precisão (recomendado: 5).`;
    log(`✅ Exemplo de "${word}" registado.`);
  } catch (err) {
    log("❌ Erro: " + err.message);
    out.textContent = "Erro ao ensinar: " + err.message;
  }
});

// ---------------------------------------------------------------------
// 📚 Palavras aprendidas
// ---------------------------------------------------------------------
async function carregarPalavras() {
  const lista = document.getElementById("listaPalavras");
  lista.innerHTML = "";
  const res = await fetch("/api/words");
  const data = await res.json();
  if (data.words.length === 0) {
    lista.innerHTML = "<li>(nenhuma palavra ainda)</li>";
    return;
  }
  data.words.forEach((w) => {
    const li = document.createElement("li");
    li.textContent = `${w.name} — ${w.n_samples} exemplo(s)`;
    lista.appendChild(li);
  });
}
document.getElementById("btnListar").addEventListener("click", carregarPalavras);

// ---------------------------------------------------------------------
// 🧠 Treinar/Atualizar modelo
// ---------------------------------------------------------------------
document.getElementById("btnTreinar").addEventListener("click", async () => {
  const out = document.getElementById("resultadoTreinar");
  try {
    log("🧠 A recalcular protótipos...");
    const res = await fetch("/api/train", { method: "POST" });
    const data = await res.json();
    out.textContent = `✅ Modelo atualizado (${data.n_words} palavra(s)).`;
    log("✅ Modelo atualizado.");
  } catch (err) {
    log("❌ Erro: " + err.message);
  }
});

// ---------------------------------------------------------------------
// 🗑️ Remover palavra
// ---------------------------------------------------------------------
document.getElementById("btnRemover").addEventListener("click", async () => {
  const word = document.getElementById("inputRemover").value.trim();
  const out = document.getElementById("resultadoRemover");
  if (!word) return;
  if (!confirm(`Remover "${word}" e todos os seus áudios?`)) return;

  try {
    const form = new FormData();
    form.append("word", word);
    const res = await fetch("/api/remove", { method: "POST", body: form });
    await res.json();
    out.textContent = `🗑️ "${word}" removida.`;
    log(`🗑️ Palavra removida: ${word}`);
    carregarPalavras();
  } catch (err) {
    log("❌ Erro: " + err.message);
  }
});

// Carrega a lista de palavras ao abrir a página
carregarPalavras();

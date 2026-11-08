(() => {
  const API = window.API || "http://127.0.0.1:8000";
  const languages = {
    fr: { speech: "fr-FR", title: "Assistant Nexa", placeholder: "Écrivez ou dictez votre question…" },
    en: { speech: "en-US", title: "Nexa Assistant", placeholder: "Type or dictate your question…" },
    ar: { speech: "ar-SA", title: "مساعد نيكسـا", placeholder: "اكتب سؤالك أو أمْلِه…" }
  };

  const savedLanguage = (localStorage.getItem("nexa_language") || "fr").slice(0, 2);
  const language = languages[savedLanguage] ? savedLanguage : "fr";
  const text = languages[language];

  const button = document.createElement("button");
  button.type = "button";
  button.textContent = `✦ ${text.title}`;
  button.style.cssText =
    "position:fixed;right:20px;bottom:20px;z-index:9999;padding:12px 16px;border:0;border-radius:24px;background:#165dce;color:white;cursor:pointer";

  const panel = document.createElement("section");
  panel.hidden = true;
  panel.style.cssText =
    "position:fixed;right:20px;bottom:75px;z-index:9999;width:min(380px,calc(100vw - 40px));padding:16px;background:white;border:1px solid #ddd;border-radius:12px;box-shadow:0 5px 25px #0002";

  panel.innerHTML = `
    <div id="assistant-messages" aria-live="polite"
         style="height:260px;overflow:auto;margin-bottom:12px"></div>
    <input id="assistant-input" maxlength="2000"
           style="width:60%;padding:8px">
    <button id="assistant-send" type="button">Envoyer</button>
    <button id="assistant-mic" type="button" aria-label="Microphone">🎙</button>
    <label style="display:block;margin-top:10px">
      <input id="assistant-speak" type="checkbox"> Lire la réponse à voix haute
    </label>
  `;

  document.body.append(button, panel);

  const input = panel.querySelector("#assistant-input");
  const messages = panel.querySelector("#assistant-messages");
  const status = document.createElement("p");
  status.setAttribute("role", "status");
  panel.append(status);
  input.placeholder = text.placeholder;

  function addMessage(content, role) {
    const item = document.createElement("p");
    item.textContent = content;
    item.style.cssText = "padding:8px;border-radius:8px;background:" +
      (role === "user" ? "#e5efff" : "#f1f5f9");
    messages.append(item);
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendQuestion(question) {
    const prompt = question.trim();
    if (!prompt) return;

    addMessage(prompt, "user");
    status.textContent = "…";

    const token = sessionStorage.getItem("access_token") ||
                  localStorage.getItem("access_token");
    if (!token || token.startsWith("demo_")) {
      status.textContent = "Connectez-vous pour utiliser l’assistant.";
      return;
    }

    try {
      const response = await fetch(`${API}/ai/query`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt, language })
      });

      if (!response.ok) throw new Error(`Erreur API : ${response.status}`);

      const data = await response.json();
      const answer = data.answer || "Aucune réponse reçue.";
      addMessage(answer, "assistant");
      status.textContent = "";

      if (panel.querySelector("#assistant-speak").checked &&
          "speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(answer);
        utterance.lang = text.speech;
        window.speechSynthesis.speak(utterance);
      }
    } catch (error) {
      console.error(error);
      status.textContent = "Impossible de joindre l’assistant.";
    }
  }

  button.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) input.focus();
  });

  panel.querySelector("#assistant-send").addEventListener("click", () => {
    const question = input.value;
    input.value = "";
    sendQuestion(question);
  });

  input.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      const question = input.value;
      input.value = "";
      sendQuestion(question);
    }
  });

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = panel.querySelector("#assistant-mic");

  if (!SpeechRecognition) {
    mic.disabled = true;
    mic.title = "La reconnaissance vocale n’est pas disponible dans ce navigateur.";
  } else {
    mic.addEventListener("click", () => {
      if (!window.isSecureContext &&
          location.hostname !== "localhost" &&
          location.hostname !== "127.0.0.1") {
        status.textContent = "Le microphone nécessite HTTPS ou localhost.";
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.lang = text.speech;
      recognition.interimResults = false;
      recognition.onresult = event => {
        const question = event.results[0][0].transcript;
        input.value = question;
        sendQuestion(question);
      };
      recognition.onerror = () => {
        status.textContent = "Erreur de reconnaissance vocale.";
      };
      recognition.start();
    });
  }
})();
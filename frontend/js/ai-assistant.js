(() => {
  "use strict";

  function initAssistant() {
    // Évite d’ajouter l’assistant deux fois si le script est chargé en double.
    if (document.getElementById("nexa-ai-launcher")) return;

    const API = window.API || "http://127.0.0.1:8000";

    const savedLanguage = (
      localStorage.getItem("nexa_language") ||
      document.documentElement.lang ||
      "fr"
    ).slice(0, 2).toLowerCase();

    const language = ["fr", "en", "ar"].includes(savedLanguage)
      ? savedLanguage
      : "fr";

    const settings = {
      fr: {
        title: "Assistant Nexa",
        open: "Assistant IA",
        close: "Fermer",
        placeholder: "Écrivez ou dictez votre question…",
        send: "Envoyer",
        listen: "Parler",
        stop: "Arrêter l’écoute",
        readAloud: "Lire la réponse à voix haute",
        welcome: "Bonjour ! Posez une question par écrit ou utilisez le microphone.",
        thinking: "Je recherche une réponse…",
        login: "Connectez-vous pour utiliser l’assistant.",
        empty: "Écrivez ou dictez une question avant de l’envoyer.",
        error: "Impossible de joindre l’assistant. Vérifiez la connexion et réessayez.",
        microphoneUnavailable: "La reconnaissance vocale n’est pas disponible dans ce navigateur.",
        microphoneSecure: "Le microphone nécessite une connexion HTTPS ou localhost.",
        navigation: "Ouverture du module."
      },
      en: {
        title: "Nexa Assistant",
        open: "AI Assistant",
        close: "Close",
        placeholder: "Type or dictate your question…",
        send: "Send",
        listen: "Speak",
        stop: "Stop listening",
        readAloud: "Read the answer aloud",
        welcome: "Hello! Type a question or use the microphone.",
        thinking: "Looking for an answer…",
        login: "Sign in to use the assistant.",
        empty: "Type or dictate a question before sending.",
        error: "Could not reach the assistant. Check your connection and try again.",
        microphoneUnavailable: "Speech recognition is unavailable in this browser.",
        microphoneSecure: "Microphone access requires HTTPS or localhost.",
        navigation: "Opening the module."
      },
      ar: {
        title: "مساعد نيكسـا",
        open: "المساعد الذكي",
        close: "إغلاق",
        placeholder: "اكتب سؤالك أو أمْلِه…",
        send: "إرسال",
        listen: "تحدث",
        stop: "إيقاف الاستماع",
        readAloud: "قراءة الإجابة بصوت عالٍ",
        welcome: "مرحباً! اكتب سؤالك أو استخدم الميكروفون.",
        thinking: "جارٍ البحث عن إجابة…",
        login: "سجّل الدخول لاستخدام المساعد.",
        empty: "اكتب سؤالك أو أمْلِه قبل الإرسال.",
        error: "تعذر الاتصال بالمساعد. تحقق من الاتصال وحاول مجدداً.",
        microphoneUnavailable: "التعرّف على الكلام غير متاح في هذا المتصفح.",
        microphoneSecure: "يتطلب استخدام الميكروفون اتصالاً آمناً HTTPS أو localhost.",
        navigation: "جارٍ فتح الوحدة."
      }
    }[language];

    const speechLocale = {
      fr: "fr-FR",
      en: "en-US",
      ar: "ar-SA"
    }[language];

    const routes = [
      { terms: ["tableau de bord", "dashboard", "الرئيسية"], href: "dashboard.html" },
      { terms: ["facture", "invoice", "الفواتير"], href: "factures.html" },
      { terms: ["produit", "product", "المنتجات"], href: "produit.html" },
      { terms: ["client", "customer", "العملاء"], href: "clients.html" },
      { terms: ["achat", "purchase", "المشتريات"], href: "achats.html" },
      { terms: ["trésorerie", "treasury", "الخزينة"], href: "tresorerie.html" },
      { terms: ["stock", "warehouse", "المخزون"], href: "stock.html" },
      { terms: ["utilisateur", "user", "المستخدمين"], href: "utilisateurs.html" },
      { terms: ["sécurité", "security", "الأمان"], href: "securite.html" },
      { terms: ["société", "company", "الشركة"], href: "societe.html" }
    ];

    const style = document.createElement("style");
    style.textContent = `
      #nexa-ai-launcher {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 10000;
        border: 0;
        border-radius: 999px;
        padding: 14px 18px;
        background: #165dce;
        color: #fff;
        font: 600 15px system-ui, sans-serif;
        box-shadow: 0 6px 24px #0f172a33;
        cursor: pointer;
      }

      #nexa-ai-panel {
        position: fixed;
        right: 24px;
        bottom: 86px;
        z-index: 10001;
        display: none;
        flex-direction: column;
        width: min(390px, calc(100vw - 32px));
        height: min(560px, calc(100vh - 120px));
        overflow: hidden;
        border: 1px solid #dbe3ef;
        border-radius: 16px;
        background: #fff;
        color: #172033;
        box-shadow: 0 16px 48px #0f172a33;
        font: 14px system-ui, sans-serif;
      }

      #nexa-ai-panel.open {
        display: flex;
      }

      #nexa-ai-panel[dir="rtl"] {
        right: auto;
        left: 24px;
      }

      #nexa-ai-panel header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        background: #165dce;
        color: #fff;
      }

      #nexa-ai-panel header button {
        border: 0;
        background: transparent;
        color: inherit;
        font-size: 20px;
        cursor: pointer;
      }

      #nexa-ai-messages {
        display: flex;
        flex: 1;
        flex-direction: column;
        gap: 10px;
        overflow: auto;
        padding: 14px;
      }

      .nexa-ai-message {
        max-width: 90%;
        padding: 10px 12px;
        border-radius: 12px;
        line-height: 1.45;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
      }

      .nexa-ai-message.assistant {
        align-self: flex-start;
        background: #f1f5f9;
      }

      .nexa-ai-message.user {
        align-self: flex-end;
        background: #e5efff;
      }

      #nexa-ai-status {
        min-height: 20px;
        padding: 0 14px;
        color: #526174;
        font-size: 12px;
      }

      #nexa-ai-speak-label {
        display: flex;
        gap: 7px;
        align-items: center;
        padding: 0 14px 10px;
        color: #526174;
        font-size: 12px;
      }

      #nexa-ai-controls {
        display: flex;
        gap: 8px;
        padding: 12px;
        border-top: 1px solid #e5eaf1;
      }

      #nexa-ai-input {
        flex: 1;
        min-width: 0;
        padding: 10px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        font: inherit;
      }

      #nexa-ai-controls button {
        padding: 9px 11px;
        border: 0;
        border-radius: 8px;
        background: #165dce;
        color: #fff;
        cursor: pointer;
      }

      #nexa-ai-controls button:disabled {
        opacity: .55;
        cursor: not-allowed;
      }

      @media (max-width: 520px) {
        #nexa-ai-launcher {
          right: 14px;
          bottom: 14px;
        }

        #nexa-ai-panel {
          right: 8px;
          bottom: 72px;
          width: calc(100vw - 16px);
        }

        #nexa-ai-panel[dir="rtl"] {
          right: auto;
          left: 8px;
        }
      }
    `;

    document.head.appendChild(style);

    const launcher = document.createElement("button");
    launcher.id = "nexa-ai-launcher";
    launcher.type = "button";
    launcher.textContent = `✦ ${settings.open}`;
    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-controls", "nexa-ai-panel");

    const panel = document.createElement("section");
    panel.id = "nexa-ai-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", settings.title);
    panel.dir = language === "ar" ? "rtl" : "ltr";

    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = settings.title;

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.textContent = "×";
    closeButton.setAttribute("aria-label", settings.close);
    header.append(title, closeButton);

    const messages = document.createElement("div");
    messages.id = "nexa-ai-messages";
    messages.setAttribute("aria-live", "polite");

    const speakLabel = document.createElement("label");
    speakLabel.id = "nexa-ai-speak-label";
    const speakToggle = document.createElement("input");
    speakToggle.type = "checkbox";
    speakToggle.id = "nexa-ai-speak";
    speakLabel.append(speakToggle, document.createTextNode(settings.readAloud));

    const status = document.createElement("div");
    status.id = "nexa-ai-status";
    status.setAttribute("role", "status");

    const controls = document.createElement("div");
    controls.id = "nexa-ai-controls";

    const input = document.createElement("input");
    input.id = "nexa-ai-input";
    input.type = "text";
    input.maxLength = 2000;
    input.autocomplete = "off";
    input.placeholder = settings.placeholder;
    input.setAttribute("aria-label", settings.placeholder);

    const sendButton = document.createElement("button");
    sendButton.id = "nexa-ai-send";
    sendButton.type = "button";
    sendButton.textContent = settings.send;

    const micButton = document.createElement("button");
    micButton.id = "nexa-ai-mic";
    micButton.type = "button";
    micButton.textContent = "🎙";
    micButton.title = settings.listen;
    micButton.setAttribute("aria-label", settings.listen);

    controls.append(input, sendButton, micButton);
    panel.append(header, messages, speakLabel, status, controls);
    document.body.append(launcher, panel);

    function addMessage(content, role) {
      const message = document.createElement("div");
      message.className = `nexa-ai-message ${role}`;
      message.textContent = content;
      messages.appendChild(message);
      messages.scrollTop = messages.scrollHeight;
    }

    function speak(content) {
      if (!("speechSynthesis" in window) || !content) return;

      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(content);
      utterance.lang = speechLocale;
      window.speechSynthesis.speak(utterance);
    }

    function navigateIfRequested(prompt) {
  const normalized = prompt.toLocaleLowerCase(language).trim();
  const command = normalized.match(
    /^(ouvre|ouvrir|va à|aller à|open|go to)\s+(.+?)[.!?]*$/i
  );

  // Une question ou une phrase complète reste une question pour l'assistant.
  if (!command) return false;

  const target = command[2].trim();
  const route = routes.find(item =>
    item.terms.some(term => target === term)
  );

  if (!route) return false;

  addMessage(settings.navigation, "assistant");
  window.location.assign(route.href);
  return true;
}
    // Historique de la conversation en cours.
    const conversationHistory = [];
    async function sendQuestion(question) {
      const prompt = question.trim();

      if (!prompt) {
        status.textContent = settings.empty;
        return;
      }

      if (navigateIfRequested(prompt)) {
        input.value = "";
        return;
      }

      const token =
        sessionStorage.getItem("access_token") ||
        localStorage.getItem("access_token");

      if (!token || token.startsWith("demo_")) {
        status.textContent = settings.login;
        return;
      }

      addMessage(prompt, "user");
      input.value = "";
      status.textContent = settings.thinking;
      sendButton.disabled = true;

      try {
        const response = await fetch(`${API}/ai/query`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            prompt,
            language,
            history: conversationHistory.slice(-12)
          })
        });

        if (!response.ok) {
          throw new Error(`Assistant API returned ${response.status}`);
        }

        const data = await response.json();
        const answer =
          typeof data.answer === "string" && data.answer.trim()
            ? data.answer
            : settings.error;

        addMessage(answer, "assistant");
        // Mémoriser les deux derniers échanges.
conversationHistory.push(
    {
        role: "user",
        content: prompt
    },
    {
        role: "assistant",
        content: answer
    }
);

// Limiter la mémoire aux 12 derniers messages.
if (conversationHistory.length > 12) {
    conversationHistory.splice(
        0,
        conversationHistory.length - 12
    );
}
        status.textContent = "";

        if (speakToggle.checked) {
          speak(answer);
        }
      } catch (error) {
        console.error("Erreur de l’assistant Nexa :", error);
        status.textContent = settings.error;
      } finally {
        sendButton.disabled = false;
      }
    }

    let welcomed = false;

    launcher.addEventListener("click", () => {
      const isOpening = !panel.classList.contains("open");
      panel.classList.toggle("open", isOpening);
      launcher.setAttribute("aria-expanded", String(isOpening));

      if (isOpening) {
        if (!welcomed) {
          addMessage(settings.welcome, "assistant");
          welcomed = true;
        }
        input.focus();
      }
    });

    closeButton.addEventListener("click", () => {
      panel.classList.remove("open");
      launcher.setAttribute("aria-expanded", "false");
    });

    sendButton.addEventListener("click", () => {
      sendQuestion(input.value);
    });

    input.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendQuestion(input.value);
      }
    });

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      micButton.disabled = true;
      micButton.title = settings.microphoneUnavailable;
    } else {
      const recognition = new SpeechRecognition();
      let isListening = false;

      recognition.lang = speechLocale;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        isListening = true;
        micButton.textContent = "■";
        micButton.title = settings.stop;
      };

      recognition.onend = () => {
        isListening = false;
        micButton.textContent = "🎙";
        micButton.title = settings.listen;
      };

      recognition.onerror = event => {
        status.textContent =
          event.error === "not-allowed"
            ? settings.microphoneSecure
            : settings.microphoneUnavailable;
      };

      recognition.onresult = event => {
        const transcript = event.results?.[0]?.[0]?.transcript;
        if (transcript) {
          input.value = transcript;
          sendQuestion(transcript);
        }
      };

      micButton.addEventListener("click", () => {
        if (!window.isSecureContext &&
            location.hostname !== "localhost" &&
            location.hostname !== "127.0.0.1") {
          status.textContent = settings.microphoneSecure;
          return;
        }

        try {
          if (isListening) {
            recognition.stop();
          } else {
            recognition.start();
          }
        } catch (error) {
          console.error("Erreur du microphone :", error);
          status.textContent = settings.microphoneUnavailable;
        }
      });
    }
  }

  // Fonctionne même si le script est déplacé dans le <head>.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAssistant, { once: true });
  } else {
    initAssistant();
  }
})();
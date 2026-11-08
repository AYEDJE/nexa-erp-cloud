HEAD
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
/* NexaERP voice assistant: browser speech APIs + existing /ai/query endpoint. */
(() => {
  'use strict';

  const API = window.API || 'http://127.0.0.1:8000';
  const locale = (() => {
    const value = (localStorage.getItem('nexa_language') || document.documentElement.lang || 'fr').toLowerCase();
    return value.startsWith('ar') ? 'ar' : value.startsWith('en') ? 'en' : 'fr';
  })();
  const copy = {
    fr: { title: 'Assistant Nexa', open: 'Ouvrir l’assistant', close: 'Fermer', input: 'Écrivez votre question…', send: 'Envoyer', listen: 'Parler', stop: 'Arrêter l’écoute', speak: 'Lire les réponses à voix haute', welcome: 'Bonjour ! Posez une question par écrit ou utilisez le microphone.', micUnsupported: 'La reconnaissance vocale n’est pas disponible dans ce navigateur. Vous pouvez continuer par écrit.', micSecure: 'Le microphone nécessite une connexion sécurisée (HTTPS ou localhost).', thinking: 'Je recherche une réponse…', error: 'Impossible de joindre l’assistant. Vérifiez votre connexion et réessayez.', empty: 'Écrivez ou dictez une question avant de l’envoyer.', nav: 'Ouverture du module.' },
    en: { title: 'Nexa Assistant', open: 'Open assistant', close: 'Close', input: 'Type your question…', send: 'Send', listen: 'Speak', stop: 'Stop listening', speak: 'Read answers aloud', welcome: 'Hello! Ask a question by typing or use the microphone.', micUnsupported: 'Speech recognition is unavailable in this browser. You can continue by typing.', micSecure: 'Microphone access requires a secure connection (HTTPS or localhost).', thinking: 'Looking for an answer…', error: 'Could not reach the assistant. Check your connection and try again.', empty: 'Type or dictate a question before sending.', nav: 'Opening the module.' },
    ar: { title: 'مساعد نيكسـا', open: 'فتح المساعد', close: 'إغلاق', input: 'اكتب سؤالك…', send: 'إرسال', listen: 'تحدث', stop: 'إيقاف الاستماع', speak: 'قراءة الإجابات بصوت عالٍ', welcome: 'مرحباً! اطرح سؤالك كتابةً أو استخدم الميكروفون.', micUnsupported: 'التعرّف على الكلام غير متاح في هذا المتصفح. يمكنك المتابعة بالكتابة.', micSecure: 'يتطلب استخدام الميكروفون اتصالاً آمناً (HTTPS أو localhost).', thinking: 'جارٍ البحث عن إجابة…', error: 'تعذر الاتصال بالمساعد. تحقق من الاتصال وحاول مجدداً.', empty: 'اكتب سؤالك أو أمْلِه قبل الإرسال.', nav: 'جارٍ فتح الوحدة.' }
  }[locale];
  const speechLocale = { fr: 'fr-FR', en: 'en-US', ar: 'ar-SA' }[locale];
  const routes = [
    { terms: ['dashboard', 'tableau de bord', 'الرئيسية'], href: 'dashboard.html' },
    { terms: ['facture', 'invoice', 'الفواتير'], href: 'factures.html' },
    { terms: ['produit', 'product', 'المنتجات'], href: 'produit.html' },
    { terms: ['client', 'customer', 'العملاء'], href: 'clients.html' },
    { terms: ['achat', 'purchase', 'المشتريات'], href: 'achats.html' },
    { terms: ['trésorerie', 'treasury', 'الخزينة'], href: 'tresorerie.html' },
    { terms: ['stock', 'warehouse', 'المخزون'], href: 'stock.html' },
    { terms: ['utilisateur', 'user', 'المستخدمين'], href: 'utilisateurs.html' },
    { terms: ['sécurité', 'security', 'الأمان'], href: 'securite.html' },
    { terms: ['société', 'company', 'الشركة'], href: 'societe.html' }
  ];

  const style = document.createElement('style');
  style.textContent = `
    #nexa-ai-launcher{position:fixed;right:24px;bottom:24px;z-index:10000;border:0;border-radius:999px;background:#165dce;color:white;padding:14px 18px;font:600 15px system-ui;box-shadow:0 6px 24px #0f172a33;cursor:pointer}
    #nexa-ai-panel{position:fixed;right:24px;bottom:86px;z-index:10001;width:min(390px,calc(100vw - 32px));height:min(560px,calc(100vh - 120px));display:none;flex-direction:column;background:#fff;color:#172033;border:1px solid #dbe3ef;border-radius:16px;box-shadow:0 16px 48px #0f172a33;font:14px system-ui;overflow:hidden}
    #nexa-ai-panel[dir=rtl]{right:auto;left:24px} #nexa-ai-panel.open{display:flex}
    #nexa-ai-panel header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:#165dce;color:#fff}
    #nexa-ai-panel button{cursor:pointer} #nexa-ai-panel header button{border:0;background:transparent;color:inherit;font-size:20px}
    #nexa-ai-messages{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
    .nexa-ai-message{max-width:90%;padding:10px 12px;border-radius:12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.45}
    .nexa-ai-message.assistant{background:#f1f5f9;align-self:flex-start}.nexa-ai-message.user{background:#e5efff;align-self:flex-end}
    #nexa-ai-status{min-height:20px;padding:0 14px;color:#526174;font-size:12px}
    #nexa-ai-controls{display:flex;gap:8px;padding:12px;border-top:1px solid #e5eaf1}
    #nexa-ai-input{min-width:0;flex:1;padding:10px;border:1px solid #cbd5e1;border-radius:8px;font:inherit}
    #nexa-ai-controls button{border:0;border-radius:8px;padding:9px 11px;background:#165dce;color:#fff}
    #nexa-ai-controls button[disabled]{opacity:.55;cursor:not-allowed}
    @media(max-width:520px){#nexa-ai-launcher{right:14px;bottom:14px}#nexa-ai-panel{right:8px;bottom:72px;width:calc(100vw - 16px)}#nexa-ai-panel[dir=rtl]{left:8px}}
  `;
  document.head.appendChild(style);

  const launcher = document.createElement('button');
  launcher.id = 'nexa-ai-launcher'; launcher.type = 'button'; launcher.textContent = `✦ ${copy.open}`;
  launcher.setAttribute('aria-expanded', 'false'); launcher.setAttribute('aria-controls', 'nexa-ai-panel');
  const panel = document.createElement('section');
  panel.id = 'nexa-ai-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', copy.title); panel.dir = locale === 'ar' ? 'rtl' : 'ltr';
  panel.innerHTML = `<header><strong></strong><button type="button" aria-label="${copy.close}">×</button></header><div id="nexa-ai-messages" aria-live="polite"></div><div id="nexa-ai-status" role="status"></div><div id="nexa-ai-controls"><input id="nexa-ai-input" maxlength="2000" autocomplete="off"><button id="nexa-ai-send" type="button"></button><button id="nexa-ai-mic" type="button" aria-label="${copy.listen}">🎙</button></div>`;
  panel.querySelector('strong').textContent = copy.title;
  const input = panel.querySelector('#nexa-ai-input'); input.placeholder = copy.input; input.setAttribute('aria-label', copy.input);
  const send = panel.querySelector('#nexa-ai-send'); send.textContent = copy.send;
  const mic = panel.querySelector('#nexa-ai-mic'); mic.title = copy.listen;
  const messages = panel.querySelector('#nexa-ai-messages');
  const status = panel.querySelector('#nexa-ai-status');
  document.body.append(launcher, panel);

  const addMessage = (text, who) => {
    const bubble = document.createElement('div'); bubble.className = `nexa-ai-message ${who}`; bubble.textContent = text;
    messages.appendChild(bubble); messages.scrollTop = messages.scrollHeight;
  };
  const speak = text => {
    if (!window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text); utterance.lang = speechLocale;
    window.speechSynthesis.speak(utterance);
  };
  const navigateIfRequested = text => {
    const normalized = text.toLocaleLowerCase(locale);
    const openIntent = /\b(ouvre|ouvrir|va à|aller à|open|go to)\b|افتح|اذهب إلى/i.test(normalized);
    if (!openIntent) return false;
    const route = routes.find(item => item.terms.some(term => normalized.includes(term)));
    if (!route) return false;
    addMessage(copy.nav, 'assistant');
    window.location.assign(route.href);
    return true;
  };
  const ask = async () => {
    const prompt = input.value.trim();
    if (!prompt) { status.textContent = copy.empty; return; }
    if (navigateIfRequested(prompt)) { input.value = ''; return; }
    input.value = ''; addMessage(prompt, 'user'); status.textContent = copy.thinking; send.disabled = true;
    try {
      const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
      if (!token || token.startsWith('demo_')) throw new Error('Authenticated API session required');
      const response = await fetch(`${API}/ai/query`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, language: locale })
      });
      if (!response.ok) throw new Error(`Assistant request failed (${response.status})`);
      const data = await response.json();
      const answer = typeof data.answer === 'string' ? data.answer : copy.error;
      addMessage(answer, 'assistant');
      const readAloud = panel.querySelector('#nexa-ai-speak')?.checked;
      if (readAloud) speak(answer);
      status.textContent = '';
    } catch (error) {
      console.error('Nexa assistant error:', error); status.textContent = copy.error;
    } finally { send.disabled = false; }
  };
  const speechApi = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  if (!speechApi) { mic.disabled = true; mic.title = copy.micUnsupported; }
  else {
    recognition = new speechApi(); recognition.lang = speechLocale; recognition.interimResults = false; recognition.maxAlternatives = 1;
    recognition.onstart = () => { mic.textContent = '■'; mic.title = copy.stop; };
    recognition.onend = () => { mic.textContent = '🎙'; mic.title = copy.listen; };
    recognition.onerror = event => { status.textContent = event.error === 'not-allowed' ? copy.micSecure : copy.micUnsupported; };
    recognition.onresult = event => { input.value = event.results[0][0].transcript; ask(); };
  }
  const speakLabel = document.createElement('label'); speakLabel.style.cssText = 'padding:0 14px 10px;display:flex;gap:7px;align-items:center;font-size:12px;color:#526174';
  const speakToggle = document.createElement('input'); speakToggle.id = 'nexa-ai-speak'; speakToggle.type = 'checkbox';
  speakLabel.append(speakToggle, document.createTextNode(copy.speak));
  panel.insertBefore(speakLabel, status);
  launcher.addEventListener('click', () => {
    const opening = !panel.classList.contains('open'); panel.classList.toggle('open', opening);
    launcher.setAttribute('aria-expanded', String(opening)); if (opening) { addWelcomeOnce(); input.focus(); }
  });
  let welcomed = false;
  function addWelcomeOnce() { if (!welcomed) { addMessage(copy.welcome, 'assistant'); welcomed = true; } }
  panel.querySelector('header button').addEventListener('click', () => { panel.classList.remove('open'); launcher.setAttribute('aria-expanded', 'false'); });
  send.addEventListener('click', ask);
  input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); ask(); } });
  mic.addEventListener('click', () => {
    if (!recognition) { status.textContent = copy.micUnsupported; return; }
    if (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') { status.textContent = copy.micSecure; return; }
    try { recognition.start(); } catch (_) { recognition.stop(); }
  });
})();

(() => {
  "use strict";

  const API = window.API || window.location.origin;
  const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");

  const $ = (id) => document.getElementById(id);
  let currentRoom = null;
  let socket = null;
  const seenMessages = new Set();

  function setStatus(message) {
    $("status").textContent = message || "";
  }

  function authHeaders(json = false) {
    const headers = { Authorization: `Bearer ${token}` };
    if (json) headers["Content-Type"] = "application/json";
    return headers;
  }

  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...authHeaders(!(options.body instanceof FormData)), ...(options.headers || {}) }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Erreur API (${response.status})`);
    }
    return data;
  }

  function appendMessage(message) {
    if (seenMessages.has(message.id)) return;
    seenMessages.add(message.id);

    const row = document.createElement("div");
    row.className = "message";
    row.textContent = `${message.user_id} · ${new Date(message.created_at).toLocaleString()} — ${message.content}`;
    $("messages").appendChild(row);
    $("messages").scrollTop = $("messages").scrollHeight;
  }

  function closeSocket() {
    if (socket) {
      socket.close();
      socket = null;
    }
  }

  function connectSocket(roomId) {
    closeSocket();

    const wsBase = API.replace(/^http:/, "ws:").replace(/^https:/, "wss:");
    socket = new WebSocket(`${wsBase}/rooms/${roomId}/live`);

    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({ token }));
    });

    socket.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "message") appendMessage(data.message);
        if (data.type === "presence") {
          $("presence").textContent = ` · ${data.user_ids.length} en ligne`;
        }
      } catch (error) {
        console.warn("Événement Room Live invalide", error);
      }
    });

    socket.addEventListener("close", () => {
      $("presence").textContent = "";
    });
  }

  async function loadRooms() {
    const rooms = await api("/rooms");
    const list = $("room-list");
    list.replaceChildren();

    rooms.forEach((room) => {
      const button = document.createElement("button");
      button.className = "room-button";
      button.type = "button";
      button.textContent = room.name;
      button.addEventListener("click", () => selectRoom(room));
      list.appendChild(button);
    });
  }

  async function loadFiles() {
    const files = await api(`/rooms/${currentRoom.id}/files`);
    const list = $("file-list");
    list.replaceChildren();

    files.forEach((file) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.className = "secondary";
      button.textContent = `Télécharger ${file.original_name}`;

      button.addEventListener("click", async () => {
        try {
          const response = await fetch(
            `${API}/rooms/${currentRoom.id}/files/${file.id}/download`,
            { headers: authHeaders(false) }
          );
          if (!response.ok) throw new Error("Téléchargement impossible.");
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = file.original_name;
          link.click();
          URL.revokeObjectURL(url);
        } catch (error) {
          setStatus(error.message);
        }
      });

      item.appendChild(button);
      list.appendChild(item);
    });
  }

  async function loadActivities() {
    const activities = await api(`/rooms/${currentRoom.id}/activities?limit=20`);
    const list = $("activity-list");
    list.replaceChildren();

    activities.forEach((activity) => {
      const item = document.createElement("li");
      item.textContent = `${new Date(activity.created_at).toLocaleString()} — ${activity.kind}`;
      list.appendChild(item);
    });
  }

  async function selectRoom(room) {
    currentRoom = room;
    seenMessages.clear();
    $("room-title").textContent = room.name;
    $("room-tools").hidden = false;
    $("messages").replaceChildren();
    setStatus("");

    try {
      const messages = await api(`/rooms/${room.id}/messages?limit=50`);
      messages.forEach(appendMessage);
      await Promise.all([loadFiles(), loadActivities()]);
      connectSocket(room.id);
    } catch (error) {
      setStatus(error.message);
    }
  }

  $("create-room").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const room = await api("/rooms", {
        method: "POST",
        body: JSON.stringify({
          name: $("room-name").value.trim(),
          description: $("room-description").value.trim() || null
        })
      });
      $("create-room").reset();
      await loadRooms();
      await selectRoom(room);
    } catch (error) {
      alert(error.message);
    }
  });

  $("accept-invite").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await api("/rooms/invitations/accept", {
        method: "POST",
        body: JSON.stringify({ token: $("invite-token").value.trim() })
      });
      $("accept-invite").reset();
      alert(result.message);
      await loadRooms();
    } catch (error) {
      alert(error.message);
    }
  });

  $("invite-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentRoom) return;

    try {
      const result = await api(`/rooms/${currentRoom.id}/invitations`, {
        method: "POST",
        body: JSON.stringify({
          email: $("invite-email").value.trim(),
          role: $("invite-role").value
        })
      });
      $("invite-result").textContent =
        `Transmettez ce jeton à ${result.email} : ${result.token}`;
      $("invite-form").reset();
      await loadActivities();
    } catch (error) {
      $("invite-result").textContent = error.message;
    }
  });

  $("message-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentRoom) return;

    const input = $("message-input");
    const content = input.value.trim();
    if (!content) return;

    try {
      const message = await api(`/rooms/${currentRoom.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content })
      });
      appendMessage(message);
      input.value = "";
      await loadActivities();
    } catch (error) {
      setStatus(error.message);
    }
  });

  $("file-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentRoom) return;

    const file = $("file-input").files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      await api(`/rooms/${currentRoom.id}/files`, {
        method: "POST",
        body: formData
      });
      $("file-form").reset();
      await Promise.all([loadFiles(), loadActivities()]);
    } catch (error) {
      setStatus(error.message);
    }
  });

  if (!token || token.startsWith("demo_")) {
    setStatus("Connectez-vous avec un compte réel pour accéder à Room Live.");
    return;
  }

  loadRooms().catch((error) => setStatus(error.message));
  window.addEventListener("beforeunload", closeSocket);
})();
(() => {
  "use strict";

  const API = window.API || window.location.origin;
  const token = sessionStorage.getItem("access_token") || localStorage.getItem("access_token");

  const $ = (id) => document.getElementById(id);
  let meeting = null;
  let socket = null;
  let localStream = null;
  const peers = new Map();
  const pendingCandidates = new Map();

  function setStatus(message) {
    const el = $("status");
    if (el) el.textContent = message || "";
  }

  function authHeaders(json = true) {
    const h = { Authorization: `Bearer ${token}` };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        ...authHeaders(!(options.body instanceof FormData)),
        ...(options.headers || {})
      }
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Erreur API (${response.status})`);
    }
    return data;
  }

  function sendSignal(type, toUserId, data) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type,
        to_user_id: toUserId,
        data
      }));
    }
  }

  function addVideo(id, stream, label, muted = false) {
    let card = document.querySelector(`[data-peer="${id}"]`);

    if (!card) {
      card = document.createElement("div");
      card.className = "video-card";
      card.dataset.peer = id;

      const video = document.createElement("video");
      video.autoplay = true;
      video.playsInline = true;
      video.muted = muted;

      const caption = document.createElement("span");
      caption.textContent = label;

      card.appendChild(video);
      card.appendChild(caption);
      $("videos").appendChild(card);
    }

    const video = card.querySelector("video");
    if (video.srcObject !== stream) {
      video.srcObject = stream;
    }
  }

  function removePeer(userId) {
    const pc = peers.get(userId);
    if (pc) {
      pc.close();
      peers.delete(userId);
    }
    pendingCandidates.delete(userId);
    const el = document.querySelector(`[data-peer="${userId}"]`);
    if (el) el.remove();
  }

  async function createPeer(userId, initiator = false) {
    if (peers.has(userId)) return peers.get(userId);

    const config = window.NEXA_RTC_ICE_SERVERS || [
      { urls: "stun:stun.l.google.com:19302" }
    ];

    const pc = new RTCPeerConnection({ iceServers: config });
    peers.set(userId, pc);

    if (localStream) {
      localStream.getTracks().forEach((track) => {
        pc.addTrack(track, localStream);
      });
    }

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        sendSignal("ice-candidate", userId, event.candidate.toJSON());
      }
    };

    pc.ontrack = (event) => {
      const stream = event.streams[0] || new MediaStream([event.track]);
      addVideo(userId, stream, `Participant ${userId}`);
    };

    pc.onconnectionstatechange = () => {
      if (["failed", "closed"].includes(pc.connectionState)) {
        removePeer(userId);
      }
    };

    if (initiator) {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      sendSignal("offer", userId, pc.localDescription.toJSON());
    }

    return pc;
  }

  async function flushCandidates(userId, pc) {
    const candidates = pendingCandidates.get(userId) || [];
    pendingCandidates.delete(userId);

    for (const candidate of candidates) {
      try {
        await pc.addIceCandidate(candidate);
      } catch (error) {
        console.warn("ICE candidate ignored:", error);
      }
    }
  }

  async function onSignal(message) {
    if (!message || typeof message !== "object") return;

    if (message.type === "participants") {
      const ids = message.user_ids || [];
      for (const userId of ids) {
        if (userId !== Number(localStorage.getItem("room_user_id") || "0")) {
          await createPeer(userId, true);
        }
      }
      return;
    }

    if (message.type === "participant_left") {
      removePeer(message.user_id);
      setStatus("Un participant a quitté la réunion.");
      return;
    }

    if (message.type === "peer_unavailable") {
      setStatus("Un participant invité n’est pas connecté.");
      return;
    }

    if (message.type === "error") {
      setStatus(message.message || "Erreur de signalisation.");
      return;
    }

    const fromUserId = message.from_user_id;
    if (!fromUserId) return;

    if (message.type === "offer") {
      const pc = await createPeer(fromUserId, false);
      await pc.setRemoteDescription(message.data);
      await flushCandidates(fromUserId, pc);

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      sendSignal("answer", fromUserId, pc.localDescription.toJSON());
      return;
    }

    if (message.type === "answer") {
      const pc = peers.get(fromUserId);
      if (!pc) return;

      await pc.setRemoteDescription(message.data);
      await flushCandidates(fromUserId, pc);
      return;
    }

    if (message.type === "ice-candidate") {
      const pc = peers.get(fromUserId);

      if (!pc || !pc.remoteDescription) {
        const list = pendingCandidates.get(fromUserId) || [];
        list.push(message.data);
        pendingCandidates.set(fromUserId, list);
      } else {
        try {
          await pc.addIceCandidate(message.data);
        } catch (error) {
          console.warn("ICE candidate ignored:", error);
        }
      }
    }
  }

  async function startCall(item) {
    if (meeting) {
      await leaveCall();
    }

    meeting = item;
    $("call-title").textContent = item.title;
    $("call-panel").hidden = false;
    $("videos").replaceChildren();

    setStatus("Autorisez la caméra et le micro…");

    try {
      localStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true
      });

      addVideo("local", localStream, "Vous", true);

      const wsBase = API.replace(/^http:/, "ws:").replace(/^https:/, "wss:");
      socket = new WebSocket(`${wsBase}/meetings/${item.id}/live`);

      socket.addEventListener("open", () => {
        socket.send(JSON.stringify({ token }));
      });

      socket.addEventListener("message", async (event) => {
        try {
          const payload = JSON.parse(event.data);
          await onSignal(payload);
        } catch (error) {
          console.error("Erreur WebRTC:", error);
          setStatus("La connexion vidéo a rencontré une erreur.");
        }
      });

      socket.addEventListener("close", () => {
        if (meeting) {
          setStatus("Connexion de signalisation interrompue. Vérifiez le réseau puis rejoignez à nouveau.");
        }
      });

      setStatus("Connexion à la réunion…");

    } catch (error) {
      await leaveCall();
      if (error.name === "NotAllowedError") {
        setStatus("Autorisez la caméra et le microphone dans votre navigateur.");
      } else {
        setStatus(`Impossible d’accéder à la caméra : ${error.message}`);
      }
    }
  }

  async function leaveCall() {
    if (socket) {
      socket.close();
      socket = null;
    }

    for (const id of [...peers.keys()]) {
      removePeer(id);
    }

    if (localStream) {
      localStream.getTracks().forEach((track) => track.stop());
      localStream = null;
    }

    meeting = null;
    $("videos").replaceChildren();
    $("call-panel").hidden = true;
  }

  async function loadMeetings() {
    const meetings = await api("/meetings");
    const list = $("meeting-list");

    list.replaceChildren();

    if (!meetings.length) {
      list.textContent = "Aucune réunion pour le moment.";
      return;
    }

    meetings
      .filter((item) => !item.is_closed)
      .forEach((item) => {
        const row = document.createElement("div");
        row.className = "meeting-row";

        const title = document.createElement("strong");
        title.textContent = item.title;

        const join = document.createElement("button");
        join.type = "button";
        join.textContent = "Rejoindre";

        join.addEventListener("click", () => {
          startCall(item);
        });

        row.appendChild(title);
        row.appendChild(join);
        list.appendChild(row);
      });
  }

  $("create-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const item = await api("/meetings", {
        method: "POST",
        body: JSON.stringify({
          title: $("meeting-title").value.trim()
        })
      });

      $("meeting-title").value = "";
      await loadMeetings();
      await startCall(item);
    } catch (error) {
      alert(error.message);
    }
  });

  $("invite-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!meeting) return;

    try {
      const result = await api(`/meetings/${meeting.id}/members`, {
        method: "POST",
        body: JSON.stringify({
          email: $("invite-email").value.trim()
        })
      });

      $("invite-status").textContent = `${result.email} peut maintenant rejoindre la réunion.`;
      $("invite-form").reset();
    } catch (error) {
      $("invite-status").textContent = error.message;
    }
  });

  $("mic-toggle").addEventListener("click", () => {
    const track = localStream && localStream.getAudioTracks()[0];
    if (track) {
      track.enabled = !track.enabled;
      $("mic-toggle").textContent = track.enabled ? "Couper le micro" : "Activer le micro";
    }
  });

  $("camera-toggle").addEventListener("click", () => {
    const track = localStream && localStream.getVideoTracks()[0];
    if (track) {
      track.enabled = !track.enabled;
      $("camera-toggle").textContent = track.enabled ? "Couper la caméra" : "Activer la caméra";
    }
  });

  $("hangup").addEventListener("click", async () => {
    await leaveCall();
  });

  if (!token || token.startsWith("demo_")) {
    const list = $("meeting-list");
    if (list) {
      list.textContent = "Connectez-vous avec un compte actif pour utiliser les réunions.";
    }
    return;
  }

  loadMeetings().catch((error) => {
    const list = $("meeting-list");
    if (list) list.textContent = error.message;
  });

  window.addEventListener("beforeunload", () => {
    if (socket) socket.close();
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
    }
  });
})();
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

  function status(text) { $("status").textContent = text; }
  function headers(json = true) {
    const h = { Authorization: `Bearer ${token}` };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }
  async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, { ...options, headers: { ...headers(!(options.body instanceof FormData)), ...(options.headers || {}) } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Erreur API ${response.status}`);
    return data;
  }
  function sendSignal(type, toUserId, data) {
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type, to_user_id: toUserId, data }));
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
      card.append(video, caption);
      $("videos").appendChild(card);
    }
    const video = card.querySelector("video");
    if (video.srcObject !== stream) video.srcObject = stream;
  }
  function removePeer(userId) {
    peers.get(userId)?.close();
    peers.delete(userId);
    pendingCandidates.delete(userId);
    document.querySelector(`[data-peer="${userId}"]`)?.remove();
  }
  async function createPeer(userId, initiator = false) {
    if (peers.has(userId)) return peers.get(userId);
    const config = window.NEXA_RTC_ICE_SERVERS || [
      { urls: "stun:stun.l.google.com:19302" }
    ];
    const pc = new RTCPeerConnection({ iceServers: config });
    peers.set(userId, pc);
    localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));
    pc.onicecandidate = (event) => {
      if (event.candidate) sendSignal("ice-candidate", userId, event.candidate.toJSON());
    };
    pc.ontrack = (event) => {
      const stream = event.streams[0] || new MediaStream([event.track]);
      addVideo(userId, stream, `Participant ${userId}`);
    };
    pc.onconnectionstatechange = () => {
      if (["failed", "closed"].includes(pc.connectionState)) removePeer(userId);
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
      try { await pc.addIceCandidate(candidate); } catch (error) { console.warn("ICE candidate ignoré", error); }
    }
  }
  async function onSignal(message) {
    if (message.type === "participants") {
      for (const id of message.user_ids || []) await createPeer(id, true);
      return;
    }
    if (message.type === "participant_left") {
      removePeer(message.user_id);
      status("Un participant a quitté la réunion.");
      return;
    }
    if (message.type === "peer_unavailable") {
      status("Un participant invité n’est pas connecté.");
      return;
    }
    if (message.type === "error") { status(message.message); return; }
    const id = message.from_user_id;
    if (!id) return;
    if (message.type === "offer") {
      const pc = await createPeer(id, false);
      await pc.setRemoteDescription(message.data);
      await flushCandidates(id, pc);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      sendSignal("answer", id, pc.localDescription.toJSON());
      return;
    }
    if (message.type === "answer") {
      const pc = peers.get(id);
      if (!pc) return;
      await pc.setRemoteDescription(message.data);
      await flushCandidates(id, pc);
      return;
    }
    if (message.type === "ice-candidate") {
      const pc = peers.get(id);
      if (!pc || !pc.remoteDescription) {
        const list = pendingCandidates.get(id) || [];
        list.push(message.data);
        pendingCandidates.set(id, list);
      } else {
        try { await pc.addIceCandidate(message.data); } catch (error) { console.warn("ICE candidate ignoré", error); }
      }
    }
  }
  async function startCall(item) {
    if (meeting) await leaveCall();
    meeting = item;
    $("call-title").textContent = item.title;
    $("call-panel").hidden = false;
    $("videos").replaceChildren();
    status("Autorisez l’accès à la caméra et au microphone…");
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
      addVideo("local", localStream, "Vous", true);
      const wsBase = API.replace(/^http:/, "ws:").replace(/^https:/, "wss:");
      socket = new WebSocket(`${wsBase}/meetings/${item.id}/live`);
      socket.addEventListener("open", () => socket.send(JSON.stringify({ token })));
      socket.addEventListener("message", async (event) => {
        try { await onSignal(JSON.parse(event.data)); }
        catch (error) { console.error("Erreur de négociation WebRTC", error); status("La connexion vidéo a rencontré une erreur."); }
      });
      socket.addEventListener("close", () => { if (meeting) status("Connexion de signalisation interrompue. Vérifiez le réseau puis rejoignez à nouveau."); });
      status("Connexion à la réunion…");
    } catch (error) {
      await leaveCall();
      status(error.name === "NotAllowedError" ? "Autorisez la caméra et le microphone dans votre navigateur." : `Impossible d’accéder à la caméra : ${error.message}`);
    }
  }
  async function leaveCall() {
    if (socket) { socket.close(); socket = null; }
    for (const id of [...peers.keys()]) removePeer(id);
    localStream?.getTracks().forEach((track) => track.stop());
    localStream = null;
    meeting = null;
    $("videos").replaceChildren();
    $("call-panel").hidden = true;
  }
  async function loadMeetings() {
    const meetings = await api("/meetings");
    const list = $("meeting-list");
    list.replaceChildren();
    if (!meetings.length) { list.textContent = "Aucune réunion pour le moment."; return; }
    meetings.filter((item) => !item.is_closed).forEach((item) => {
      const row = document.createElement("div");
      row.className = "meeting-row";
      const title = document.createElement("strong");
      title.textContent = item.title;
      const join = document.createElement("button");
      join.textContent = "Rejoindre";
      join.addEventListener("click", () => startCall(item));
      row.append(title, join);
      list.appendChild(row);
    });
  }
  $("create-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const item = await api("/meetings", { method: "POST", body: JSON.stringify({ title: $("meeting-title").value.trim() }) });
      $("create-form").reset();
      await loadMeetings();
      await startCall(item);
    } catch (error) { alert(error.message); }
  });
  $("invite-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!meeting) return;
    try {
      const result = await api(`/meetings/${meeting.id}/members`, { method: "POST", body: JSON.stringify({ email: $("invite-email").value.trim() }) });
      $("invite-status").textContent = `${result.email} peut maintenant rejoindre depuis la page Réunions.`;
      $("invite-form").reset();
    } catch (error) { $("invite-status").textContent = error.message; }
  });
  $("mic-toggle").addEventListener("click", () => {
    const track = localStream?.getAudioTracks()[0];
    if (track) { track.enabled = !track.enabled; $("mic-toggle").textContent = track.enabled ? "Couper le micro" : "Activer le micro"; }
  });
  $("camera-toggle").addEventListener("click", () => {
    const track = localStream?.getVideoTracks()[0];
    if (track) { track.enabled = !track.enabled; $("camera-toggle").textContent = track.enabled ? "Couper la caméra" : "Activer la caméra"; }
  });
  $("hangup").addEventListener("click", leaveCall);
  if (!token || token.startsWith("demo_")) {
    $("meeting-list").textContent = "Connectez-vous avec un compte actif pour utiliser les réunions.";
    return;
  }
  loadMeetings().catch((error) => { $("meeting-list").textContent = error.message; });
  window.addEventListener("beforeunload", () => {
    socket?.close();
    localStream?.getTracks().forEach((track) => track.stop());
  });
})();

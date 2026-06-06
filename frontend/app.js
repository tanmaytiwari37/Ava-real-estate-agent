/* ==========================================================
   💎 GLOBAL VARIABLES & STATE
   ========================================================== */
let room = null;
let localAudioTrack = null;
let pollIntervalId = null;
let activeTab = "leads";

// Web Audio API visualizer variables
let audioCtx = null;
let analyser = null;
let dataArray = null;
let visualizerFrameId = null;

// DOM Elements
const backendStatusText = document.getElementById("backend-status-text");
const callStatusBadge = document.getElementById("call-status");
const callBtn = document.getElementById("call-btn");
const callBtnText = document.getElementById("call-btn-text");
const muteBtn = document.getElementById("mute-btn");
const muteBtnText = document.getElementById("mute-btn-text");
const muteBtnIcon = document.getElementById("mute-btn-icon");
const voiceStateText = document.getElementById("voice-state");
const visualizerOrb = document.getElementById("visualizer-orb");

const backendUrlInput = document.getElementById("backend-url");
const roomNameInput = document.getElementById("room-name");

const tabButtons = document.querySelectorAll(".tab-btn");
const leadsList = document.getElementById("leads-list");
const appointmentsList = document.getElementById("appointments-list");

/* ==========================================================
   💻 INTERACTIVE TABS & DATABASE POLLING
   ========================================================== */
// Switch Tabs
tabButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    tabButtons.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    
    const targetTab = btn.getAttribute("data-tab");
    activeTab = targetTab;
    
    document.querySelectorAll(".tab-content").forEach(content => {
      content.classList.remove("active");
    });
    document.getElementById(`tab-${targetTab}`).classList.add("active");
    
    fetchDatabaseData();
  });
});

// Check API Server Status
async function checkBackendStatus() {
  const backendUrl = backendUrlInput.value.trim();
  const pulseDot = document.querySelector(".pulse-dot");
  
  try {
    const res = await fetch(backendUrl);
    if (res.ok) {
      const data = await res.json();
      backendStatusText.textContent = "CRM API: Online";
      pulseDot.className = "pulse-dot active";
    } else {
      backendStatusText.textContent = `CRM API Error (Status ${res.status})`;
      pulseDot.className = "pulse-dot warning";
    }
  } catch (err) {
    backendStatusText.textContent = "CRM API: Offline";
    pulseDot.className = "pulse-dot error";
  }
}

// Fetch Leads & Appointments
async function fetchDatabaseData() {
  const backendUrl = backendUrlInput.value.trim();
  
  if (activeTab === "leads") {
    try {
      const res = await fetch(`${backendUrl}/leads`);
      if (res.ok) {
        const leads = await res.json();
        renderLeads(leads);
      }
    } catch (err) {
      console.error("Error fetching leads:", err);
    }
  } else {
    try {
      const res = await fetch(`${backendUrl}/appointments`);
      if (res.ok) {
        const appointments = await res.json();
        renderAppointments(appointments);
      }
    } catch (err) {
      console.error("Error fetching appointments:", err);
    }
  }
}

// Render Leads list
function renderLeads(leads) {
  if (!leads || leads.length === 0) {
    leadsList.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">👥</span>
        <p>No leads captured yet.</p>
        <p class="sub">Speak to Ava to save a new lead.</p>
      </div>
    `;
    return;
  }
  
  // Sort by latest leads (newest UUIDs/randomness first or preserve order)
  leadsList.innerHTML = leads.map(lead => `
    <div class="feed-item">
      <div class="feed-item-header">
        <span class="feed-item-title">👤 ${escapeHtml(lead.name)}</span>
        <span class="feed-item-time">Active Lead</span>
      </div>
      <div class="feed-item-details">
        <div><span class="detail-label">Phone:</span> <span class="detail-value">${escapeHtml(lead.phone)}</span></div>
        <div><span class="detail-label">Email:</span> <span class="detail-value">${escapeHtml(lead.email || "Not shared")}</span></div>
        <div><span class="detail-label">Budget:</span> <span class="detail-value">${lead.budget ? '₹' + Number(lead.budget).toLocaleString('en-IN') : "Not specified"}</span></div>
        <div><span class="detail-label">Lead ID:</span> <span class="detail-value" style="font-size:10px; font-family:monospace;">${lead.id.substring(0,8)}...</span></div>
      </div>
    </div>
  `).join("");
}

// Render Appointments list
function renderAppointments(apps) {
  if (!apps || apps.length === 0) {
    appointmentsList.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📅</span>
        <p>No appointments booked yet.</p>
        <p class="sub">Ask Ava to schedule a viewing visit.</p>
      </div>
    `;
    return;
  }
  
  appointmentsList.innerHTML = apps.map(app => {
    const time = new Date(app.appointment_time).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short'
    });
    return `
      <div class="feed-item">
        <div class="feed-item-header">
          <span class="feed-item-title">📅 Viewing Scheduled</span>
          <span class="feed-item-time" style="color:var(--success); font-weight:600;">Confirmed</span>
        </div>
        <div class="feed-item-details">
          <div><span class="detail-label">Time:</span> <span class="detail-value" style="color:var(--secondary);">${time}</span></div>
          <div><span class="detail-label">Property:</span> <span class="detail-value" style="font-weight:600; color:white;">🏠 ${escapeHtml(app.property_id)}</span></div>
          <div style="grid-column: span 2;"><span class="detail-label">Notes:</span> <span class="detail-value">${escapeHtml(app.notes || "None")}</span></div>
          <div style="grid-column: span 2;"><span class="detail-label">Lead ID:</span> <span class="detail-value" style="font-size:10px; font-family:monospace;">${app.lead_id}</span></div>
        </div>
      </div>
    `;
  }).join("");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ==========================================================
   🎙️ AUDIO ANALYSIS & VISUALIZER
   ========================================================== */
function startAudioAnalysis(track) {
  try {
    // Initialize Web Audio Context
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    // Attach stream from LiveKit audio track
    const mediaStream = new MediaStream([track.mediaStreamTrack]);
    const source = audioCtx.createMediaStreamSource(mediaStream);
    
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);
    
    const bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);
    
    function draw() {
      analyser.getByteFrequencyData(dataArray);
      
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const average = sum / bufferLength;
      
      // If average volume is above threshold, Ava is speaking
      if (average > 3) {
        visualizerOrb.className = "ava-orb speaking";
        voiceStateText.textContent = "Ava is speaking...";
        
        // Scale and glow based on voice volume
        const scale = 1.0 + (average / 120) * 0.22;
        const glow = 40 + (average / 120) * 40;
        visualizerOrb.style.transform = `scale(${scale})`;
        visualizerOrb.style.boxShadow = `0 0 ${glow}px rgba(217, 70, 239, 0.65)`;
      } else {
        // Return to listening state
        visualizerOrb.className = "ava-orb listening";
        voiceStateText.textContent = "Ava is listening. Go ahead, talk to her!";
        visualizerOrb.style.transform = "scale(1)";
        visualizerOrb.style.boxShadow = "0 0 40px var(--secondary-glow)";
      }
      
      visualizerFrameId = requestAnimationFrame(draw);
    }
    
    draw();
  } catch (err) {
    console.error("Failed to start audio analysis:", err);
  }
}

function stopAudioAnalysis() {
  if (visualizerFrameId) {
    cancelAnimationFrame(visualizerFrameId);
    visualizerFrameId = null;
  }
  if (audioCtx) {
    audioCtx.close();
    audioCtx = null;
  }
  visualizerOrb.className = "ava-orb";
  visualizerOrb.style.transform = "scale(1)";
  visualizerOrb.style.boxShadow = "";
}

/* ==========================================================
   🔗 LIVEKIT CONNECTION
   ========================================================== */
async function connectToAva() {
  const backendUrl = backendUrlInput.value.trim();
  const roomName = roomNameInput.value.trim();
  
  updateCallUI("connecting");
  voiceStateText.textContent = "Acquiring connection token...";
  
  try {
    // 1. Get Access Token from local FastAPI backend
    const res = await fetch(`${backendUrl}/token?room_name=${roomName}`);
    if (!res.ok) {
      throw new Error(`Token request failed with status ${res.status}`);
    }
    const connectionData = await res.json();
    if (connectionData.error) {
      throw new Error(connectionData.error);
    }
    
    const { token, url } = connectionData;
    
    // 2. Initialize LiveKit Room
    const { Room, RoomEvent } = LivekitClient;
    room = new Room();
    
    // 3. Set up Room Event Listeners
    room.on(RoomEvent.Connected, () => {
      console.log("Connected to LiveKit room successfully!");
      updateCallUI("connected");
      voiceStateText.textContent = "Connected! Say hello to Ava.";
      visualizerOrb.className = "ava-orb listening";
      
      // Auto-publish local microphone
      room.localParticipant.setMicrophoneEnabled(true).then(track => {
        localAudioTrack = track;
      }).catch(err => {
        console.error("Error enabling microphone:", err);
        voiceStateText.textContent = "Connected, but microphone access was denied.";
      });
    });
    
    room.on(RoomEvent.Disconnected, (reason) => {
      console.log("Disconnected from room:", reason);
      handleDisconnect();
    });
    
    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      // If we receive the voice agent's audio track, play it and visualise it
      if (track.kind === "audio") {
        console.log("Subscribed to audio track from participant:", participant.identity);
        const audioElement = track.attach();
        document.body.appendChild(audioElement);
        
        // Start animating the orb visualizer in sync with Ava's voice!
        startAudioAnalysis(track);
      }
    });
    
    // 4. Trigger WebRTC Connection
    voiceStateText.textContent = "Connecting to LiveKit room...";
    await room.connect(url, token);
    
  } catch (err) {
    console.error("Connection failed:", err);
    alert(`Could not connect to Ava: ${err.message}`);
    updateCallUI("disconnected");
    voiceStateText.textContent = "Connection failed. Please retry.";
    visualizerOrb.className = "ava-orb";
  }
}

function handleDisconnect() {
  if (room) {
    room.disconnect();
    room = null;
  }
  localAudioTrack = null;
  stopAudioAnalysis();
  updateCallUI("disconnected");
  voiceStateText.textContent = "Ava is resting. Click call to wake her up.";
}

function updateCallUI(state) {
  if (state === "connecting") {
    callStatusBadge.textContent = "Connecting...";
    callStatusBadge.className = "badge connecting";
    callBtnText.textContent = "Connecting...";
    callBtn.disabled = true;
    muteBtn.disabled = true;
  } else if (state === "connected") {
    callStatusBadge.textContent = "Connected";
    callStatusBadge.className = "badge connected";
    callBtnText.textContent = "Disconnect";
    callBtn.className = "btn btn-primary connected";
    callBtn.disabled = false;
    muteBtn.disabled = false;
  } else {
    callStatusBadge.textContent = "Disconnected";
    callStatusBadge.className = "badge disconnected";
    callBtnText.textContent = "Connect to Ava";
    callBtn.className = "btn btn-primary";
    callBtn.disabled = false;
    muteBtn.disabled = true;
    muteBtn.className = "btn btn-secondary";
    muteBtnText.textContent = "Mute Mic";
    muteBtnIcon.textContent = "🎤";
  }
}

// Toggle Microphone Mute
async function toggleMute() {
  if (!room || !room.localParticipant) return;
  
  const isMuted = room.localParticipant.isMicrophoneEnabled;
  if (isMuted) {
    await room.localParticipant.setMicrophoneEnabled(false);
    muteBtn.className = "btn btn-secondary muted";
    muteBtnText.textContent = "Unmute Mic";
    muteBtnIcon.textContent = "🔇";
  } else {
    await room.localParticipant.setMicrophoneEnabled(true);
    muteBtn.className = "btn btn-secondary";
    muteBtnText.textContent = "Mute Mic";
    muteBtnIcon.textContent = "🎤";
  }
}

/* ==========================================================
   🚀 INITIALIZATION & RUN
   ========================================================== */
// Wire Call Button
callBtn.addEventListener("click", () => {
  if (room && room.state === "connected") {
    handleDisconnect();
  } else {
    connectToAva();
  }
});

// Wire Mute Button
muteBtn.addEventListener("click", toggleMute);

// Initialize Backend Connection Polling
window.addEventListener("DOMContentLoaded", () => {
  checkBackendStatus();
  fetchDatabaseData();
  
  // Poll backend status and data lists every 3 seconds
  pollIntervalId = setInterval(() => {
    checkBackendStatus();
    fetchDatabaseData();
  }, 3000);
});

// Cleanup on exit
window.addEventListener("beforeunload", () => {
  if (pollIntervalId) clearInterval(pollIntervalId);
  handleDisconnect();
});

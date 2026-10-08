let callId = null;
let recognition = null;
let listening = false;
let currentState = null;

const $ = id => document.getElementById(id);

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

function formatMoney(value) {
  return typeof value === "number" ? "₹" + value.toLocaleString("en-IN") : "—";
}

function statusClass(status) {
  if (["QUALIFIED"].includes(status)) return "good";
  if (["NOT_ELIGIBLE", "TRANSFER", "NOT_INTERESTED"].includes(status)) return "bad";
  if (["CALLBACK", "ENDED"].includes(status)) return "warning";
  return "neutral";
}

function addMessage(speaker, text) {
  const box = $("messages");
  const empty = box.querySelector(".empty-state");
  if (empty) empty.remove();
  const div = document.createElement("div");
  div.className = "message " + (speaker === "AI" ? "ai" : "customer");
  div.innerHTML = `<div class="speaker-row"><span class="speaker-dot"></span><span class="speaker">${speaker === "AI" ? "AI Agent" : "Customer"}</span></div><div>${escapeHtml(text)}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  if (speaker === "AI") speak(text);
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = $("language").value === "Hindi" ? "hi-IN" : "en-IN";
  u.rate = 0.98;
  speechSynthesis.speak(u);
}

function answeredCount(state) {
  if (!state) return 0;
  const keys = ["property_type", "ownership_status", "documents_available", "loan_amount", "occupation_income", "market_value", "tenure"];
  return keys.reduce((count, key) => {
    if (key === "occupation_income") return count + (state.occupation && state.income_mode ? 1 : 0);
    return count + (state[key] !== null && state[key] !== undefined ? 1 : 0);
  }, 0);
}

function displayValue(key, value) {
  if (value === null || value === undefined || value === "") return "Pending";
  if (key === "documents_available") return value === true ? "Available" : value === false ? "Not available" : "Pending";
  if (key === "loan_amount") return formatMoney(value);
  if (key === "market_value") return formatMoney(value);
  if (key === "tenure") return `${value} years`;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return value;
}

function renderState(state) {
  currentState = state;
  const items = [
    ["property_type", "Property type"],
    ["ownership_status", "Ownership"],
    ["documents_available", "Original documents"],
    ["loan_amount", "Loan amount"],
    ["occupation", "Occupation"],
    ["income_mode", "Income mode"],
    ["market_value", "Market value"],
    ["tenure", "Tenure"],
  ];
  $("state").innerHTML = items.map(([key, label]) => {
    const value = displayValue(key, state[key]);
    const pending = value === "Pending";
    return `<div class="check-row"><div class="check-label"><span class="check-circle ${pending ? "pending" : "done"}">${pending ? "" : "✓"}</span><span>${label}</span></div><span class="check-value ${pending ? "pending-text" : ""}">${escapeHtml(value)}</span></div>`;
  }).join("");

  const count = answeredCount(state);
  const percent = Math.round((count / 7) * 100);
  $("metricProgress").textContent = `${count} / 7`;
  $("progressText").textContent = `${percent}%`;
  $("progressBar").style.width = `${percent}%`;
  $("metricLoan").textContent = formatMoney(state.loan_amount);
  $("metricStatus").textContent = state.status || "IN_PROGRESS";
  const badge = $("statusBadge");
  badge.className = `status-badge ${statusClass(state.status)}`;
  badge.innerHTML = `<span></span> ${escapeHtml((state.status || "IN_PROGRESS").replaceAll("_", " "))}`;

  const decision = $("decisionBox");
  const status = state.status || "IN_PROGRESS";
  const messages = {
    QUALIFIED: ["Qualified", "All seven checklist items passed the preliminary rules."],
    NOT_ELIGIBLE: ["Not eligible", state.disqualification_reason || "A qualification rule was not met."],
    TRANSFER: ["Transfer specialist", "The request requires the loan-transfer specialist flow."],
    CALLBACK: ["Callback requested", "The customer asked to continue at a later time."],
    NOT_INTERESTED: ["Not interested", "The customer chose not to proceed with the capped offer."],
    AWAITING_LOAN_CAP_CONFIRMATION: ["Awaiting confirmation", "The requested amount is above the ₹75 lakh offer limit."],
    ENDED: ["Call ended", "The call was ended before qualification completed."],
    IN_PROGRESS: ["In progress", "Continue the conversation to complete the checklist."],
  };
  const [title, description] = messages[status] || messages.IN_PROGRESS;
  decision.className = `decision-box ${statusClass(status)}-decision`;
  decision.innerHTML = `<span class="decision-dot"></span><div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(description)}</p></div>`;
}

async function startCall() {
  try {
    const customerName = $("customerName").value.trim() || "Customer";
    const language = $("language").value;
    const res = await fetch("/api/start", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({customer_name: customerName, language})
    });
    if (!res.ok) throw new Error("Unable to start the call.");
    const data = await res.json();
    callId = data.call_id;
    $("metricCustomer").textContent = customerName;
    $("callIdLabel").textContent = `Call ID: ${callId}`;
    $("messages").innerHTML = "";
    addMessage("AI", data.message);
    renderState(data.state);
    setCallControls(true);
  } catch (error) {
    $("support").textContent = error.message;
  }
}

function setCallControls(active) {
  $("micBtn").disabled = !active;
  $("sendBtn").disabled = !active;
  $("stopBtn").disabled = !active;
  $("startBtn").disabled = active;
  $("customerName").disabled = active;
  $("language").disabled = active;
}

async function sendText(text) {
  if (!callId || !text.trim()) return;
  const clean = text.trim();
  addMessage("Customer", clean);
  try {
    const res = await fetch("/api/chat", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({call_id:callId, text:clean})
    });
    const data = await res.json();
    if (data.error) { addMessage("AI", data.error); return; }
    addMessage("AI", data.message);
    renderState(data.state);
    if (data.finished) await finishCallUI();
  } catch (error) {
    addMessage("AI", "The server could not process that response. Please try again.");
    $("support").textContent = error.message;
  }
}

async function finishCallUI() {
  if (recognition && listening) recognition.stop();
  setCallControls(false);
  await loadHistory();
  callId = null;
}

async function endCall() {
  if (!callId) return;
  try {
    const res = await fetch("/api/end", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({call_id: callId})
    });
    const data = await res.json();
    if (!data.error) {
      addMessage("AI", "The call has been ended. The conversation has been saved.");
      renderState(data.state);
    }
  } finally {
    await finishCallUI();
  }
}

function initSpeech() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    $("support").textContent = "Browser speech recognition is unavailable. Use the text box, or open this page in Chrome/Edge.";
    return;
  }
  recognition = new SR();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.onstart = () => { listening = true; $("micBtn").innerHTML = "🛑 <span>Listening...</span>"; };
  recognition.onend = () => { listening = false; $("micBtn").innerHTML = "🎤 <span>Speak</span>"; };
  recognition.onerror = e => { $("support").textContent = "Microphone error: " + e.error; };
  recognition.onresult = e => sendText(e.results[0][0].transcript);
}

async function loadHistory() {
  try {
    const res = await fetch("/api/conversations");
    const rows = await res.json();
    const body = $("historyBody");
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="4" class="table-empty">No completed calls yet.</td></tr>`;
      return;
    }
    body.innerHTML = rows.slice(0, 10).map(row => `
      <tr>
        <td><strong>${escapeHtml(row.customer_name || "Customer")}</strong></td>
        <td><span class="table-status ${statusClass(row.status)}">${escapeHtml(row.status.replaceAll("_", " "))}</span></td>
        <td>${escapeHtml(row.started_at || "—")}</td>
        <td>${escapeHtml((row.transcript || "").split("\n").length)} turns</td>
      </tr>`).join("");
  } catch (error) {
    $("historyBody").innerHTML = `<tr><td colspan="4" class="table-empty">Unable to load call history.</td></tr>`;
  }
}

$("startBtn").onclick = startCall;
$("sendBtn").onclick = () => {
  const input = $("textInput");
  sendText(input.value);
  input.value = "";
  input.focus();
};
$("textInput").addEventListener("keydown", e => {
  if (e.key === "Enter") $("sendBtn").click();
});
$("micBtn").onclick = () => {
  if (!recognition) return;
  if (listening) recognition.stop(); else recognition.start();
};
$("stopBtn").onclick = endCall;
$("refreshHistory").onclick = loadHistory;

initSpeech();
loadHistory();

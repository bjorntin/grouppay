/* GroupPay Mini App — app.js */

const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// ── URL params (used for QR view mode) ────────────────────────────────────
const urlParams = new URLSearchParams(window.location.search);
const viewMode = urlParams.get("mode");

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  groupChatId: null,
  eventName: "",
  subtotal: 0,
  gstApplied: false,
  total: 0,
  splitType: null,           // "equal" | "custom"
  participants: [],          // [{ username, amount }]
};

// Extract group_chat_id from start_param — only relevant in bill-creation mode
const startParam = tg.initDataUnsafe?.start_param || "";
if (viewMode !== "qr" && startParam.startsWith("grp_")) {
  state.groupChatId = startParam.slice(4); // remove "grp_" prefix
}

// ── DOM refs ───────────────────────────────────────────────────────────────
const screens = {
  details:  document.getElementById("screen-details"),
  split:    document.getElementById("screen-split"),
  equal:    document.getElementById("screen-equal"),
  custom:   document.getElementById("screen-custom"),
  review:   document.getElementById("screen-review"),
  qr:       document.getElementById("screen-qr"),
};

function showScreen(name) {
  Object.values(screens).forEach(s => s.classList.remove("active"));
  screens[name].classList.add("active");
}

function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.add("visible");
}
function clearError(id) {
  const el = document.getElementById(id);
  el.textContent = "";
  el.classList.remove("visible");
}

// ── GST calculation ────────────────────────────────────────────────────────
function calcWithGST(subtotal) {
  const sc = subtotal * 0.10;
  const gst = (subtotal + sc) * 0.09;
  return { sc, gst, total: +(subtotal + sc + gst).toFixed(2) };
}

function fmt(n) { return "$" + n.toFixed(2); }

function updateGSTBreakdown() {
  const subtotal = parseFloat(document.getElementById("subtotal").value) || 0;
  const gstOn = document.getElementById("gst-toggle").checked;
  const breakdown = document.getElementById("gst-breakdown");

  if (gstOn && subtotal > 0) {
    const { sc, gst, total } = calcWithGST(subtotal);
    document.getElementById("br-subtotal").textContent = fmt(subtotal);
    document.getElementById("br-sc").textContent       = fmt(sc);
    document.getElementById("br-gst").textContent      = fmt(gst);
    document.getElementById("br-total").textContent    = fmt(total);
    breakdown.classList.add("visible");
  } else {
    breakdown.classList.remove("visible");
  }
}

document.getElementById("subtotal").addEventListener("input", updateGSTBreakdown);
document.getElementById("gst-toggle").addEventListener("change", updateGSTBreakdown);

// ── Screen 1 → 2 ──────────────────────────────────────────────────────────
document.getElementById("btn-to-split").addEventListener("click", () => {
  clearError("err-details");
  const eventName = document.getElementById("event-name").value.trim();
  const subtotal  = parseFloat(document.getElementById("subtotal").value);
  const gstOn     = document.getElementById("gst-toggle").checked;

  if (!eventName) { showError("err-details", "Please enter an event name."); return; }
  if (!subtotal || subtotal <= 0) { showError("err-details", "Please enter a valid amount."); return; }

  state.eventName  = eventName;
  state.subtotal   = subtotal;
  state.gstApplied = gstOn;
  state.total      = gstOn ? calcWithGST(subtotal).total : +subtotal.toFixed(2);

  showScreen("split");
});

document.getElementById("back-to-details").addEventListener("click", () => showScreen("details"));

// ── Screen 2: Choose split type ────────────────────────────────────────────
function chooseSplit(type) {
  state.splitType = type;
  state.participants = [];

  if (type === "equal") {
    document.getElementById("equal-list").innerHTML = "";
    document.getElementById("equal-username").value = "";
    document.getElementById("btn-equal-done").disabled = true;
    clearError("err-equal");
    updatePerPerson();
    showScreen("equal");
  } else {
    document.getElementById("custom-list").innerHTML = "";
    document.getElementById("custom-username").value = "";
    document.getElementById("custom-amount").value = "";
    document.getElementById("custom-total-label").textContent = fmt(state.total);
    document.getElementById("btn-custom-done").disabled = true;
    clearError("err-custom");
    updateCustomRemaining();
    showScreen("custom");
  }
}

document.getElementById("btn-equal").addEventListener("click", () => chooseSplit("equal"));
document.getElementById("btn-custom").addEventListener("click", () => chooseSplit("custom"));

document.getElementById("back-to-split-from-equal").addEventListener("click", () => showScreen("split"));
document.getElementById("back-to-split-from-custom").addEventListener("click", () => showScreen("split"));

// ── Screen 3a: Equal split ─────────────────────────────────────────────────
function updatePerPerson() {
  const n = state.participants.length;
  const note = document.getElementById("per-person-note");
  if (n === 0) {
    note.textContent = "";
  } else {
    const each = state.total / n;
    note.textContent = `${fmt(each)} per person (${n} people)`;
  }
}

function renderEqualList() {
  const list = document.getElementById("equal-list");
  const n = state.participants.length;
  const each = n > 0 ? (state.total / n) : 0;

  list.innerHTML = state.participants.map((p, i) => `
    <div class="participant-item">
      <span class="name">@${p.username}</span>
      <span style="display:flex;align-items:center;gap:8px">
        <span class="amount">${fmt(each)}</span>
        <button class="remove-btn" data-i="${i}" title="Remove">✕</button>
      </span>
    </div>
  `).join("");

  list.querySelectorAll(".remove-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.participants.splice(parseInt(btn.dataset.i), 1);
      renderEqualList();
      updatePerPerson();
      document.getElementById("btn-equal-done").disabled = state.participants.length === 0;
    });
  });
}

function addEqualParticipant() {
  clearError("err-equal");
  const input = document.getElementById("equal-username");
  const username = input.value.trim().replace(/^@/, "").toLowerCase();
  if (!username) { showError("err-equal", "Please enter a username."); return; }
  if (state.participants.some(p => p.username === username)) {
    showError("err-equal", `@${username} is already added.`); return;
  }
  state.participants.push({ username, amount: 0 });
  input.value = "";
  renderEqualList();
  updatePerPerson();
  document.getElementById("btn-equal-done").disabled = false;
}

document.getElementById("btn-equal-add").addEventListener("click", addEqualParticipant);
document.getElementById("equal-username").addEventListener("keydown", e => {
  if (e.key === "Enter") addEqualParticipant();
});

document.getElementById("btn-equal-done").addEventListener("click", () => {
  const n = state.participants.length;
  const each = +(state.total / n).toFixed(2);
  let assigned = 0;
  state.participants.forEach((p, i) => {
    if (i < n - 1) { p.amount = each; assigned += each; }
    else { p.amount = +(state.total - assigned).toFixed(2); }
  });
  renderReview();
  showScreen("review");
});

// ── Screen 3b: Custom split ────────────────────────────────────────────────
function updateCustomRemaining() {
  const assigned = state.participants.reduce((s, p) => s + p.amount, 0);
  const remaining = +(state.total - assigned).toFixed(2);
  const el = document.getElementById("custom-remaining");
  if (state.participants.length === 0) {
    el.textContent = "";
    return;
  }
  if (Math.abs(remaining) < 0.005) {
    el.style.color = "var(--link)";
    el.textContent = "✓ Total matches";
  } else if (remaining > 0) {
    el.style.color = "var(--hint)";
    el.textContent = `Remaining: ${fmt(remaining)}`;
  } else {
    el.style.color = "#ff4444";
    el.textContent = `Over by ${fmt(-remaining)}`;
  }
}

function renderCustomList() {
  const list = document.getElementById("custom-list");
  list.innerHTML = state.participants.map((p, i) => `
    <div class="participant-item">
      <span class="name">@${p.username}</span>
      <span style="display:flex;align-items:center;gap:8px">
        <span class="amount">${fmt(p.amount)}</span>
        <button class="remove-btn" data-i="${i}" title="Remove">✕</button>
      </span>
    </div>
  `).join("");

  list.querySelectorAll(".remove-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      state.participants.splice(parseInt(btn.dataset.i), 1);
      renderCustomList();
      updateCustomRemaining();
      checkCustomDone();
    });
  });
}

function checkCustomDone() {
  const assigned = state.participants.reduce((s, p) => s + p.amount, 0);
  const ok = state.participants.length > 0 && Math.abs(assigned - state.total) < 0.005;
  document.getElementById("btn-custom-done").disabled = !ok;
}

function addCustomParticipant() {
  clearError("err-custom");
  const uInput = document.getElementById("custom-username");
  const aInput = document.getElementById("custom-amount");
  const username = uInput.value.trim().replace(/^@/, "").toLowerCase();
  const amount = parseFloat(aInput.value);

  if (!username) { showError("err-custom", "Please enter a username."); return; }
  if (!amount || amount <= 0) { showError("err-custom", "Please enter a valid amount."); return; }
  if (state.participants.some(p => p.username === username)) {
    showError("err-custom", `@${username} is already added.`); return;
  }

  const assigned = state.participants.reduce((s, p) => s + p.amount, 0);
  if (assigned + amount > state.total + 0.005) {
    showError("err-custom", `That would exceed the total of ${fmt(state.total)}.`); return;
  }

  state.participants.push({ username, amount: +amount.toFixed(2) });
  uInput.value = "";
  aInput.value = "";
  renderCustomList();
  updateCustomRemaining();
  checkCustomDone();
}

document.getElementById("btn-custom-add").addEventListener("click", addCustomParticipant);
document.getElementById("custom-amount").addEventListener("keydown", e => {
  if (e.key === "Enter") addCustomParticipant();
});

document.getElementById("btn-custom-done").addEventListener("click", () => {
  renderReview();
  showScreen("review");
});

document.getElementById("back-to-participants").addEventListener("click", () => {
  showScreen(state.splitType === "equal" ? "equal" : "custom");
});

// ── Screen 4: Review ───────────────────────────────────────────────────────
function renderReview() {
  const tbody = document.getElementById("review-tbody");
  tbody.innerHTML = state.participants.map(p => `
    <tr>
      <td>@${p.username}</td>
      <td style="text-align:right">${fmt(p.amount)}</td>
    </tr>
  `).join("");

  const reviewTotal = state.participants.reduce((s, p) => s + p.amount, 0);
  document.getElementById("review-total-val").textContent = fmt(reviewTotal);
}

document.getElementById("btn-confirm").addEventListener("click", () => {
  clearError("err-review");

  if (!state.groupChatId) {
    showError("err-review", "Cannot determine group. Please start from /split in a group chat.");
    return;
  }

  const payload = {
    group_chat_id: state.groupChatId,
    event: state.eventName,
    total: state.total,
    gst_applied: state.gstApplied,
    split_type: state.splitType,
    participants: state.participants,
  };

  tg.sendData(JSON.stringify(payload));
});

// ── Screen 5: QR View mode ────────────────────────────────────────────────
// Activated when the page is opened with ?mode=qr (from the "View QR" button in the group).
// All QR data is encoded in the URL — no backend call needed.
if (viewMode === "qr") {
  showScreen("qr");

  const encoded = urlParams.get("p") || "";
  const amount  = urlParams.get("a") || "0.00";
  const event   = urlParams.get("e") || "Bill";
  const payer   = urlParams.get("n") || "Payer";

  document.getElementById("qr-event").textContent = event;
  document.getElementById("qr-amount").textContent = `$${amount}`;
  document.getElementById("qr-payer").textContent  = `Pay to: ${payer}`;

  if (encoded) {
    try {
      // Decode base64url (restore padding stripped by Python)
      const b64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
      const padded = b64 + "=".repeat((4 - b64.length % 4) % 4);
      const payloadStr = atob(padded);

      new QRCode(document.getElementById("qrcode-container"), {
        text: payloadStr,
        width: 240,
        height: 240,
        colorDark: "#6b21a8",   // purple to match bot QR style
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.M,
      });
    } catch (err) {
      showError("err-qr", "Could not generate QR code. Please try tapping the button again.");
    }
  } else {
    showError("err-qr", "QR data missing. Please tap the button in the group again.");
  }

  document.getElementById("btn-close-qr").addEventListener("click", () => {
    if (tg && tg.close) tg.close();
    else window.close();
  });
}

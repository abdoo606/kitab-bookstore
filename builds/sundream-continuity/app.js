const MODELS = {
  seedance_mini: { label: "Seedance 2.0 Mini (480p · 28 cr)", credits: 28, quality: 0.76 },
  minimax_h3:    { label: "MiniMax H3 2K + Audio (104 cr)", credits: 104, quality: 0.96 }
};
const KEYFRAME_CREDITS = 4; // Seedream 4.5 4K start frame

const PRESETS = {
  last_train: {
    title: "The Last Train",
    shots: [
      { id: "S01", title: "Platform 9 Rain Arrival", hero: true, cast: "Elena (Trench Coat #A1)", lighting: "3200K Sodium Wet", model: "minimax_h3", locked: true, continuity: 97, dialogue: "SFX: Distant rail screech + rain" },
      { id: "S02", title: "Ticket Booth Exchange", hero: false, cast: "Elena + Clerk", lighting: "Fluorescent Green", model: "seedance_mini", locked: false, continuity: 74, dialogue: "ELENA: One way to Harbor." },
      { id: "S03", title: " boarding Empty Car 04", hero: false, cast: "Elena (Trench Coat #A1)", lighting: "Flicker Tungsten", model: "seedance_mini", locked: true, continuity: 93, dialogue: "SFX: Pneumatic doors seal" },
      { id: "S04", title: "Briefcase Reveal Close-Up", hero: true, cast: "Elena Hands + Brass Key", lighting: "rim-amber", model: "minimax_h3", locked: false, continuity: 78, dialogue: "ELENA (V.O.): He never meant to board." },
      { id: "S05", title: "Tunnel Exit Sunrise Wide", hero: true, cast: "Train Exterior + Elena", lighting: "Golden Dawn", model: "minimax_h3", locked: true, continuity: 96, dialogue: "SCORE: Cello swell + sub-bass" }
    ]
  },
  sneaker_ad: {
    title: "Sneaker Spec Ad",
    shots: [
      { id: "A01", title: "Asphalt Puddle Macro Impact", hero: true, cast: "Runner #01 + Volt Sole", lighting: "High-Contrast Neon", model: "minimax_h3", locked: true, continuity: 98, dialogue: "SFX: Sub-drop impact" },
      { id: "A02", title: "SubwayStair Sprint Tracking", hero: false, cast: "Runner #01", lighting: "Cool Cyan Tube", model: "seedance_mini", locked: true, continuity: 91, dialogue: "SFX: Rapid breath + percussive beat" },
      { id: "A03", title: "Lace Tension Whip-Pan", hero: false, cast: "Volt Shoe Macro", lighting: "Strobe White", model: "seedance_mini", locked: false, continuity: 76, dialogue: "VO: Zero slip." },
      { id: "A04", title: "Rooftop Leap Slow-Motion", hero: true, cast: "Runner #01 + City Skyline", lighting: "Sunset Backlight", model: "minimax_h3", locked: true, continuity: 95, dialogue: "SFX: Heartbeat + wind rush" },
      { id: "A05", title: "360 Hero Product Turntable", hero: true, cast: "Volt Shoe Pair", lighting: "Studio Rim Dual", model: "minimax_h3", locked: false, continuity: 81, dialogue: "VO: Built for the final mile." },
      { id: "A06", title: "Packshot Logo Lockup", hero: false, cast: "Brand Endcard", lighting: "Clean Dark Studio", model: "seedance_mini", locked: true, continuity: 99, dialogue: "MUSIC: Crisp sting" }
    ]
  }
};

let currentKey = "last_train";
let shots = JSON.parse(JSON.stringify(PRESETS.last_train.shots));
let budgetCap = 360;
const logs = ["[00:00] Initialized Sundream Continuity & Credit Orchestrator prototype."];

function logEvent(msg) {
  const ts = new Date().toISOString().slice(11, 19);
  logs.unshift(`[${ts}] ${msg}`);
  document.getElementById("eventLog").textContent = logs.slice(0, 18).join("\n");
}

function totalCredits() {
  return shots.reduce((sum, s) => sum + KEYFRAME_CREDITS + MODELS[s.model].credits, 0);
}

function avgContinuity() {
  return Math.round(shots.reduce((sum, s) => sum + s.continuity, 0) / shots.length);
}

function optimizeWithinBudget() {
  // Start all non-hero shots on draft Seedance Mini, then upgrade highest-priority hero shots to MiniMax H3 if budget allows
  shots.forEach(s => { s.model = "seedance_mini"; });
  for (const s of shots) {
    if (s.hero && totalCredits() + (MODELS.minimax_h3.credits - MODELS.seedance_mini.credits) <= budgetCap) {
      s.model = "minimax_h3";
    }
  }
  for (const s of shots) {
    if (!s.hero && totalCredits() + (MODELS.minimax_h3.credits - MODELS.seedance_mini.credits) <= budgetCap) {
      s.model = "minimax_h3";
    }
  }
  logEvent(`Auto-routed ${shots.length} shots inside ${budgetCap} cr budget (${totalCredits()} cr total).`);
  render();
}

function lockAllCast() {
  shots.forEach(s => {
    s.locked = true;
    s.continuity = Math.max(s.continuity, 95);
  });
  logEvent("Locked Seedream 4.5 cast & lighting reference anchors across all scenes (95%+ continuity).");
  render();
}

function buildManifest() {
  return {
    project: PRESETS[currentKey].title,
    duration_seconds: shots.length * 8,
    budget_cap_credits: budgetCap,
    planned_credits: totalCredits(),
    average_continuity_score: avgContinuity(),
    export_ready: totalCredits() <= budgetCap && avgContinuity() >= 88,
    timeline: shots.map((s, idx) => ({
      shot_id: s.id,
      tc_in: `00:00:${String(idx * 8).padStart(2, "0")}:00`,
      tc_out: `00:00:${String((idx + 1) * 8).padStart(2, "0")}:00`,
      title: s.title,
      keyframe_model: "seedream-4.5-4k (4 cr)",
      video_model: s.model,
      credits: KEYFRAME_CREDITS + MODELS[s.model].credits,
      cast_anchor_locked: s.locked,
      continuity_score: s.continuity,
      audio_track: s.dialogue
    }))
  };
}

function renderAssistant() {
  const container = document.getElementById("assistantProposals");
  const unlocked = shots.filter(s => !s.locked);
  const overBudget = totalCredits() - budgetCap;
  const cards = [];

  if (overBudget > 0) {
    cards.push({
      title: `Trim ${overBudget} cr to fit ${budgetCap} cr ceiling`,
      desc: "Route non-hero coverage shots to Seedance 2.0 Mini (28 cr) while preserving MiniMax H3 2K on hero beats.",
      actionLabel: "Do it",
      fn: () => optimizeWithinBudget()
    });
  }
  if (unlocked.length > 0) {
    cards.push({
      title: `Fix character drift on ${unlocked.map(u => u.id).join(", ")}`,
      desc: `Bind Seedream 4.5 cast & wardrobe reference tokens on ${unlocked.length} unlocked shot(s) before batch render.`,
      actionLabel: "Do it",
      fn: () => lockAllCast()
    });
  }
  cards.push({
    title: `Queue remaining ${shots.length} eight-second clips (${totalCredits()} cr)`,
    desc: "Validate start frames, reserve credits atomically, and generate FCPXML/JSON cut manifest.",
    actionLabel: "Simulate Batch Render",
    fn: () => {
      shots.forEach(s => { s.rendered = true; });
      logEvent(`Batch render verified: ${shots.length} clips (${shots.length * 8}s) ready on picture + audio tracks.`);
      render();
    }
  });

  container.innerHTML = "";
  cards.forEach(c => {
    const div = document.createElement("div");
    div.className = "assistant-prop";
    div.innerHTML = `<div style="font-weight:700;font-size:13px;margin-bottom:4px;">${c.title}</div>
      <div style="font-size:12px;color:#9aa6c7;margin-bottom:9px;">${c.desc}</div>
      <div style="display:flex;gap:8px;">
        <button class="btn btn-primary do-btn">${c.actionLabel}</button>
        <button class="btn skip-btn">Not now</button>
      </div>`;
    div.querySelector(".do-btn").addEventListener("click", c.fn);
    div.querySelector(".skip-btn").addEventListener("click", () => logEvent(`Deferred suggestion: "${c.title}"`));
    container.appendChild(div);
  });
}

function render() {
  const spent = totalCredits();
  const cont = avgContinuity();
  document.getElementById("kpiCredits").textContent = `${spent} cr`;
  document.getElementById("kpiCap").textContent = `${budgetCap} cr`;
  document.getElementById("kpiContinuity").textContent = `${cont}%`;
  const ok = spent <= budgetCap && cont >= 88;
  document.getElementById("kpiRuntime").textContent = `${shots.length * 8}s ${ok ? "PASS" : "REVIEW"}`;

  const badge = document.getElementById("budgetStatusBadge");
  badge.textContent = spent <= budgetCap ? `Within Cap (${budgetCap - spent} cr saved)` : `Over Cap (+${spent - budgetCap} cr)`;

  const exportBadge = document.getElementById("exportGateBadge");
  exportBadge.textContent = ok ? "Pre-Export Checks PASS" : "Resolve Drift / Budget";

  const grid = document.getElementById("shotsGrid");
  grid.innerHTML = "";
  shots.forEach((s, idx) => {
    const card = document.createElement("div");
    card.className = `shot-card ${s.continuity < 85 ? "drift" : ""}`;
    card.innerHTML = `
      <div class="shot-meta">
        <span><strong>${s.id}</strong> &middot; ${s.hero ? "HERO BEAT" : "COVERAGE"}</span>
        <span>${KEYFRAME_CREDITS + MODELS[s.model].credits} cr</span>
      </div>
      <div style="font-weight:700;font-size:14px;">${s.title}</div>
      <div style="font-size:12px;color:#9aa6c7;">Cast: ${s.cast}<br/>Look: ${s.lighting}</div>
      <div class="bar ${s.continuity < 85 ? "warn" : ""}"><span style="width:${s.continuity}%"></span></div>
      <div class="shot-meta">
        <span>Continuity: ${s.continuity}%</span>
        <span>${s.locked ? "Anchor Locked" : "Unlocked Drift"}</span>
      </div>
      <select class="btn model-sel" aria-label="Model for ${s.id}">
        <option value="seedance_mini" ${s.model === "seedance_mini" ? "selected" : ""}>Seedance 2.0 Mini (28 cr)</option>
        <option value="minimax_h3" ${s.model === "minimax_h3" ? "selected" : ""}>MiniMax H3 2K (104 cr)</option>
      </select>
      <button class="btn lock-btn">${s.locked ? "Anchor Locked ✓" : "Lock Cast Anchor"}</button>
    `;
    card.querySelector(".model-sel").addEventListener("change", e => {
      shots[idx].model = e.target.value;
      logEvent(`${s.id} model switched to ${MODELS[s.model].label}`);
      render();
    });
    card.querySelector(".lock-btn").addEventListener("click", () => {
      shots[idx].locked = !shots[idx].locked;
      shots[idx].continuity = shots[idx].locked ? 96 : 75;
      logEvent(`${s.id} cast reference ${shots[idx].locked ? "locked (96%)" : "unlocked (75%)"}`);
      render();
    });
    grid.appendChild(card);
  });

  const track = document.getElementById("timelineTrack");
  track.innerHTML = shots.map((s, i) => `
    <div class="clip-pill">
      <div><strong>${s.id}</strong> (00:${String(i * 8).padStart(2, "0")}–00:${String((i + 1) * 8).padStart(2, "0")})</div>
      <div style="color:#9aa6c7;margin-top:2px;">${s.title}</div>
      <div style="color:#fbbf24;margin-top:4px;">${s.dialogue}</div>
    </div>
  `).join("");

  document.getElementById("manifestPreview").textContent = JSON.stringify(buildManifest(), null, 2);
  renderAssistant();
}

document.getElementById("budgetSlider").addEventListener("input", e => {
  budgetCap = Number(e.target.value);
  document.getElementById("budgetLabel").textContent = budgetCap;
  render();
});
document.getElementById("autoOptimizeBtn").addEventListener("click", optimizeWithinBudget);
document.getElementById("lockAllCastBtn").addEventListener("click", lockAllCast);
document.getElementById("projectSelect").addEventListener("change", e => {
  currentKey = e.target.value;
  shots = JSON.parse(JSON.stringify(PRESETS[currentKey].shots));
  logEvent(`Loaded preset "${PRESETS[currentKey].title}".`);
  render();
});
document.getElementById("exportEdlBtn").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(buildManifest(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${currentKey}-sundream-cut-manifest.json`;
  a.click();
  logEvent(`Downloaded validated cut manifest (${currentKey}-sundream-cut-manifest.json).`);
});

render();

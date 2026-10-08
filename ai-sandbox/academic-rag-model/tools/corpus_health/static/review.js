"use strict";
const token = new URLSearchParams(window.location.search).get("token") || "";
const apiHeaders = {"X-Corpus-Health-Token": token};
const message = document.getElementById("message");
const container = document.getElementById("findings");
const labels = {accepted: "Accept", declined: "Decline", deferred: "Defer"};

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

async function post(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {...apiHeaders, "Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

function decisionButton(label, decision, entry) {
  const button = el("button", label);
  if (decision === "accepted" && (!entry.finding.fingerprint || entry.finding.fingerprint.startsWith("stat:"))) {
    button.disabled = true;
    button.title = "A content fingerprint is required before accepting this item.";
  }
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await post("/api/decision", {
        finding_id: entry.finding_id,
        fingerprint: entry.finding.fingerprint,
        decision
      });
      entry.card.remove();
      message.textContent = `${label} recorded.`;
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false;
    }
  });
  return button;
}

function renderGroup(groupName, entries) {
  const section = el("section", undefined, "group");
  section.append(el("h2", `${groupName} (${entries.length})`));
  const controls = el("div", undefined, "controls");
  for (const decision of ["accepted", "declined", "deferred"]) {
    const button = el("button", `${labels[decision]} all in this group`);
    if (decision === "accepted" && !entries.every(entry => entry.finding.batch_approval_allowed
      && entry.finding.fingerprint && !entry.finding.fingerprint.startsWith("stat:"))) {
      button.disabled = true;
      button.title = "Per-item acceptance is required for this cost category.";
    }
    button.addEventListener("click", async () => {
      const decisions = entries.map(entry => ({
        finding_id: entry.finding_id,
        fingerprint: entry.finding.fingerprint,
        decision
      }));
      button.disabled = true;
      try {
        await post("/api/batch", {decisions});
        section.remove();
        message.textContent = `${decisions.length} ${decision} decisions recorded.`;
      } catch (error) {
        message.textContent = error.message;
        button.disabled = false;
      }
    });
    controls.append(button);
  }
  section.append(controls);
  for (const entry of entries) {
    const item = entry.finding;
    const card = el("article", undefined, "finding");
    entry.card = card;
    card.append(el("h3", item.title || item.kind));
    card.append(el("p", item.path, "path"));
    if (item.expected_output) card.append(el("p", `Expected output: ${item.expected_output}`, "path"));
    card.append(el("p", item.evidence));
    card.append(el("p", `Cost: ${item.cost_category || "unknown"}`, "muted"));
    if (item.suggested_action) card.append(el("p", `Proposed step: ${item.suggested_action}`));
    const actions = el("div", undefined, "controls");
    for (const decision of ["accepted", "declined", "deferred"]) {
      actions.append(decisionButton(labels[decision], decision, entry));
    }
    card.append(actions);
    section.append(card);
  }
  return section;
}

async function load() {
  const response = await fetch(`/api/findings?token=${encodeURIComponent(token)}`);
  if (!response.ok) throw new Error(`Could not load findings (${response.status})`);
  const entries = await response.json();
  const groups = new Map();
  for (const entry of entries) {
    const key = `${entry.finding.kind} / ${entry.finding.cost_category || "unknown"}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entry);
  }
  container.replaceChildren(...Array.from(groups, ([kind, items]) => renderGroup(kind, items)));
  message.textContent = entries.length ? `${entries.length} pending findings.` : "No findings are waiting for review.";
}

document.getElementById("finish").addEventListener("click", async () => {
  try {
    await post("/api/close", {});
    message.textContent = "Review finished. You can close this tab.";
  } catch (error) {
    message.textContent = error.message;
  }
});
load().catch(error => { message.textContent = error.message; });

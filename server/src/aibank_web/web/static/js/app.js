// Chat controller: owns the message log, composer, streaming, and citation rendering.
import { streamChat } from "./sse.js";
import { renderInto, knownSet, assetHref } from "./markdown.js";

const log = document.getElementById("log");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const stopBtn = document.getElementById("stop");

const history = []; // prior turns as {role, content} (text only)
let known = new Set();
let controller = null;

// Best-effort: load the catalog's closed name vocabulary for citation linkifying.
fetch("/api/catalog/names")
  .then((r) => (r.ok ? r.json() : null))
  .then((names) => { if (names) known = knownSet(names); })
  .catch(() => {});

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function nearBottom() {
  return log.scrollHeight - log.scrollTop - log.clientHeight < 120;
}
function scrollIfFollowing(wasNear) {
  if (wasNear) log.scrollTop = log.scrollHeight;
}

function addUserMessage(text) {
  const wasNear = nearBottom();
  const msg = el("div", "msg user");
  msg.appendChild(el("div", "bubble", text));
  log.appendChild(msg);
  scrollIfFollowing(wasNear);
}

function addAssistantMessage() {
  const msg = el("div", "msg assistant");
  const activity = el("div", "activity");
  const bubble = el("div", "bubble");
  const content = el("div", "content");
  const sources = el("div", "sources");
  sources.hidden = true;
  bubble.append(content, sources);
  msg.append(activity, bubble);
  log.appendChild(msg);
  return { msg, activity, content, sources };
}

function setActivity(activity, text) {
  // Replace the live activity chip with the latest action.
  activity.innerHTML = "";
  if (!text) return;
  const chip = el("div", "chip");
  chip.append(el("span", "spinner"), el("span", "chip-label", text));
  activity.appendChild(chip);
}

function renderSources(container, sources) {
  if (!sources.length) return;
  container.hidden = false;
  container.innerHTML = "";
  container.appendChild(el("span", "sources-label", "Sources"));
  const list = el("div", "source-list");
  for (const s of sources) {
    const a = el("a", "source-chip");
    a.href = assetHref(s.kind, s.name, s.reference);
    a.textContent = s.reference ? `${s.kind}: ${s.name} / ${s.reference}` : `${s.kind}: ${s.name}`;
    list.appendChild(a);
  }
  container.appendChild(list);
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  input.disabled = busy;
  stopBtn.hidden = !busy;
  if (!busy) input.focus();
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || controller) return;

  addUserMessage(text);
  input.value = "";
  autoGrow();

  const view = addAssistantMessage();
  setActivity(view.activity, "Thinking…");

  let raw = "";
  let finalSources = [];
  let pending = false;
  const flush = () => {
    pending = false;
    const wasNear = nearBottom();
    renderInto(view.content, raw, known);
    scrollIfFollowing(wasNear);
  };
  const scheduleRender = () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(flush);
  };

  const body = { message: text, history: history.slice() };
  history.push({ role: "user", content: text });

  controller = new AbortController();
  setBusy(true);

  streamChat(
    body,
    {
      onToolCall: (d) => setActivity(view.activity, d.label),
      onStatus: (phase) => { if (phase === "thinking") setActivity(view.activity, "Thinking…"); },
      onText: (t) => {
        if (t) { raw += t; setActivity(view.activity, ""); scheduleRender(); }
      },
      onCitations: (sources) => { finalSources = sources; },
      onError: (err) => {
        setActivity(view.activity, "");
        const box = el("div", "error", err.message || "Something went wrong.");
        view.bubble.insertBefore(box, view.sources);
      },
      onDone: () => {
        setActivity(view.activity, "");
        renderInto(view.content, raw, known);
        renderSources(view.sources, finalSources);
        if (raw.trim()) history.push({ role: "assistant", content: raw });
        controller = null;
        setBusy(false);
      },
    },
    controller.signal,
  );
});

stopBtn.addEventListener("click", () => {
  if (controller) controller.abort();
  controller = null;
  setBusy(false);
});

// Enter to send, Shift+Enter for newline.
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// Auto-grow the textarea.
function autoGrow() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 200) + "px";
}
input.addEventListener("input", autoGrow);
input.focus();

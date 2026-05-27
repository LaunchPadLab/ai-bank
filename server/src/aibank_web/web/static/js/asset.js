// In-app asset viewer: reads kind/name from the path, fetches the JSON, renders the body.
// The browser route /a/{...} mirrors the API route /api/asset/{...}, so we just swap the prefix.
import { renderInto, knownSet } from "./markdown.js";

const root = document.getElementById("asset");

async function load() {
  const apiUrl = location.pathname.replace(/^\/a\//, "/api/asset/");
  let known = new Set();
  try {
    const namesResp = await fetch("/api/catalog/names");
    if (namesResp.ok) known = knownSet(await namesResp.json());
  } catch { /* linkify is best-effort */ }

  let resp;
  try {
    resp = await fetch(apiUrl);
  } catch {
    return showError("Could not reach the server.");
  }
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    return showError(data.error || `Not found (${resp.status}).`);
  }
  render(await resp.json(), known);
}

function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text != null) n.textContent = text;
  return n;
}

function render(asset, known) {
  document.title = `${asset.name} · ai-bank`;
  root.innerHTML = "";

  const header = el("header", "asset-header");
  header.appendChild(el("span", `badge badge-${asset.kind}`, asset.kind));
  header.appendChild(el("h1", "asset-title", asset.reference ? `${asset.name} / ${asset.reference}` : asset.name));
  if (asset.description) header.appendChild(el("p", "asset-desc", asset.description));
  root.appendChild(header);

  const meta = metaLine(asset);
  if (meta) root.appendChild(meta);

  const body = el("article", "asset-body markdown");
  renderInto(body, asset.body || "*(no content)*", known);
  root.appendChild(body);
}

function metaLine(asset) {
  const bits = [];
  if (asset.kind === "agent" && asset.model) bits.push(`model: ${asset.model}`);
  if (asset.kind === "rule" && asset.paths && asset.paths.length)
    bits.push(`paths: ${asset.paths.join(", ")}`);
  if (asset.kind === "skill" && asset.used_by_agents && asset.used_by_agents.length)
    bits.push(`used by: ${asset.used_by_agents.join(", ")}`);
  return bits.length ? el("p", "asset-meta", bits.join("  ·  ")) : null;
}

function showError(message) {
  root.innerHTML = "";
  root.appendChild(el("p", "error", message));
}

load();

// Markdown rendering + citation linkifying.
//
// Assistant output is model-generated and therefore untrusted: every render goes through
// marked (parse) -> DOMPurify (sanitize). Citation tokens like [skill:name], [agent:name],
// [rule:name], and [skill:name#file.md] are linkified to the in-app viewer AFTER render, by
// walking text nodes (so tokens inside code blocks/links are left alone). Only tokens whose
// (kind, name) exists in the catalog become links -- invented ones stay inert text, a visible
// tell that the model named something that doesn't exist.

const CITE = /\[(skill|agent|rule):([A-Za-z0-9][A-Za-z0-9_-]*)(?:#([^\]\s]+))?\]/g;

export function renderMarkdown(text) {
  const raw = window.marked.parse(text || "", { breaks: true, gfm: true });
  return window.DOMPurify.sanitize(raw, { ADD_ATTR: ["target", "rel"] });
}

// Render markdown into `el` and linkify any known citation tokens.
export function renderInto(el, text, known) {
  el.innerHTML = renderMarkdown(text);
  if (known) linkifyCitations(el, known);
}

function assetHref(kind, name, ref) {
  const base = `/a/${kind}/${encodeURIComponent(name)}`;
  return ref ? `${base}/reference/${encodeURIComponent(ref)}` : base;
}

// Build a Set of "kind:name" (lowercased) from a {skills, agents, rules} names payload.
export function knownSet(names) {
  const set = new Set();
  (names.skills || []).forEach((n) => set.add(`skill:${n.toLowerCase()}`));
  (names.agents || []).forEach((n) => set.add(`agent:${n.toLowerCase()}`));
  (names.rules || []).forEach((n) => set.add(`rule:${n.toLowerCase()}`));
  return set;
}

const SKIP_TAGS = new Set(["A", "CODE", "PRE", "SCRIPT", "STYLE"]);

export function linkifyCitations(root, known) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      for (let p = node.parentNode; p && p !== root; p = p.parentNode) {
        if (SKIP_TAGS.has(p.nodeName)) return NodeFilter.FILTER_REJECT;
      }
      return CITE.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });
  const targets = [];
  while (walker.nextNode()) targets.push(walker.currentNode);

  for (const node of targets) {
    const frag = document.createDocumentFragment();
    let last = 0;
    const text = node.nodeValue;
    CITE.lastIndex = 0;
    let m;
    while ((m = CITE.exec(text)) !== null) {
      const [token, kind, name, ref] = m;
      if (!known.has(`${kind}:${name.toLowerCase()}`)) continue; // unknown -> leave as text
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      const a = document.createElement("a");
      a.href = assetHref(kind, name, ref);
      a.className = "citation";
      a.textContent = ref ? `${name}#${ref}` : name;
      a.title = `${kind}: ${name}${ref ? " / " + ref : ""}`;
      frag.appendChild(a);
      last = m.index + token.length;
    }
    if (last === 0) continue; // no known tokens replaced
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    node.parentNode.replaceChild(frag, node);
  }
}

export { assetHref };

// Minimal SSE client over fetch + ReadableStream.
//
// We POST (message + history in the body) and read text/event-stream back, so the native
// EventSource API (GET-only, no body) won't do. Frames are delimited by a blank line; each has
// an `event:` type and a `data:` JSON payload. Comment lines (": ping" keepalives) are ignored.

const BOUNDARY = /\r?\n\r?\n/;

export async function streamChat(body, handlers, signal) {
  let resp;
  try {
    resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") return;
    handlers.onError?.({ code: "network", message: "Could not reach the server." });
    handlers.onDone?.();
    return;
  }

  if (!resp.ok || !resp.body) {
    handlers.onError?.({ code: "http", message: `Request failed (${resp.status}).` });
    handlers.onDone?.();
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let m;
      while ((m = BOUNDARY.exec(buf)) !== null) {
        const frame = buf.slice(0, m.index);
        buf = buf.slice(m.index + m[0].length);
        dispatchFrame(frame, handlers);
      }
    }
  } catch (err) {
    if (err.name === "AbortError") return;
    handlers.onError?.({ code: "stream", message: "The connection was interrupted." });
    handlers.onDone?.();
  }
}

function dispatchFrame(frame, handlers) {
  let event = "message";
  const dataLines = [];
  for (const line of frame.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue; // blank or comment/keepalive
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  let data = {};
  if (dataLines.length) {
    try {
      data = JSON.parse(dataLines.join("\n"));
    } catch {
      return;
    }
  }
  switch (event) {
    case "tool_call": handlers.onToolCall?.(data); break;
    case "text": handlers.onText?.(data.text || ""); break;
    case "status": handlers.onStatus?.(data.phase); break;
    case "citations": handlers.onCitations?.(data.sources || []); break;
    case "usage": handlers.onUsage?.(data); break;
    case "error": handlers.onError?.(data); break;
    case "done": handlers.onDone?.(); break;
  }
}

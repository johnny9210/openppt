const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SSEEvent {
  event: string;
  data: unknown;
}

export async function* streamGenerate(
  userRequest: string
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_request: userRequest }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const reader = response.body
    ?.pipeThrough(new TextDecoderStream())
    .getReader();

  if (!reader) throw new Error("No response body");

  let buffer = "";
  // Persist event type across read chunks (event: may arrive in separate chunk from data:)
  let currentEvent = "message";
  // Accumulate data: lines per SSE spec — a single event can span multiple data: lines
  let dataLines: string[] = [];

  function* flushEvent(): Generator<SSEEvent> {
    if (dataLines.length > 0) {
      const dataStr = dataLines.join("\n");
      try {
        yield { event: currentEvent, data: JSON.parse(dataStr) };
      } catch {
        yield { event: currentEvent, data: dataStr };
      }
      dataLines = [];
    }
    currentEvent = "message";
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += value;
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      } else if (line.trim() === "") {
        // Empty line = end of event block per SSE spec
        yield* flushEvent();
      }
    }
  }

  // Flush any pending event data if the stream ends without a trailing empty line
  yield* flushEvent();
}

export async function submitHumanReview(sessionId: string, action: string) {
  const response = await fetch(`${API_URL}/api/human-review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action }),
  });
  return response.json();
}

export async function downloadPptx(sessionId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/export/pptx/${sessionId}`);

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(err.detail || `Export error: ${response.status}`);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = "presentation.pptx";
  if (disposition) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match) filename = match[1];
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

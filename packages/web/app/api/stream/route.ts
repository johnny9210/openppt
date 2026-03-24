/**
 * SSE Proxy Route Handler
 * Proxies SSE stream from core API to the browser.
 * Necessary for Docker networking (browser can't reach core directly).
 */

export const dynamic = "force-dynamic";

const CORE_API_URL = process.env.CORE_API_URL || "http://core:8000";

export async function POST(request: Request) {
  const body = await request.json();

  const upstream = await fetch(`${CORE_API_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(JSON.stringify({ error: "Upstream error" }), {
      status: upstream.status,
    });
  }

  // Pipe the SSE stream through
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}

/**
 * Export slides to PPTX using dom-to-pptx.
 *
 * dom-to-pptx runs INSIDE the iframe (where the slides are rendered)
 * so that getBoundingClientRect / getComputedStyle work correctly.
 *
 * Flow:
 *   1. Parent sends { type: "exportPptx" } to iframe via postMessage
 *   2. Iframe loads dom-to-pptx CDN on demand, makes all slides visible
 *   3. dom-to-pptx traverses the DOM, extracts computed styles/coordinates
 *   4. Generates PPTX blob, sends ArrayBuffer back via postMessage
 *   5. Parent creates Blob and triggers browser download
 */

const EXPORT_TIMEOUT_MS = 120_000; // 2 minutes (CDN load + processing)

export function exportViaDomToPptx(
  iframeEl: HTMLIFrameElement,
  fileName: string,
  onStatus?: (msg: string) => void,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error("PPTX export timeout"));
    }, EXPORT_TIMEOUT_MS);

    function handler(e: MessageEvent) {
      if (e.data?.type === "pptxResult") {
        cleanup();
        const blob = new Blob([e.data.buffer], {
          type: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        });
        resolve(blob);
      } else if (e.data?.type === "pptxError") {
        cleanup();
        reject(new Error(e.data.error || "Export failed"));
      } else if (e.data?.type === "pptxStatus") {
        onStatus?.(e.data.message);
      }
    }

    function cleanup() {
      clearTimeout(timeout);
      window.removeEventListener("message", handler);
    }

    window.addEventListener("message", handler);
    iframeEl.contentWindow?.postMessage(
      { type: "exportPptx", fileName },
      "*",
    );
  });
}

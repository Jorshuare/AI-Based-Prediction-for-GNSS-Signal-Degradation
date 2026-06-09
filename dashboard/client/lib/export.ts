/** Client-side export helpers: CSV download and SVG→PNG snapshot. */

function trigger(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** Download an array of flat objects as a CSV file. */
export function downloadCSV(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  trigger(url, filename);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Rasterise an <svg> to a PNG and download it (white background, 2× for crispness). */
export async function downloadSvgAsPng(svg: SVGSVGElement, filename: string, scale = 2) {
  const rect = svg.getBoundingClientRect();
  const w = Math.max(rect.width, 1);
  const h = Math.max(rect.height, 1);
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("width", String(w));
  clone.setAttribute("height", String(h));
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const xml = new XMLSerializer().serializeToString(clone);
  const src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(xml)));
  const img = new Image();
  await new Promise<void>((res, rej) => { img.onload = () => res(); img.onerror = rej; img.src = src; });
  const canvas = document.createElement("canvas");
  canvas.width = w * scale;
  canvas.height = h * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.scale(scale, scale);
  ctx.drawImage(img, 0, 0);
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    trigger(url, filename);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, "image/png");
}

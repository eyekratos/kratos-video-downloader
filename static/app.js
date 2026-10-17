const $ = (id) => document.getElementById(id);
const urlInput = $("videoUrl"), inspectBtn = $("inspectBtn"), inspectLabel = $("inspectLabel");
const pasteBtn = $("pasteBtn"), statusBox = $("status"), result = $("result");
const titleEl = $("videoTitle"), detailsEl = $("videoDetails"), thumbnail = $("thumbnail");
const thumbFallback = $("thumbFallback"), quality = $("quality"), downloadBtn = $("downloadBtn");
let currentUrl = "", currentInfo = null;

function status(message, error = false) {
  statusBox.textContent = message;
  statusBox.className = "status" + (error ? " error" : "");
  statusBox.hidden = false;
}
function busyInspect(busy) {
  inspectBtn.disabled = busy;
  inspectLabel.textContent = busy ? "Checking link…" : "Find video";
}
pasteBtn.addEventListener("click", async () => {
  try { urlInput.value = await navigator.clipboard.readText(); urlInput.focus(); }
  catch { status("Clipboard access blocked. Paste the URL into the field manually."); }
});
urlInput.addEventListener("keydown", e => { if (e.key === "Enter") inspectBtn.click(); });

inspectBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  if (!url) return status("Pehle video URL paste karo.", true);
  if (!/^https:\/\//i.test(url)) return status("Please paste a full HTTPS link.", true);
  currentUrl = url; currentInfo = null; result.hidden = true; statusBox.hidden = true;
  busyInspect(true);
  try {
    const res = await fetch("/api/info", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url})});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not read this link.");
    currentInfo = data;
    titleEl.textContent = data.title || "Video";
    const meta = [];
    if (data.uploader) meta.push(data.uploader);
    if (data.duration) meta.push(Math.floor(data.duration / 60) + ":" + String(data.duration % 60).padStart(2, "0"));
    detailsEl.textContent = meta.join(" · ") || "Choose an available quality below.";
    if (data.thumbnail) {
      thumbnail.src = data.thumbnail; thumbnail.hidden = false; thumbFallback.hidden = true;
      thumbnail.onerror = () => { thumbnail.hidden = true; thumbFallback.hidden = false; };
    } else { thumbnail.hidden = true; thumbFallback.hidden = false; }
    quality.replaceChildren();
    const formats = data.formats || [];
    if (!formats.length) quality.add(new Option("Best available", ""));
    else formats.forEach(f => quality.add(new Option(f.label + (f.ext ? " · " + f.ext.toUpperCase() : ""), f.format_id)));
    result.hidden = false;
    status("Video details loaded. Choose a quality and download.");
    result.scrollIntoView({behavior:"smooth", block:"nearest"});
  } catch (err) { status(err.message || "Could not read this supported public link.", true); }
  finally { busyInspect(false); }
});

downloadBtn.addEventListener("click", async () => {
  if (!currentUrl || !currentInfo) return status("Find a video first.", true);
  downloadBtn.disabled = true; downloadBtn.textContent = "Preparing video…"; statusBox.hidden = true;
  try {
    const res = await fetch("/api/download", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url:currentUrl, format_id:quality.value || null})});
    if (!res.ok) {
      let message = "Download failed. Try another quality.";
      try { const data = await res.json(); message = data.detail || message; } catch {}
      throw new Error(message);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const a = document.createElement("a"), objectUrl = URL.createObjectURL(blob);
    a.href = objectUrl; a.download = match ? match[1] : "kratos-video.mp4";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    status("Download started. Check your browser's Downloads folder.");
  } catch (err) { status(err.message || "Download failed. The platform may not support this URL.", true); }
  finally { downloadBtn.disabled = false; downloadBtn.textContent = "Download ↓"; }
});
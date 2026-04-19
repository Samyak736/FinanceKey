function apiUrl(path) {
  const root = (typeof window !== "undefined" && window.__API_ROOT__) || "";
  const r = String(root).replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return r ? `${r}${p}` : p;
}

async function uploadFile(file) {
  const status = document.getElementById("status");
  status.textContent = "";
  status.className = "hint";
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(apiUrl("/api/upload"), { method: "POST", body: form });
  const ct = res.headers.get("content-type") || "";
  let data = {};
  if (ct.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = {};
    }
  } else {
    const t = await res.text();
    data = {
      error:
        (t && t.slice(0, 400)) ||
        res.statusText ||
        "Server did not return JSON (check app URL / reverse proxy).",
    };
  }
  if (!res.ok) {
    status.textContent = data.error || `Upload failed (${res.status})`;
    status.classList.add("error");
    return;
  }
  status.textContent = `Imported ${data.inserted} rows. Redirecting…`;
  status.classList.add("success");
  const dash =
    (typeof document !== "undefined" && document.body?.dataset?.dashboardUrl) || "/dashboard";
  setTimeout(() => {
    window.location.href = dash;
  }, 600);
}

function initUploadPage() {
  const fileInput = document.getElementById("file");
  const sampleBtn = document.getElementById("sample-btn");
  if (!fileInput || !sampleBtn) return;

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  });

  sampleBtn.addEventListener("click", async () => {
    const res = await fetch(apiUrl("/api/sample-csv"));
    if (!res.ok) {
      const status = document.getElementById("status");
      status.textContent = `Could not load sample (${res.status}). Check network / app URL.`;
      status.className = "hint error";
      return;
    }
    const blob = await res.blob();
    const file = new File([blob], "sample.csv", { type: "text/csv" });
    uploadFile(file);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initUploadPage);
} else {
  initUploadPage();
}

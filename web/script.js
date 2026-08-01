// web/script.js

// Truncate long values for UI
function clip(text, max = 256) {
  if (!text) return '';
  return text.length > max
    ? (text.slice(0, max) + `… (${text.length} chars)`)
    : text;
}

function makeUrl(path) {
  return path; // relative to same origin
}

// Escape user-controlled values before inserting into innerHTML to prevent XSS.
function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function authHeaders(extra = {}) {
  const token = localStorage.getItem('token');
  const headers = { ...extra };
  if (token) headers["Authorization"] = "Bearer " + token;
  return headers;
}

function tokenParam() {
  return '?token=' + encodeURIComponent(localStorage.getItem('token') || '');
}

// FastAPI reports failures as {detail: string} or {detail: [{msg, loc}, ...]}.
// Surface something a person can act on instead of a raw JSON blob.
async function readError(res) {
  const fallback = `Request failed (${res.status})`;
  let body;
  try { body = await res.text(); } catch (e) { return fallback; }
  if (!body) return fallback;

  try {
    const parsed = JSON.parse(body);
    const detail = parsed.detail ?? parsed.message;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
    }
  } catch (e) { /* not JSON — fall through to the raw body */ }

  return body.length > 200 ? fallback : body;
}

async function api(path, method = "GET", body = null) {
  const url = new URL(path, window.location.origin);
  const headers = authHeaders();
  const fetchOpts = { method, headers };

  if (body !== null) {
    headers["Content-Type"] = "application/json";
    fetchOpts.body = JSON.stringify(body);
  }

  const res = await fetch(url, fetchOpts);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

async function apiForm(path, formData) {
  const url = new URL(path, window.location.origin);

  const res = await fetch(url, { method: "POST", headers: authHeaders(), body: formData });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

function ensureAuth(expectedRole){
  const token = localStorage.getItem('token');
  const role  = localStorage.getItem('role');

  if (!token || !role || (expectedRole && role !== expectedRole)) {
    location.replace('/login');
  }
}

function logout(){
  localStorage.clear();
  location.href = "/login";
}


function prettyTime(ts) {
  if (!ts) return '';

  // Normalize UTC (fix timestamps missing 'Z')
  const iso = ts.endsWith('Z') ? ts : ts + 'Z';
  const d = new Date(iso);

  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// ─── Toast ───
// One polite live region per page; messages stack and self-dismiss.
function toast(message, kind = '') {
  let region = document.getElementById('toastRegion');
  if (!region) {
    region = document.createElement('div');
    region.id = 'toastRegion';
    region.className = 'toast-region';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    document.body.appendChild(region);
  }

  const el = document.createElement('div');
  el.className = kind ? `toast toast-${kind}` : 'toast';
  el.textContent = message;
  region.appendChild(el);

  setTimeout(() => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 200);
  }, kind === 'bad' ? 5200 : 3000);
}

// ─── Table states ───
// `hint` is inserted as HTML so callers can include <code>; pass literals only.
function tableSkeleton(tbody, cols, rows = 3) {
  const widths = ['w-60', 'w-80', 'w-40'];
  let html = '';
  for (let r = 0; r < rows; r++) {
    html += '<tr>';
    for (let c = 0; c < cols; c++) {
      html += `<td><span class="skel ${widths[(r + c) % widths.length]}"></span></td>`;
    }
    html += '</tr>';
  }
  tbody.innerHTML = html;
  const table = tbody.closest('table');
  if (table) table.setAttribute('aria-busy', 'true');
}

function tableState(tbody, cols, { title, hint = '', kind = '' } = {}) {
  const table = tbody.closest('table');
  if (table) table.removeAttribute('aria-busy');
  tbody.innerHTML = `
    <tr><td colspan="${cols}">
      <div class="state${kind === 'bad' ? ' state-bad' : ''}">
        <p class="state-title">${escapeHtml(title)}</p>
        ${hint ? `<p class="state-hint">${hint}</p>` : ''}
      </div>
    </td></tr>`;
}

function tableReady(tbody) {
  const table = tbody.closest('table');
  if (table) table.removeAttribute('aria-busy');
}

// ─── Busy buttons ───
// Swaps in a spinner for the duration of `fn`, then restores the label.
// Guards against double-submit by ignoring clicks while busy.
async function withBusy(btn, busyLabel, fn) {
  if (!btn) return fn();
  if (btn.dataset.busy) return;

  const original = btn.innerHTML;
  btn.dataset.busy = '1';
  btn.setAttribute('aria-busy', 'true');
  btn.innerHTML = `<span class="spinner" aria-hidden="true"></span>${escapeHtml(busyLabel)}`;

  try {
    return await fn();
  } finally {
    delete btn.dataset.busy;
    btn.removeAttribute('aria-busy');
    btn.innerHTML = original;
  }
}

// ─── File inputs echo the chosen filename ───
function initFileInputs(root = document) {
  root.querySelectorAll('.input-file input[type="file"]').forEach((input) => {
    if (input.dataset.echoBound) return;
    input.dataset.echoBound = '1';

    const wrap = input.closest('.input-file');
    const echo = wrap && wrap.querySelector('.file-name');
    if (!echo) return;

    const fallback = echo.dataset.default || echo.textContent;
    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      echo.textContent = file ? file.name : fallback;
      wrap.classList.toggle('has-file', Boolean(file));
      wrap.removeAttribute('aria-invalid');
    });
  });
}

// ─── Theme toggle ───
function currentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'light'
    ? 'light' : 'dark';
}

function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'light') root.setAttribute('data-theme', 'light');
  else root.removeAttribute('data-theme');
}

function updateThemeToggles() {
  const isLight = currentTheme() === 'light';
  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    btn.setAttribute('aria-label', isLight ? 'Switch to dark theme' : 'Switch to light theme');
    btn.setAttribute('aria-pressed', String(isLight));
  });
}

function setTheme(theme) {
  applyTheme(theme);
  try { localStorage.setItem('theme', theme); } catch (e) { /* storage blocked */ }
  updateThemeToggles();
}

function initThemeToggle() {
  updateThemeToggles();
  document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      setTheme(currentTheme() === 'light' ? 'dark' : 'light');
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initFileInputs();
});

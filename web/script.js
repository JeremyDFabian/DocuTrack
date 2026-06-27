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

async function api(path, method = "GET", body = null) {
  const url = new URL(path, window.location.origin);
  const headers = authHeaders();
  const fetchOpts = { method, headers };

  if (body !== null) {
    headers["Content-Type"] = "application/json";
    fetchOpts.body = JSON.stringify(body);
  }

  const res = await fetch(url, fetchOpts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function apiForm(path, formData) {
  const url = new URL(path, window.location.origin);

  const res = await fetch(url, { method: "POST", headers: authHeaders(), body: formData });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function ensureAuth(expectedRole){
  const token = localStorage.getItem('token');
  const role  = localStorage.getItem('role');

  if (!token || !role || (expectedRole && role !== expectedRole)) {
    alert("Please login");
    location.href = 'login.html';
  }
}

async function loadStudents(){
  const res = await api('/users/students');
  const sel = document.getElementById('students');
  if(sel){
    sel.innerHTML = '';
    res.forEach(s=>{
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = `${s.name} <${s.email}>`;
      sel.appendChild(opt);
    });
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

document.addEventListener('DOMContentLoaded', initThemeToggle);

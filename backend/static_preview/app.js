/** Shared helpers for the preview pages. */
const API_BASE = window.location.origin;

const ICON_MAP = {
  wear_gloves: 'hand', gloves: 'hand',
  cut: 'scissors', sharp: 'scissors',
  heat: 'flame', hot: 'flame',
  check: 'check-circle-2', inspect: 'search',
  power_off: 'power', power_on: 'power', power: 'power',
  electrical: 'zap', electricity: 'zap',
  chemical: 'flask-conical', chemicals: 'flask-conical',
  moving_parts: 'cog', machine: 'cog',
  wash_hands: 'droplets', water: 'droplets', clean: 'sparkles',
  measure: 'ruler', mix: 'blend', pour: 'droplet',
  wear_mask: 'shield', ppe: 'shield',
  warning: 'alert-triangle', careful: 'alert-triangle',
};

function iconFor(step) {
  const key = (step.icon || '').trim().toLowerCase();
  if (ICON_MAP[key]) return ICON_MAP[key];
  return step.is_safety_warning ? 'alert-triangle' : 'circle-dot';
}

const param = (name) => new URLSearchParams(location.search).get(name);

async function api(path, options) {
  const res = await fetch(API_BASE + path, options);
  if (!res.ok) throw new Error(`${path}: ${await res.text()}`);
  return res.json();
}

/* ---- staff session. Workers never have one; every access is guarded so that a
   browser with storage blocked still renders the worker pages. ---- */

const SESSION_KEY = 'v2sSession';

function session() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY)) || null;
  } catch {
    return null;
  }
}

function saveSession(data) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(data)); } catch {}
}

function signOut() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch {}
  location.href = 'index.html';
}

const token = () => session()?.token || null;

function authHeaders() {
  return { Authorization: `Bearer ${token()}` };
}

/** The page a role belongs on after signing in. */
function homeFor(role) {
  return role === 'supervisor' ? 'machines.html' : 'inbox.html';
}

/** Send anyone without one of these roles back to the sign-in page. */
function requireRole(...roles) {
  const who = session();
  if (!who || !roles.includes(who.role)) {
    location.href = 'index.html';
    return null;
  }
  return who;
}

/** api() with the token attached; an expired session returns to sign-in. */
async function apiAuth(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  });
  if (res.status === 401) {
    signOut();
    throw new Error('session expired');
  }
  if (!res.ok) throw new Error(`${path}: ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

async function getMachine(machineId) {
  const machines = await api('/api/machines');
  const machine = machines.find((m) => m.id === Number(machineId));
  if (!machine) throw new Error(`machine ${machineId} not found`);
  return machine;
}

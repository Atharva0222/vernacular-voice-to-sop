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

async function getMachine(machineId) {
  const machines = await api('/api/machines');
  const machine = machines.find((m) => m.id === Number(machineId));
  if (!machine) throw new Error(`machine ${machineId} not found`);
  return machine;
}

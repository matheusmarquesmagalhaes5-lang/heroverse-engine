// OmniRoute free-pool usage, sanitized (owner 2026-11-06: "administre os tokens agora junto com o omniroute").
// Runs ON THE OWNER'S PC (deployed as C:\HeroVerse\omni-usage.mjs): `node C:\HeroVerse\omni-usage.mjs`.
// Reads OmniRoute's local management API with OmniRoute's own per-install CLI token (derived by its
// bin/cli/utils/cliToken.mjs; never stored, never printed) and writes C:\HeroVerse\bridge\omni-usage.json.
// Output is an allowlist: provider names, counters, percentages, reset times, lockout model names.
// No API key, token, connection/account id, account name, e-mail or request body ever leaves this script.
// Cloud sessions read the JSON with Desktop Commander read_file, then run migration/ops/omniroute_snapshot.py.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const BASE = 'http://127.0.0.1:20128';
const COMBO = 'heroverse-fallback';
const OUT = process.argv[2] || 'C:\\HeroVerse\\bridge\\omni-usage.json';
const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const str = (v) => (typeof v === 'string' ? v.slice(0, 80) : null);
const out = { schema: 'omniroute-usage-v1', generated_at: new Date().toISOString(), combo: COMBO, up: false,
  errors: [], providers: {}, totals_24h: null, free_tier: null, alerts: [] };

let tok = '', header = 'x-omniroute-cli-token';
try {
  const root = path.join(process.env.APPDATA || '', 'npm', 'node_modules', 'omniroute');
  const m = await import(pathToFileURL(path.join(root, 'bin', 'cli', 'utils', 'cliToken.mjs')).href);
  tok = await m.getCliToken();
  header = m.CLI_TOKEN_HEADER || header;
} catch (e) { out.errors.push('cli_token_unavailable'); }

async function get(ep) {
  try {
    const r = await fetch(BASE + ep, { headers: { [header]: tok }, signal: AbortSignal.timeout(20000) });
    if (!r.ok) { out.errors.push(`${ep.split('?')[0]}:${r.status}`); return null; }
    return await r.json();
  } catch (e) { out.errors.push(`${ep.split('?')[0]}:${e.name === 'TimeoutError' ? 'timeout' : 'unreachable'}`); return null; }
}
const prov = (name) => (out.providers[name] ||= { connections: 0, quota_used: null, quota_pct_remaining: null,
  token_status: null, windows: {}, requests_24h: 0, errors_24h: 0, rate_limited_24h: 0, success_rate_pct_today: null,
  tokens_today: 0, lockouts: [] });

const quota = await get('/api/usage/quota');
out.up = !!quota;
const byConn = {};
for (const p of quota?.providers || []) {
  const name = str(p.provider); if (!name) continue;
  byConn[p.connectionId] = name;
  const x = prov(name);
  x.quota_used = num(p.quotaUsed); x.quota_pct_remaining = num(p.percentRemaining); x.token_status = str(p.tokenStatus);
}
const rl = await get('/api/rate-limits');
for (const c of rl?.connections || []) {
  const name = str(c.provider); if (!name) continue;
  byConn[c.connectionId] ||= name;
  prov(name).connections += 1;
}
for (const l of rl?.lockouts || []) {
  const name = str(l.provider); if (!name) continue;
  prov(name).lockouts.push({ model: str(l.model), reason: str(l.reason), remaining_s: Math.round((num(l.remainingMs) || 0) / 1000) });
}
const limits = await get('/api/usage/provider-limits');
for (const [id, c] of Object.entries(limits?.caches || {})) {
  const name = byConn[id]; if (!name) continue;
  for (const [w, q] of Object.entries(c.quotas || {})) {
    if (!q || typeof q !== 'object') continue;
    prov(name).windows[str(w)] = { used: num(q.used), total: num(q.total), remaining: num(q.remaining),
      remaining_pct: num(q.remainingPercentage), reset_at: str(q.resetAt), unlimited: q.unlimited === true };
  }
}
const logs = await get('/api/usage/call-logs?limit=1000');
const since = Date.now() - 24 * 3600 * 1000;
let req = 0, err = 0, r429 = 0;
// analytics names providers by display name; map them to the provider ids the other endpoints use
const display = { 'Gemini (Google AI Studio)': 'gemini', 'OpenRouter': 'openrouter', 'Cloudflare Workers AI': 'cloudflare-ai',
  'Cloudflare AI Playground': 'cloudflare-playground', 'Groq': 'groq', 'Cohere': 'cohere', 'UncloseAI': 'uncloseai' };
for (const l of Array.isArray(logs) ? logs : []) {
  if (str(l.providerDisplay) && str(l.provider)) display[str(l.providerDisplay)] = str(l.provider);
  if (Date.parse(l.timestamp) < since) continue;
  const name = str(l.provider) || 'unknown'; const x = prov(name); const s = Number(l.status) || 0;
  x.requests_24h += 1; req += 1;
  if (s >= 400 || s === 0) { x.errors_24h += 1; err += 1; }
  if (s === 429) { x.rate_limited_24h += 1; r429 += 1; }
}
const an = await get('/api/usage/analytics?period=day');
for (const p of an?.byProvider || []) {
  const d = str(p.provider); if (!d) continue;
  const name = display[d] || d.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const x = prov(name); x.tokens_today = num(p.totalTokens) || 0;
  x.success_rate_pct_today = num(Number(p.successRatePct));
}
out.totals_24h = { requests: req, errors: err, rate_limited: r429, sampled_max: 1000 };
const ft = await get('/api/free-tier/summary');
if (ft) out.free_tier = { headline: str(ft.headline), steady_recurring_tokens_month: num(ft.steadyRecurringTokens),
  model_count: num(ft.modelCount), catalog_updated_at: str(ft.catalogUpdatedAt) };

// alerts: OmniRoute down, a provider with an exhausted free window, or every provider exhausted/locked
if (!out.up) out.alerts.push('OMNIROUTE_DOWN');
const exhausted = [];
for (const [name, x] of Object.entries(out.providers)) {
  const dead = Object.values(x.windows).some((w) => !w.unlimited && w.total !== 0 && w.remaining_pct !== null && w.remaining_pct <= 0)
    || (x.quota_pct_remaining !== null && x.quota_pct_remaining <= 0)
    || (x.connections > 0 && x.token_status !== null && x.token_status !== 'valid');
  x.exhausted = dead;
  if (dead) exhausted.push(name);
}
if (exhausted.length) out.alerts.push('PROVIDER_EXHAUSTED:' + exhausted.sort().join(','));
const live = Object.values(out.providers).filter((x) => x.connections > 0);
if (out.up && live.length && live.every((x) => x.exhausted)) out.alerts.push('FREE_QUOTAS_EXHAUSTED');
if (req >= 20 && r429 / req > 0.3) out.alerts.push('HIGH_429_RATE');

let text = JSON.stringify(out, null, 1);
if (tok && text.includes(tok)) text = text.split(tok).join('<redacted>');
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, text + '\n');
console.log(`RESULT up=${out.up} providers=${Object.keys(out.providers).length} alerts=${out.alerts.join('|') || 'none'} -> ${OUT}`);

export const config = { runtime: 'edge' };

// Waitlist ingest — no Airtable, no third-party SaaS.
// Two opt-in backends, tried in order:
//   1. gtm-engine on Fly.io  (env: GTM_ENGINE_URL + GTM_ENGINE_TOKEN)
//      → full ICP scoring, deal pipeline, hot-lead Slack, KafCa events.
//   2. GitHub Issues         (env: GH_TOKEN + GH_REPO="owner/repo")
//      → each signup becomes one labeled issue in a repo you own.
//        Free forever, auditable, exportable via GitHub's own tools.
//
// If neither is configured (or both fail), we still return 200:
//   - Plausible has already recorded the WaitlistSignup event client-side
//   - The landing's localStorage queue is untouched
//   - You don't lose users to a backend hiccup

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'POST, OPTIONS',
  'access-control-allow-headers': 'content-type',
};

// Per-edge-instance IP throttle. Not distributed — good enough to
// block trivial abuse; pair with Vercel WAF for real DoS protection.
const seen = new Map();
function throttle(ip) {
  const now = Date.now();
  const last = seen.get(ip) || 0;
  if (now - last < 3000) return false;
  seen.set(ip, now);
  if (seen.size > 500) seen.clear();
  return true;
}

async function toGtmEngine({ email, source, plan, ua }) {
  const url = globalThis.process?.env?.GTM_ENGINE_URL;
  const token = globalThis.process?.env?.GTM_ENGINE_TOKEN;
  if (!url || !token) return { ok: false, skipped: true };
  const r = await fetch(`${url.replace(/\/$/, '')}/accounts`, {
    method: 'POST',
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: JSON.stringify({ email, source, plan, ua }),
  });
  if (!r.ok) throw new Error(`gtm-${r.status}`);
  return { ok: true, via: 'gtm-engine' };
}

async function toGithubIssues({ email, source, plan, ua, ip }) {
  const token = globalThis.process?.env?.GH_TOKEN;
  const repo = globalThis.process?.env?.GH_REPO; // "owner/repo"
  if (!token || !repo || !/^[\w.-]+\/[\w.-]+$/.test(repo)) return { ok: false, skipped: true };

  // Redact IP octet for privacy; keep source/plan searchable via labels.
  const ipMasked = ip.split('.').length === 4 ? ip.replace(/\.\d+$/, '.x') : 'redacted';
  const body = [
    `**Email**: ${email}`,
    `**Source**: ${source}`,
    `**Plan**: ${plan}`,
    `**UA**: ${ua || '(unknown)'}`,
    `**IP** (masked): ${ipMasked}`,
    `**Timestamp**: ${new Date().toISOString()}`,
  ].join('\n');

  const labels = ['waitlist', `source:${source}`, `plan:${plan}`].map(l => l.slice(0, 50));

  const r = await fetch(`https://api.github.com/repos/${repo}/issues`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      accept: 'application/vnd.github+json',
      'content-type': 'application/json',
      'x-github-api-version': '2022-11-28',
    },
    body: JSON.stringify({
      title: `waitlist: ${email}`,
      body,
      labels,
    }),
  });
  if (!r.ok) throw new Error(`gh-${r.status}`);
  return { ok: true, via: 'github-issues' };
}

async function persist({ email, source, plan, ua, ip }) {
  // Try in priority order. Return on first success.
  // Both backends are opt-in via env — skip cleanly if unconfigured.
  const attempts = [
    () => toGtmEngine({ email, source, plan, ua }),
    () => toGithubIssues({ email, source, plan, ua, ip }),
  ];
  const errors = [];
  for (const attempt of attempts) {
    try {
      const r = await attempt();
      if (r.ok) return { ok: true, via: r.via };
      if (r.skipped) continue;
    } catch (e) {
      errors.push(e?.message || String(e));
    }
  }
  return { ok: false, errors };
}

export default async function handler(req) {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  if (req.method !== 'POST') return json({ error: 'method-not-allowed' }, 405);

  const ip = req.headers.get('x-forwarded-for')?.split(',')[0].trim() || 'unknown';
  if (!throttle(ip)) return json({ error: 'rate-limited' }, 429);

  let body;
  try { body = await req.json(); } catch { return json({ error: 'invalid-json' }, 400); }
  const email = String(body?.email || '').trim().toLowerCase();
  if (!EMAIL_RE.test(email) || email.length > 200) return json({ error: 'invalid-email' }, 400);

  const source = String(body?.source || 'unknown').slice(0, 40);
  const plan = String(body?.plan || 'pro').slice(0, 20);
  const ua = req.headers.get('user-agent')?.slice(0, 200) || '';

  const result = await persist({ email, source, plan, ua, ip });

  // Return 200 either way — Plausible + landing localStorage already have
  // the signal. A backend hiccup should never look like a UI failure.
  if (result.ok) {
    return json({ ok: true, message: "You're in.", via: result.via }, 200);
  }
  console.warn('waitlist-nostore', { email, errors: result.errors });
  return json({ ok: true, message: "You're in. (queued)", via: 'client-queue' }, 200);
}

function json(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...CORS },
  });
}


;(() => {
  const SCRIPT = document.currentScript;
  const OPTS = {
    envEndpoint: (SCRIPT && SCRIPT.dataset.envEndpoint) || '/api/_audit/env',
    hideInProd: (SCRIPT && SCRIPT.dataset.hideInProd) === 'true',
    force: (SCRIPT && SCRIPT.dataset.force) === '1',
    position: (SCRIPT && SCRIPT.dataset.position) || 'br', // br, bl, tr, tl
  };

  const LS_KEY = 'empireDevBadges.hidden';

  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null) el.setAttribute(k, v);
    });
    children.filter(Boolean).forEach(c => {
      if (typeof c === 'string') el.appendChild(document.createTextNode(c));
      else el.appendChild(c);
    });
    return el;
  }

  function swatch(color) {
    return h('span', { class: 'emp-badge-swatch', style: { background: color || 'transparent' } });
  }

  function rootVar(name) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return v ? v.trim() : '';
  }

  function guessDbHost(env) {
    const e = env || {};
    const source = e.env && typeof e.env === 'object' ? e.env : e; // handle { env: {...} } or flat
    const keys = ['db_host','database_host','DB_HOST','DATABASE_HOST'];
    for (const k of keys) if (source[k]) return String(source[k]);
    const urlKeys = ['SUPABASE_URL','supabase_url','DATABASE_URL','database_url'];
    for (const k of urlKeys) {
      const v = source[k];
      if (typeof v === 'string') {
        try { return new URL(v).host; } catch {}
      }
    }
    return 'unknown';
  }

  function isProd(env) {
    const source = env && env.env ? env.env : env || {};
    const az = (source.AZURE_FUNCTIONS_ENVIRONMENT || '').toLowerCase();
    const node = (source.NODE_ENV || '').toLowerCase();
    if (az) return az === 'production';
    if (node) return node === 'production';
    // Heuristic: Azure *.azurewebsites.net usually production
    return /azurewebsites\.net$/i.test(location.hostname);
  }

  async function fetchEnv() {
    try {
      const r = await fetch(OPTS.envEndpoint, { headers: { 'Accept': 'application/json' } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.json();
    } catch (e) {
      return { error: String(e) };
    }
  }

  function mountBadges(env) {
    if (OPTS.hideInProd && !OPTS.force && isProd(env)) {
      // Hidden in prod unless data-force="1"
      return;
    }
    if (localStorage.getItem(LS_KEY) === '1') return;

    const themeColor = rootVar('--color-card-bg') || rootVar('--surface');
    const dbHost = guessDbHost(env);

    const container = h('div', { id: 'emp-dev-badges', class: `emp-pos-${OPTS.position}` });
    const theme = h('div', { class: 'emp-badge' },
      h('span', { class: 'emp-badge-label' }, 'Theme'),
      swatch(themeColor),
      h('span', { class: 'emp-badge-value' }, themeColor || '(unset)')
    );
    const db = h('div', { class: 'emp-badge' },
      h('span', { class: 'emp-badge-label' }, 'DB'),
      h('span', { class: 'emp-badge-value' }, dbHost)
    );
    const close = h('button', { class: 'emp-badge-close', title: 'Hide (Alt+D)' }, '×');
    close.addEventListener('click', () => {
      container.remove();
      localStorage.setItem(LS_KEY, '1');
    });

    container.append(theme, db, close);
    document.body.appendChild(container);

    // Live update theme swatch if CSS var changes
    const obs = new MutationObserver(() => {
      const c = rootVar('--color-card-bg') || themeColor;
      theme.querySelector('.emp-badge-swatch').style.background = c;
      theme.querySelector('.emp-badge-value').textContent = c;
    });
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['style','class'] });

    // Keyboard toggle
    window.addEventListener('keydown', (e) => {
      if (e.altKey && (e.key === 'd' || e.key === 'D')) {
        const el = document.getElementById('emp-dev-badges');
        if (el) { el.remove(); localStorage.setItem(LS_KEY, '1'); }
        else { localStorage.removeItem(LS_KEY); mountBadges(env); }
      }
    });
  }

  // Inject CSS (works even if CSS file wasn’t included)
  const CSS = `
  #emp-dev-badges {
    position: fixed; z-index: 2147483647; display: inline-flex; gap: 8px; padding: 8px 10px;
    background: rgba(0,0,0,0.5); backdrop-filter: blur(6px); border-radius: 12px; align-items: center;
    font: 12px/1.2 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    color: #fff; box-shadow: 0 4px 18px rgba(0,0,0,0.25);
  }
  .emp-pos-br { right: 14px; bottom: 14px; }
  .emp-pos-bl { left: 14px; bottom: 14px; }
  .emp-pos-tr { right: 14px; top: 14px; }
  .emp-pos-tl { left: 14px; top: 14px; }

  .emp-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 10px;
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); }
  .emp-badge-label { opacity: 0.75; text-transform: uppercase; letter-spacing: .06em; font-size: 10px; }
  .emp-badge-swatch { width: 14px; height: 14px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3); display: inline-block; }
  .emp-badge-value { font-weight: 600; }
  .emp-badge-close { margin-left: 2px; width: 22px; height: 22px; border-radius: 6px; border: none; cursor: pointer;
    color: #fff; background: rgba(255,255,255,0.12); }
  .emp-badge-close:hover { background: rgba(255,255,255,0.22); }
  `;
  const style = document.createElement('style'); style.textContent = CSS; document.head.appendChild(style);

  // Boot
  fetchEnv().then(env => mountBadges(env));
})();
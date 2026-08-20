// ── Org chart: tidy SVG tree with pan, zoom, collapse and colour-by ────────
(() => {
  const { API, Fmt, state, query, colorFor } = OrgApp;

  const NODE_W = 216, NODE_H = 88;
  const SIB_GAP = 26, LEVEL_GAP = 58;     // vertical layout
  const H_SIB_GAP = 14, H_LEVEL_GAP = 76; // horizontal layout
  const HANG_INDENT = 40, HANG_GAP = 10, HANG_TRUNK = 20;  // compact leaf columns
  const SOFT_NODE_LIMIT = 1400;   // beyond this, panning gets sluggish
  const DEFAULT_VISIBLE = 60;     // nodes to show before the first expand
  const MIN_ZOOM = 0.02;

  const DIMS = [
    ['function', 'Function'], ['department', 'Department'], ['division', 'Division'],
    ['job_level', 'Job Level'], ['job_family', 'Job Family'], ['location', 'Location'],
    ['employment_type', 'Employment Type'], ['vacancy', 'Vacancy'], ['none', 'None'],
  ];

  let tree = null;          // { roots, count, breadcrumb }
  let nodesById = new Map();
  let lastPlaced = [];      // nodes drawn in the latest pass — collapsed ones keep
                            // stale coordinates, which would corrupt fit()
  let view = { x: 0, y: 0, k: 1 };
  let paletteValues = [];   // ordered values for the active colour dimension
  let legendCollapsed = false;

  // ── Rendering shell ──────────────────────────────────────────────────────
  function render() {
    return `
      <div id="chart-shell">
        <div id="chart-toolbar">
          <div class="toolbar-group">
            <button class="btn btn-sm" id="c-expand" title="Expand every branch">Expand all</button>
            <button class="btn btn-sm" id="c-collapse" title="Show top levels only">Collapse</button>
          </div>
          <label class="field compact">
            <span>Colour by</span>
            <select id="c-color">
              ${DIMS.map(([k, l]) => `<option value="${k}"${state.colorBy === k ? ' selected' : ''}>${l}</option>`).join('')}
            </select>
          </label>
          <div class="toolbar-group">
            <button class="btn btn-sm" id="c-compact" title="Hang single-level teams in a column">${state.compact ? '⊟' : '⊞'}</button>
            <button class="btn btn-sm" id="c-orient" title="Switch orientation">${state.orientation === 'vertical' ? '↕' : '↔'}</button>
            <button class="btn btn-sm" id="c-zoom-out" title="Zoom out">−</button>
            <button class="btn btn-sm" id="c-zoom-in" title="Zoom in">+</button>
            <button class="btn btn-sm" id="c-fit" title="Fit to screen">Fit</button>
          </div>
          <div class="toolbar-spacer"></div>
          <div id="chart-crumb"></div>
          <button class="btn btn-sm" id="c-svg" title="Download the chart as SVG">⬇ SVG</button>
        </div>
        <svg id="chart-canvas"><g id="chart-root"></g></svg>
        <div id="chart-legend" class="hidden"></div>
        <div id="chart-status"></div>
      </div>`;
  }

  async function init() {
    tree = await API.get('/api/org/tree' + query({ root: state.rootId }));
    indexTree();
    applyDefaultCollapse();
    wire();
    draw();
    fit();
  }

  function indexTree() {
    nodesById = new Map();
    const walk = (n, depth, parent) => {
      n._depth = depth;
      n._parent = parent;
      nodesById.set(n.employee_id, n);
      (n.children || []).forEach(c => walk(c, depth + 1, n));
    };
    tree.roots.forEach(r => walk(r, 0, null));
  }

  // Open three layers by default, going deeper only while the result still fits
  // on screen — a fully expanded large org zooms out past the point of legibility.
  function applyDefaultCollapse() {
    if (state.collapsed.size) return;
    if (nodesById.size <= DEFAULT_VISIBLE) return;   // small org: show everything

    let depthLimit = 3;
    while (depthLimit < 40 && countVisible(depthLimit + 1) <= DEFAULT_VISIBLE) depthLimit++;

    nodesById.forEach(n => {
      if (n._depth >= depthLimit - 1 && (n.children || []).length) state.collapsed.add(n.employee_id);
    });
  }

  function countVisible(maxDepth) {
    let n = 0;
    nodesById.forEach(node => { if (node._depth < maxDepth) n++; });
    return n;
  }

  const visibleChildren = n =>
    state.collapsed.has(n.employee_id) ? [] : (n.children || []);

  // ── Layout ───────────────────────────────────────────────────────────────
  // Leaves are placed sequentially and parents centred over their children:
  // not the most compact arrangement possible, but it cannot produce overlaps.
  // A manager whose visible children are all leaves gets them hung in a single
  // indented column instead — a team of 12 ICs would otherwise stretch the
  // canvas so wide that fitting it to screen makes every card unreadable.
  function layout() {
    const horizontal = state.orientation === 'horizontal';
    const step  = horizontal ? NODE_H + H_SIB_GAP : NODE_W + SIB_GAP;
    const level = horizontal ? NODE_W + H_LEVEL_GAP : NODE_H + LEVEL_GAP;

    const placed = [];
    let cursor = 0;

    const canHang = kids =>
      state.compact && !horizontal && kids.length >= 3 &&
      kids.every(k => !visibleChildren(k).length);

    const put = (n, seq, depth) => {
      n._x = horizontal ? depth * level : seq;
      n._y = horizontal ? seq : depth * level;
      n._hang = false;
      placed.push(n);
    };

    const walk = (n, depth) => {
      const kids = visibleChildren(n);
      let seq;

      if (!kids.length) {
        seq = cursor;
        cursor += step;
        put(n, seq, depth);
      } else if (canHang(kids)) {
        seq = cursor;
        cursor += step + HANG_INDENT;   // the column sits inside the parent's slot
        put(n, seq, depth);
        kids.forEach((k, i) => {
          k._x = n._x + HANG_INDENT;
          k._y = n._y + NODE_H + LEVEL_GAP / 2 + i * (NODE_H + HANG_GAP);
          k._hang = true;
          placed.push(k);
        });
      } else {
        const spans = kids.map(k => walk(k, depth + 1));
        seq = (spans[0] + spans[spans.length - 1]) / 2;
        put(n, seq, depth);
      }
      return seq;
    };

    tree.roots.forEach(r => {
      walk(r, 0);
      cursor += step;   // gap between separate top-level trees
    });
    lastPlaced = placed;
    return placed;
  }

  // ── Colour ───────────────────────────────────────────────────────────────
  function colorKeyOf(node) {
    if (state.colorBy === 'none') return null;
    if (state.colorBy === 'vacancy') return node.is_vacant ? 'Vacant' : 'Filled';
    return node[state.colorBy] || 'Unspecified';
  }

  function buildPalette() {
    const counts = new Map();
    nodesById.forEach(n => {
      const k = colorKeyOf(n);
      if (k) counts.set(k, (counts.get(k) || 0) + 1);
    });
    paletteValues = [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([k]) => k);
    return counts;
  }

  function nodeColor(node) {
    if (state.colorBy === 'none') return 'var(--primary)';
    if (state.colorBy === 'vacancy') return node.is_vacant ? '#f59e0b' : '#22c55e';
    return colorFor(colorKeyOf(node), paletteValues);
  }

  // ── Draw ─────────────────────────────────────────────────────────────────
  function draw() {
    const nodes = layout();
    const counts = buildPalette();
    const root = document.getElementById('chart-root');

    const links = [];
    nodes.forEach(n => visibleChildren(n).forEach(c => links.push(linkPath(n, c))));

    root.innerHTML =
      `<g class="links">${links.join('')}</g>` +
      `<g class="nodes">${nodes.map(nodeSvg).join('')}</g>`;

    root.querySelectorAll('.node-card').forEach(el => {
      el.addEventListener('click', () => OrgApp.showEmployee(el.dataset.id));
    });
    root.querySelectorAll('.toggle-btn').forEach(el => {
      el.addEventListener('click', e => {
        e.stopPropagation();
        const id = el.dataset.id;
        state.collapsed.has(id) ? state.collapsed.delete(id) : state.collapsed.add(id);
        draw();
      });
    });

    drawLegend(counts);
    drawCrumb();
    document.getElementById('chart-status').textContent =
      `${Fmt.int(nodes.length)} of ${Fmt.int(tree.count)} shown` +
      (nodes.length > SOFT_NODE_LIMIT ? ' · collapse branches for smoother panning' : '');
    applyTransform();
  }

  function linkPath(parent, child) {
    if (child._hang) {
      const x = parent._x + HANG_TRUNK;
      return `<path class="link" d="M${x},${parent._y + NODE_H} V${child._y + NODE_H / 2} H${child._x}"/>`;
    }
    if (state.orientation === 'horizontal') {
      const x1 = parent._x + NODE_W, y1 = parent._y + NODE_H / 2;
      const x2 = child._x, y2 = child._y + NODE_H / 2;
      const mid = x1 + H_LEVEL_GAP / 2;
      return `<path class="link" d="M${x1},${y1} H${mid} V${y2} H${x2}"/>`;
    }
    const x1 = parent._x + NODE_W / 2, y1 = parent._y + NODE_H;
    const x2 = child._x + NODE_W / 2, y2 = child._y;
    const mid = y1 + LEVEL_GAP / 2;
    return `<path class="link" d="M${x1},${y1} V${mid} H${x2} V${y2}"/>`;
  }

  // Rough width measure — SVG text has no wrapping, so clip by estimated px.
  function trim(text, maxPx, size) {
    const s = String(text ?? '');
    const max = Math.floor(maxPx / (size * 0.54));
    return s.length > max ? s.slice(0, Math.max(1, max - 1)) + '…' : s;
  }

  function nodeSvg(n) {
    const kids = (n.children || []).length;
    const collapsed = state.collapsed.has(n.employee_id);
    const accent = nodeColor(n);
    const hc = n.total_headcount;
    const meta = [n.function, n.job_level, n.location].filter(Boolean).join(' · ');
    const pillW = Math.max(26, String(Fmt.int(hc)).length * 7 + 16);

    const hangingKids = !collapsed && state.compact && state.orientation === 'vertical' &&
                        (n.children || []).some(c => c._hang);
    const toggle = kids ? (() => {
      const cx = state.orientation === 'horizontal' ? n._x + NODE_W
               : hangingKids ? n._x + HANG_TRUNK : n._x + NODE_W / 2;
      const cy = state.orientation === 'horizontal' ? n._y + NODE_H / 2 : n._y + NODE_H;
      return `
        <g class="toggle-btn" data-id="${Fmt.esc(n.employee_id)}" transform="translate(${cx},${cy})">
          <circle class="toggle-circle" r="10"/>
          <text class="toggle-sign" y="4">${collapsed ? '+' : '−'}</text>
          ${collapsed ? `<text class="toggle-count" y="24">${Fmt.int(n.total_reports)}</text>` : ''}
        </g>`;
    })() : '';

    return `
      <g class="node-card${n.is_vacant ? ' node-vacant' : ''}${state.selectedId === n.employee_id ? ' selected' : ''}"
         data-id="${Fmt.esc(n.employee_id)}" transform="translate(${n._x},${n._y})">
        <rect class="node-box" width="${NODE_W}" height="${NODE_H}"/>
        <rect class="node-accent" x="0" y="10" width="4" height="${NODE_H - 20}" fill="${accent}"/>
        <text class="node-name"  x="14" y="24">${Fmt.esc(trim(n.name, NODE_W - 34 - pillW, 13))}</text>
        <text class="node-title" x="14" y="42">${Fmt.esc(trim(n.job_title || '—', NODE_W - 28, 11))}</text>
        <text class="node-meta"  x="14" y="59">${Fmt.esc(trim(meta || '—', NODE_W - 28, 10))}</text>
        <text class="node-meta"  x="14" y="76">${Fmt.int(n.direct_reports)} direct${n.direct_reports === 1 ? '' : 's'}${n.total_vacant ? ` · ${Fmt.int(n.total_vacant)} vacant` : ''}</text>
        <rect class="node-hc-bg" x="${NODE_W - pillW - 10}" y="12" width="${pillW}" height="18"/>
        <text class="node-hc-text" x="${NODE_W - pillW / 2 - 10}" y="25" text-anchor="middle">${Fmt.int(hc)}</text>
      </g>${toggle}`;
  }

  function drawLegend(counts) {
    const el = document.getElementById('chart-legend');
    if (state.colorBy === 'none' || !paletteValues.length) {
      el.classList.add('hidden');
      return;
    }
    const label = (DIMS.find(d => d[0] === state.colorBy) || [, ''])[1];
    el.classList.remove('hidden');
    el.classList.toggle('collapsed', legendCollapsed);
    el.innerHTML = `<div class="legend-title" id="legend-toggle">${label}
        <span class="legend-caret">${legendCollapsed ? '▸' : '▾'}</span></div>` +
      (legendCollapsed ? '' :
      paletteValues.slice(0, 18).map(v => `
        <div class="legend-item">
          <span class="legend-swatch" style="background:${
            state.colorBy === 'vacancy' ? (v === 'Vacant' ? '#f59e0b' : '#22c55e') : colorFor(v, paletteValues)
          }"></span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${Fmt.esc(v)}</span>
          <span class="text-muted">${Fmt.int(counts.get(v) || 0)}</span>
        </div>`).join('') +
      (paletteValues.length > 18 ? `<div class="legend-item text-muted">+${paletteValues.length - 18} more</div>` : ''));

    document.getElementById('legend-toggle').addEventListener('click', () => {
      legendCollapsed = !legendCollapsed;
      drawLegend(counts);
    });
  }

  function drawCrumb() {
    const el = document.getElementById('chart-crumb');
    if (!state.rootId) { el.innerHTML = ''; return; }
    const chain = tree.breadcrumb || [];
    el.innerHTML = `
      <div class="breadcrumb card" style="padding:5px 10px">
        <a id="crumb-all">Whole org</a>
        ${chain.map(c => `<span class="sep">›</span><a data-focus="${Fmt.esc(c.employee_id)}">${Fmt.esc(c.name || c.employee_id)}</a>`).join('')}
      </div>`;
    document.getElementById('crumb-all').addEventListener('click', () => {
      state.rootId = null;
      state.collapsed.clear();
      OrgApp.render();
    });
  }

  // ── Pan / zoom ───────────────────────────────────────────────────────────
  function applyTransform() {
    document.getElementById('chart-root')
      .setAttribute('transform', `translate(${view.x},${view.y}) scale(${view.k})`);
  }

  function bounds() {
    const nodes = lastPlaced;
    if (!nodes.length) return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
    return {
      minX: Math.min(...nodes.map(n => n._x)),
      minY: Math.min(...nodes.map(n => n._y)),
      maxX: Math.max(...nodes.map(n => n._x)) + NODE_W,
      maxY: Math.max(...nodes.map(n => n._y)) + NODE_H,
    };
  }

  function fit() {
    const svg = document.getElementById('chart-canvas');
    const r = svg.getBoundingClientRect();
    const b = bounds();
    const pad = 60;
    const k = Math.min((r.width - pad) / (b.maxX - b.minX || 1),
                       (r.height - pad) / (b.maxY - b.minY || 1), 1.1);
    view.k = Math.max(MIN_ZOOM, k);
    view.x = (r.width - (b.maxX - b.minX) * view.k) / 2 - b.minX * view.k;
    view.y = (r.height - (b.maxY - b.minY) * view.k) / 2 - b.minY * view.k;
    applyTransform();
  }

  function zoomAt(factor, cx, cy) {
    const k = Math.min(2.5, Math.max(MIN_ZOOM, view.k * factor));
    view.x = cx - (cx - view.x) * (k / view.k);
    view.y = cy - (cy - view.y) * (k / view.k);
    view.k = k;
    applyTransform();
  }

  function wire() {
    const svg = document.getElementById('chart-canvas');

    let dragging = false, last = null;
    const start = (x, y) => { dragging = true; last = { x, y }; svg.classList.add('dragging'); };
    const move = (x, y) => {
      if (!dragging) return;
      view.x += x - last.x;
      view.y += y - last.y;
      last = { x, y };
      applyTransform();
    };
    const end = () => { dragging = false; svg.classList.remove('dragging'); };

    svg.addEventListener('mousedown', e => { if (e.button === 0) start(e.clientX, e.clientY); });
    window.addEventListener('mousemove', e => move(e.clientX, e.clientY));
    window.addEventListener('mouseup', end);

    svg.addEventListener('touchstart', e => {
      if (e.touches.length === 1) start(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    svg.addEventListener('touchmove', e => {
      if (e.touches.length === 1) move(e.touches[0].clientX, e.touches[0].clientY);
    }, { passive: true });
    svg.addEventListener('touchend', end);

    svg.addEventListener('wheel', e => {
      e.preventDefault();
      const r = svg.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });

    const center = () => {
      const r = svg.getBoundingClientRect();
      return [r.width / 2, r.height / 2];
    };
    document.getElementById('c-zoom-in').addEventListener('click', () => zoomAt(1.25, ...center()));
    document.getElementById('c-zoom-out').addEventListener('click', () => zoomAt(0.8, ...center()));
    document.getElementById('c-fit').addEventListener('click', fit);

    document.getElementById('c-expand').addEventListener('click', () => {
      state.collapsed.clear();
      draw();
      fit();
    });
    document.getElementById('c-collapse').addEventListener('click', () => {
      state.collapsed.clear();
      nodesById.forEach(n => {
        if (n._depth >= 1 && (n.children || []).length) state.collapsed.add(n.employee_id);
      });
      draw();
      fit();
    });
    document.getElementById('c-color').addEventListener('change', e => {
      state.colorBy = e.target.value;
      draw();
    });
    document.getElementById('c-compact').addEventListener('click', () => {
      state.compact = !state.compact;
      document.getElementById('c-compact').textContent = state.compact ? '⊟' : '⊞';
      draw();
      fit();
    });
    document.getElementById('c-orient').addEventListener('click', () => {
      state.orientation = state.orientation === 'vertical' ? 'horizontal' : 'vertical';
      document.getElementById('c-orient').textContent = state.orientation === 'vertical' ? '↕' : '↔';
      draw();
      fit();
    });
    document.getElementById('c-svg').addEventListener('click', downloadSvg);
  }

  // ── Export ───────────────────────────────────────────────────────────────
  function downloadSvg() {
    const b = bounds();
    const pad = 30;
    const w = b.maxX - b.minX + pad * 2, h = b.maxY - b.minY + pad * 2;
    const inner = document.getElementById('chart-root').innerHTML;

    // Inline the theme colours: the exported file has no access to our stylesheet.
    const css = `
      .link{fill:none;stroke:#3a3a58;stroke-width:1.4}
      .node-box{fill:#0f0f1a;stroke:#2a2a45;rx:9}
      .node-vacant .node-box{stroke:#f59e0b;stroke-dasharray:4 3}
      .node-name{fill:#f0f0f8;font-size:13px;font-weight:600}
      .node-title{fill:#94a3b8;font-size:11px}
      .node-meta{fill:#55607a;font-size:10px}
      .node-hc-bg{fill:#1e1e35;rx:9}
      .node-hc-text{fill:#a5b4fc;font-size:10px;font-weight:700}
      .toggle-circle{fill:#14142a;stroke:#3a3a58}
      .toggle-sign{fill:#94a3b8;font-size:12px;font-weight:700;text-anchor:middle}
      .toggle-count{fill:#55607a;font-size:9px;text-anchor:middle}
      text{font-family:system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}`;

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
      <style>${css}</style><rect width="${w}" height="${h}" fill="#09090f"/>
      <g transform="translate(${pad - b.minX},${pad - b.minY})">${inner}</g></svg>`;

    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'org-chart.svg';
    a.click();
    URL.revokeObjectURL(url);
  }

  // Let the app redraw the chart when the selected person changes.
  OrgApp.refreshChartSelection = () => { if (tree) draw(); };

  OrgApp.registerView('chart', { render, init });
})();

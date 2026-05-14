VIZ_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Graph Memory</title>
  <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f1117;color:#e0e0e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}

    header{display:flex;align-items:center;gap:10px;padding:9px 16px;background:#1a1d27;border-bottom:1px solid #2a2d3e;flex-shrink:0;flex-wrap:wrap}
    header h1{font-size:14px;font-weight:700;color:#a78bfa;white-space:nowrap;margin-right:4px}
    .stats{display:flex;gap:12px;font-size:12px;color:#555;flex:1}
    .stats b{color:#ccc}
    .badge-live{padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;background:#14532d;color:#4ade80;letter-spacing:.5px;animation:pulse 2s infinite;white-space:nowrap}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}

    /* Style selector */
    .style-group{display:flex;gap:3px;background:#12151f;border:1px solid #2a2d3e;border-radius:7px;padding:3px}
    .style-btn{padding:4px 10px;border-radius:5px;border:none;cursor:pointer;font-size:11px;font-weight:500;background:transparent;color:#666;transition:all .15s;white-space:nowrap}
    .style-btn:hover{background:#2a2d3e;color:#ccc}
    .style-btn.active{background:#4c1d95;color:#c4b5fd}

    /* Action buttons */
    .btn{padding:4px 11px;border-radius:6px;border:1px solid #3a3d4e;cursor:pointer;font-size:11px;font-weight:500;transition:all .15s;background:#2a2d3e;color:#ccc;white-space:nowrap}
    .btn:hover{background:#3a3d4e;color:#fff}
    .btn-purple{background:#4c1d95;border-color:#6d28d9;color:#c4b5fd}
    .btn-purple:hover{background:#5b21b6}
    .btn-red{background:#450a0a;border-color:#b91c1c;color:#fca5a5}
    .btn-red:hover{background:#7f1d1d}
    .btn-green{background:#052e16;border-color:#15803d;color:#86efac}
    .btn-green:hover{background:#14532d}
    .btn-amber{background:#451a03;border-color:#b45309;color:#fcd34d}
    .btn-amber:hover{background:#7c2d12}

    .main{display:flex;flex:1;overflow:hidden}
    #network{flex:1;background:radial-gradient(ellipse at center,#141720 0%,#0f1117 100%);transition:background .3s}
    #network.tree-mode{background:radial-gradient(ellipse at center,#0d1520 0%,#0a0f17 100%)}

    .sidebar{width:270px;background:#1a1d27;border-left:1px solid #2a2d3e;display:flex;flex-direction:column;flex-shrink:0;overflow:hidden}
    .sb-section{padding:10px 13px;border-bottom:1px solid #2a2d3e}
    .sb-section h3{font-size:9px;text-transform:uppercase;letter-spacing:1px;color:#444;margin-bottom:7px}

    .legend-item{display:flex;align-items:center;gap:7px;margin-bottom:4px;font-size:11px}
    .legend-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}

    #detail-panel{flex:1;padding:11px 13px;overflow-y:auto}
    #detail-panel h3{font-size:9px;text-transform:uppercase;letter-spacing:1px;color:#444;margin-bottom:7px}
    .detail-name{font-size:16px;font-weight:700;color:#fff;margin-bottom:2px;display:flex;align-items:center;gap:6px}
    .edit-btn{background:none;border:none;color:#444;cursor:pointer;padding:2px 4px;border-radius:4px;font-size:12px;transition:color .15s}
    .edit-btn:hover{color:#a78bfa;background:#2a2d3e}
    .edit-input{background:#12151f;border:1px solid #6d28d9;border-radius:5px;color:#fff;font-size:15px;font-weight:700;padding:2px 7px;width:100%;outline:none}
    .edit-actions{display:flex;gap:4px;margin-top:5px;margin-bottom:2px}
    .edit-actions button{padding:3px 9px;font-size:10px}
    .detail-type{font-size:9px;color:#444;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}

    .rel-row{display:flex;align-items:center;gap:6px;margin-bottom:5px;padding:5px 7px;background:#12151f;border-radius:5px;font-size:11px}
    .rel-pred{color:#a78bfa;font-size:9px;font-weight:600;display:block;margin-bottom:1px}
    .rel-del{margin-left:auto;padding:1px 6px;font-size:9px;border-radius:3px;border:1px solid #7f1d1d;background:#450a0a;color:#fca5a5;cursor:pointer;flex-shrink:0;opacity:0;transition:opacity .15s}
    .rel-row:hover .rel-del{opacity:1}

    .sb-actions{padding:8px 12px;border-top:1px solid #2a2d3e;display:flex;flex-direction:column;gap:5px}

    /* Isolated mode indicator */
    #isolated-bar{display:none;background:#451a03;border-bottom:1px solid #b45309;padding:5px 16px;font-size:12px;color:#fcd34d;align-items:center;gap:10px;flex-shrink:0}
    #isolated-bar.visible{display:flex}

    /* Modal */
    .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}
    .overlay.open{display:flex}
    .modal{background:#1a1d27;border:1px solid #2a2d3e;border-radius:10px;padding:22px;width:370px;max-width:95vw}
    .modal h2{font-size:14px;font-weight:700;margin-bottom:16px;color:#a78bfa}
    .field{margin-bottom:12px}
    .field label{display:block;font-size:10px;color:#555;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px}
    .field input,.field select{width:100%;padding:6px 9px;background:#12151f;border:1px solid #2a2d3e;border-radius:5px;color:#ddd;font-size:12px;outline:none}
    .field input:focus,.field select:focus{border-color:#6d28d9}
    .field select option{background:#1a1d27}
    .modal-btns{display:flex;gap:7px;margin-top:16px}
    .modal-btns .btn{flex:1;padding:7px}

    .confirm-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:150;align-items:center;justify-content:center}
    .confirm-overlay.open{display:flex}
    .confirm-box{background:#1a1d27;border:1px solid #b91c1c;border-radius:9px;padding:20px;width:300px;text-align:center}
    .confirm-box p{margin-bottom:14px;font-size:13px;color:#ddd;line-height:1.5}
    .confirm-btns{display:flex;gap:8px}
    .confirm-btns .btn{flex:1;padding:7px}

    #toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1a1d27;border:1px solid #2a2d3e;color:#ddd;padding:7px 16px;border-radius:7px;font-size:12px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:200}
    #toast.show{opacity:1}

    .meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 8px;margin:8px 0;padding:7px 9px;background:#12151f;border-radius:5px;border:1px solid #1e2130}
    .meta-cell{display:flex;flex-direction:column;gap:1px}
    .meta-lbl{font-size:8px;text-transform:uppercase;letter-spacing:.8px;color:#444}
    .meta-val{font-size:11px;color:#a78bfa;font-weight:600}
    .meta-full{grid-column:1/-1}
  </style>
</head>
<body>

<header>
  <h1>⬡ Graph Memory</h1>

  <div class="stats">
    <span>Nodos: <b id="node-count">0</b></span>
    <span>Relaciones: <b id="edge-count">0</b></span>
    <span class="badge-live">● LIVE</span>
  </div>

  <!-- Style selector -->
  <div class="style-group" title="Estilo de visualización">
    <button class="style-btn active" onclick="applyStyle('fisica')"    id="s-fisica">🌐 Física</button>
    <button class="style-btn"        onclick="applyStyle('arbol_ud')"  id="s-arbol_ud">🌳 Árbol ↕</button>
    <button class="style-btn"        onclick="applyStyle('arbol_lr')"  id="s-arbol_lr">🌳 Árbol →</button>
    <button class="style-btn"        onclick="applyStyle('disperso')"  id="s-disperso">💨 Disperso</button>
  </div>

  <button class="btn" onclick="network && network.fit()">⊡ Centrar</button>
  <button class="btn btn-purple" onclick="openAddModal()">＋ Relación</button>
  <button class="btn btn-red"    onclick="confirmClear()">🗑 Borrar todo</button>
</header>

<!-- Isolated mode bar -->
<div id="isolated-bar">
  <span id="isolated-label">Rama aislada</span>
  <button class="btn btn-green" onclick="showAll()" style="padding:2px 10px;font-size:11px">↩ Mostrar todo el grafo</button>
</div>

<div class="main">
  <div id="network"></div>

  <div class="sidebar">
    <div class="sb-section">
      <h3>Tipos de nodo</h3>
      <div id="legend"></div>
    </div>

    <div id="detail-panel">
      <h3>Detalle</h3>
      <div id="detail-content" style="color:#333;font-size:12px">Haz clic en un nodo o relación.</div>
    </div>

    <div class="sb-actions" id="node-actions" style="display:none">
      <button class="btn btn-amber" id="isolate-btn" onclick="isolateSelected()">◎ Aislar esta rama</button>
      <button class="btn btn-red"   id="del-node-btn" onclick="deleteSelectedNode()">✕ Eliminar nodo y relaciones</button>
    </div>
  </div>
</div>

<!-- Add relation modal -->
<div class="overlay" id="add-modal">
  <div class="modal">
    <h2>Nueva relación</h2>
    <div class="field"><label>Sujeto</label><input id="f-subject" placeholder="ej: Usuario" list="node-names"><datalist id="node-names"></datalist></div>
    <div class="field"><label>Predicado</label><input id="f-predicate" placeholder="ej: VIVE_EN"></div>
    <div class="field"><label>Objeto</label><input id="f-object" placeholder="ej: Madrid" list="node-names"></div>
    <div class="field"><label>Tipo sujeto</label>
      <select id="f-stype"><option>PERSONA</option><option>ENTRETENIMIENTO</option><option>GENERO</option><option>SUBTEMA</option><option>DIRECTOR</option><option>PELICULA</option><option>MUSICA</option><option>ARTISTA</option><option>LUGAR</option><option>MASCOTA</option><option>TRABAJO</option><option>TECNOLOGIA</option><option>CONCEPTO</option><option>ENTIDAD</option></select>
    </div>
    <div class="field"><label>Tipo objeto</label>
      <select id="f-otype"><option>ENTIDAD</option><option>PERSONA</option><option>ENTRETENIMIENTO</option><option>GENERO</option><option>SUBTEMA</option><option>DIRECTOR</option><option>PELICULA</option><option>MUSICA</option><option>ARTISTA</option><option>LUGAR</option><option>MASCOTA</option><option>TRABAJO</option><option>TECNOLOGIA</option><option>CONCEPTO</option></select>
    </div>
    <div class="modal-btns">
      <button class="btn" onclick="closeAddModal()">Cancelar</button>
      <button class="btn btn-green" onclick="submitTriple()">Guardar</button>
    </div>
  </div>
</div>

<!-- Confirm clear -->
<div class="confirm-overlay" id="confirm-overlay">
  <div class="confirm-box">
    <p id="confirm-msg">¿Borrar todo el grafo?</p>
    <div class="confirm-btns">
      <button class="btn" onclick="closeConfirm()">Cancelar</button>
      <button class="btn btn-red" id="confirm-ok">Borrar</button>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
// ── Color scheme ─────────────────────────────────────────────────────────────
const TYPE_COLORS = {
  PERSONA:        {bg:'#3b82f6', border:'#1d4ed8'},
  ENTRETENIMIENTO:{bg:'#f97316', border:'#c2410c'},
  GENERO:         {bg:'#a855f7', border:'#7e22ce'},
  SUBTEMA:        {bg:'#8b5cf6', border:'#6d28d9'},
  DIRECTOR:       {bg:'#ec4899', border:'#be185d'},
  PELICULA:       {bg:'#f43f5e', border:'#be123c'},
  SERIE:          {bg:'#fb7185', border:'#e11d48'},
  MUSICA:         {bg:'#06b6d4', border:'#0e7490'},
  ARTISTA:        {bg:'#22d3ee', border:'#0891b2'},
  LIBRO:          {bg:'#84cc16', border:'#4d7c0f'},
  AUTOR:          {bg:'#a3e635', border:'#65a30d'},
  DEPORTE:        {bg:'#facc15', border:'#ca8a04'},
  EQUIPO:         {bg:'#fbbf24', border:'#d97706'},
  LUGAR:          {bg:'#22c55e', border:'#15803d'},
  MASCOTA:        {bg:'#fb923c', border:'#ea580c'},
  TRABAJO:        {bg:'#14b8a6', border:'#0f766e'},
  EMPRESA:        {bg:'#2dd4bf', border:'#0d9488'},
  TECNOLOGIA:     {bg:'#60a5fa', border:'#2563eb'},
  COMIDA:         {bg:'#f87171', border:'#dc2626'},
  HOBBIE:         {bg:'#c084fc', border:'#9333ea'},
  ESTADO:         {bg:'#ef4444', border:'#b91c1c'},
  CONDICION:      {bg:'#ef4444', border:'#b91c1c'},
  CONCEPTO:       {bg:'#94a3b8', border:'#64748b'},
  FECHA:          {bg:'#38bdf8', border:'#0284c7'},
  ENTIDAD:        {bg:'#6b7280', border:'#4b5563'},
  DEFAULT:        {bg:'#8b5cf6', border:'#6d28d9'},
};
const colorFor = t => TYPE_COLORS[t] || TYPE_COLORS.DEFAULT;

// ── Style definitions ─────────────────────────────────────────────────────────
const STYLES = {
  fisica: {
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant:-60, springLength:130, springConstant:.08, damping:.4 },
      stabilization: { iterations:150 },
    },
    layout: { hierarchical: { enabled:false } },
    edges: { smooth: { type:'curvedCW', roundness:.15 } },
  },
  arbol_ud: {
    physics: { enabled:false },
    layout: { hierarchical: { enabled:true, direction:'UD', sortMethod:'directed', levelSeparation:100, nodeSpacing:140, treeSpacing:160 } },
    edges: { smooth: { type:'cubicBezier', forceDirection:'vertical' } },
  },
  arbol_lr: {
    physics: { enabled:false },
    layout: { hierarchical: { enabled:true, direction:'LR', sortMethod:'directed', levelSeparation:160, nodeSpacing:80, treeSpacing:120 } },
    edges: { smooth: { type:'cubicBezier', forceDirection:'horizontal' } },
  },
  disperso: {
    physics: {
      enabled: true,
      solver: 'barnesHut',
      barnesHut: { gravitationalConstant:-8000, centralGravity:.1, springLength:200, springConstant:.02, damping:.5 },
      stabilization: { iterations:100 },
    },
    layout: { hierarchical: { enabled:false } },
    edges: { smooth: { type:'dynamic' } },
  },
};

let nodesDS, edgesDS, network;
let allEdges=[], allNodes=[];
let currentStyle = 'fisica';
let isIsolated   = false;
let selectedNode = null;

// ── Build / refresh network ───────────────────────────────────────────────────
function buildNetwork(data) {
  allEdges = data.edges;
  allNodes = data.nodes;
  document.getElementById('node-count').textContent = data.nodes.length;
  document.getElementById('edge-count').textContent = data.edges.length;
  updateDatalist();

  const visNodes = data.nodes.map(n => nodeConfig(n));
  const visEdges = data.edges.map((e,i) => edgeConfig(e,i));

  if (!network) {
    nodesDS = new vis.DataSet(visNodes);
    edgesDS = new vis.DataSet(visEdges);
    initNetwork();
  } else if (!isIsolated) {
    nodesDS.update(visNodes);
    const newIds = new Set(visEdges.map(e=>e.id));
    edgesDS.remove(edgesDS.getIds().filter(id=>!newIds.has(id)));
    edgesDS.update(visEdges);
  }
  buildLegend(data.nodes);
}

function fmtDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString('es-ES', {day:'numeric', month:'short', year:'numeric',
    hour:'2-digit', minute:'2-digit'});
}

function nodeConfig(n) {
  const c = colorFor(n.type);
  const isPersona = n.type === 'PERSONA';
  return {
    id: n.id, label: n.label, title: n.type,
    color:{ background:c.bg, border:c.border, highlight:{background:c.bg, border:'#fff'} },
    font:{ color:'#fff', size:13, face:'Segoe UI' },
    borderWidth: isPersona ? 4 : 2,
    borderDashes: false,
    shape: 'dot',
    size:  isPersona ? 22 : 14,
    _weight: n.weight ?? 1.0,
    _access_count: n.access_count ?? 0,
    _created_at: n.created_at ?? null,
    _last_accessed: n.last_accessed ?? null,
  };
}

function edgeConfig(e, i) {
  return {
    id:i, from:e.from, to:e.to, label:e.label,
    font:{color:'#666', size:9, face:'Segoe UI', align:'middle', strokeWidth:0},
    color:{color:'#2a2d3e', highlight:'#a78bfa', opacity:.8},
    arrows:{to:{enabled:true, scaleFactor:.55}},
    smooth: STYLES[currentStyle].edges.smooth,
    _weight: e.weight ?? 1.0,
    _access_count: e.access_count ?? 0,
    _confidence: e.confidence ?? 1.0,
    _created_at: e.created_at ?? null,
    _last_accessed: e.last_accessed ?? null,
  };
}

function initNetwork() {
  const opts = {
    ...STYLES[currentStyle],
    interaction:{ hover:true, tooltipDelay:200 },
  };
  network = new vis.Network(document.getElementById('network'), {nodes:nodesDS, edges:edgesDS}, opts);
  network.on('click', onNetworkClick);
}

// ── Style switching ───────────────────────────────────────────────────────────
function applyStyle(name) {
  if (currentStyle === name && network) return;
  currentStyle = name;

  // Update active button
  document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('s-' + name)?.classList.add('active');

  const netEl = document.getElementById('network');
  netEl.classList.toggle('tree-mode', name.startsWith('arbol'));

  if (network) {
    network.destroy();
    network = null;
  }
  initNetwork();
  setTimeout(() => network && network.fit(), 600);
}

// ── Branch isolation ──────────────────────────────────────────────────────────
function isolateSelected() {
  if (!selectedNode) return;

  // BFS in both directions from selected node
  const reachable = new Set([selectedNode]);
  const queue = [selectedNode];
  while (queue.length) {
    const cur = queue.shift();
    for (const n of network.getConnectedNodes(cur)) {
      if (!reachable.has(n)) { reachable.add(n); queue.push(n); }
    }
  }

  // Hide non-reachable nodes
  nodesDS.update(nodesDS.getIds().map(id => ({ id, hidden: !reachable.has(id) })));

  // Hide edges where any endpoint is hidden
  edgesDS.update(edgesDS.getIds().map(id => {
    const e = edgesDS.get(id);
    return { id, hidden: !reachable.has(e.from) || !reachable.has(e.to) };
  }));

  isIsolated = true;
  const bar = document.getElementById('isolated-bar');
  bar.classList.add('visible');
  document.getElementById('isolated-label').textContent =
    `Rama aislada: "${selectedNode}" (${reachable.size} nodos visibles)`;

  network.fit({ nodes: [...reachable], animation:{ duration:500, easingFunction:'easeInOutQuad' } });
  toast(`Rama "${selectedNode}" aislada — ${reachable.size} nodos`);
}

function showAll() {
  nodesDS.update(nodesDS.getIds().map(id => ({ id, hidden:false })));
  edgesDS.update(edgesDS.getIds().map(id => ({ id, hidden:false })));
  isIsolated = false;
  document.getElementById('isolated-bar').classList.remove('visible');
  network.fit({ animation:{ duration:500, easingFunction:'easeInOutQuad' } });
  toast('Grafo completo restaurado');
}

// ── Click handler ─────────────────────────────────────────────────────────────
function onNetworkClick(params) {
  const panel   = document.getElementById('detail-content');
  const actions = document.getElementById('node-actions');

  if (params.nodes.length) {
    selectedNode = params.nodes[0];
    actions.style.display = 'flex';
    const node = nodesDS.get(selectedNode);
    const out  = allEdges.filter(e => e.from === selectedNode);
    const inc  = allEdges.filter(e => e.to   === selectedNode);

    let html = `<div class="detail-name">
      <span id="node-label-text">${node.label}</span>
      <button class="edit-btn" title="Editar" onclick="startEditNode('${node.label}')">✏</button>
    </div>
    <div id="node-edit-area" style="display:none">
      <input class="edit-input" id="node-edit-input" value="${node.label}">
      <div class="edit-actions">
        <button class="btn btn-green" onclick="saveNodeName('${node.label}')">Guardar</button>
        <button class="btn" onclick="cancelEditNode()">Cancelar</button>
      </div>
    </div>
    <div class="detail-type">${node.title}</div>
    <div class="meta-grid">
      <div class="meta-cell"><span class="meta-lbl">Peso</span><span class="meta-val">${(node._weight||1).toFixed(2)}</span></div>
      <div class="meta-cell"><span class="meta-lbl">Accesos</span><span class="meta-val">${node._access_count||0}</span></div>
      <div class="meta-cell meta-full"><span class="meta-lbl">Creado</span><span class="meta-val" style="color:#60a5fa">${fmtDate(node._created_at)}</span></div>
      <div class="meta-cell meta-full"><span class="meta-lbl">Último acceso</span><span class="meta-val" style="color:#4ade80">${fmtDate(node._last_accessed)}</span></div>
    </div>`;

    const relBlock = (arr, dir) => arr.map(e => `
      <div class="rel-row">
        <span style="color:#444">${dir}</span>
        <div style="flex:1">
          <span class="rel-pred">${e.label}</span>
          <span style="color:#ddd">${dir==='→' ? e.to : e.from}</span>
        </div>
        <button class="rel-del" onclick="deleteEdge('${e.from}','${e.label}','${e.to}')">✕</button>
      </div>`).join('');

    if (out.length) html += `<div style="font-size:9px;color:#333;margin:8px 0 4px;text-transform:uppercase;letter-spacing:.8px">Salientes</div>` + relBlock(out, '→');
    if (inc.length) html += `<div style="font-size:9px;color:#333;margin:8px 0 4px;text-transform:uppercase;letter-spacing:.8px">Entrantes</div>` + relBlock(inc, '←');
    panel.innerHTML = html;

  } else if (params.edges.length) {
    selectedNode = null;
    actions.style.display = 'none';
    const edge = edgesDS.get(params.edges[0]);
    if (edge) {
      panel.innerHTML = `
        <div style="margin-bottom:6px">
          <div style="font-size:9px;color:#333;margin-bottom:3px">RELACIÓN</div>
          <div style="font-size:15px;font-weight:700;color:#a78bfa">${edge.label}</div>
        </div>
        <div style="font-size:12px;color:#aaa;margin-bottom:8px"><b style="color:#ddd">${edge.from}</b> → <b style="color:#ddd">${edge.to}</b></div>
        <div class="meta-grid">
          <div class="meta-cell"><span class="meta-lbl">Peso</span><span class="meta-val">${(edge._weight||1).toFixed(2)}</span></div>
          <div class="meta-cell"><span class="meta-lbl">Accesos</span><span class="meta-val">${edge._access_count||0}</span></div>
          <div class="meta-cell"><span class="meta-lbl">Confianza</span><span class="meta-val">${(edge._confidence||1).toFixed(2)}</span></div>
          <div class="meta-cell meta-full"><span class="meta-lbl">Creado</span><span class="meta-val" style="color:#60a5fa">${fmtDate(edge._created_at)}</span></div>
          <div class="meta-cell meta-full"><span class="meta-lbl">Último acceso</span><span class="meta-val" style="color:#4ade80">${fmtDate(edge._last_accessed)}</span></div>
        </div>
        <button class="btn btn-red" style="margin-top:6px;width:100%;padding:6px"
          onclick="deleteEdge('${edge.from}','${edge.label}','${edge.to}')">✕ Eliminar relación</button>`;
    }
  } else {
    selectedNode = null;
    actions.style.display = 'none';
    panel.innerHTML = '<span style="color:#333;font-size:12px">Haz clic en un nodo o relación.</span>';
  }
}

// ── Legend ────────────────────────────────────────────────────────────────────
function buildLegend(nodes) {
  const types = [...new Set(nodes.map(n => n.type))];
  document.getElementById('legend').innerHTML = types.map(t => {
    const c = colorFor(t);
    return `<div class="legend-item"><div class="legend-dot" style="background:${c.bg}"></div><span>${t}</span></div>`;
  }).join('');
}

function updateDatalist() {
  document.getElementById('node-names').innerHTML =
    allNodes.map(n => `<option value="${n.label}">`).join('');
}

// ── Edit node name ────────────────────────────────────────────────────────────
function startEditNode(name) {
  document.getElementById('node-label-text').parentElement.style.display = 'none';
  const area = document.getElementById('node-edit-area');
  area.style.display = 'block';
  const inp = document.getElementById('node-edit-input');
  inp.value = name; inp.focus(); inp.select();
  inp.onkeydown = e => { if(e.key==='Enter') saveNodeName(name); if(e.key==='Escape') cancelEditNode(); };
}
function cancelEditNode() {
  document.getElementById('node-edit-area').style.display = 'none';
  document.getElementById('node-label-text').parentElement.style.display = 'flex';
}
async function saveNodeName(oldName) {
  const newName = document.getElementById('node-edit-input').value.trim();
  if (!newName || newName === oldName) { cancelEditNode(); return; }
  await fetch(`/node/${encodeURIComponent(oldName)}?new_name=${encodeURIComponent(newName)}`, {method:'PATCH'});
  toast(`"${oldName}" → "${newName}"`);
  selectedNode = newName;
  await refresh();
}

// ── Delete ────────────────────────────────────────────────────────────────────
async function deleteEdge(from, pred, to) {
  await fetch(`/triple?subject=${encodeURIComponent(from)}&predicate=${encodeURIComponent(pred)}&object=${encodeURIComponent(to)}`, {method:'DELETE'});
  toast(`Relación "${pred}" eliminada`);
  await refresh();
}
async function deleteSelectedNode() {
  if (!selectedNode) return;
  await fetch(`/node/${encodeURIComponent(selectedNode)}`, {method:'DELETE'});
  toast(`Nodo "${selectedNode}" eliminado`);
  selectedNode = null;
  document.getElementById('node-actions').style.display = 'none';
  document.getElementById('detail-content').innerHTML = '<span style="color:#333;font-size:12px">Haz clic en un nodo.</span>';
  if (isIsolated) showAll();
  await refresh();
}

// ── Clear all ─────────────────────────────────────────────────────────────────
let confirmCallback = null;
function confirmClear() {
  document.getElementById('confirm-msg').textContent = '¿Borrar TODO el grafo? Esta acción no se puede deshacer.';
  confirmCallback = async () => { await fetch('/graph',{method:'DELETE'}); toast('Grafo borrado'); if(isIsolated) showAll(); await refresh(); };
  document.getElementById('confirm-overlay').classList.add('open');
  document.getElementById('confirm-ok').onclick = async () => { closeConfirm(); await confirmCallback(); };
}
function closeConfirm() { document.getElementById('confirm-overlay').classList.remove('open'); }

// ── Add triple modal ──────────────────────────────────────────────────────────
function openAddModal() { document.getElementById('add-modal').classList.add('open'); }
function closeAddModal() { document.getElementById('add-modal').classList.remove('open'); }
async function submitTriple() {
  const s=document.getElementById('f-subject').value.trim();
  const p=document.getElementById('f-predicate').value.trim().toUpperCase().replace(/\s+/g,'_');
  const o=document.getElementById('f-object').value.trim();
  const st=document.getElementById('f-stype').value;
  const ot=document.getElementById('f-otype').value;
  if(!s||!p||!o){toast('Completa todos los campos');return;}
  await fetch('/api/triple',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({subject:s,subject_type:st,predicate:p,object:o,object_type:ot})});
  toast(`${s} → ${p} → ${o}`);
  closeAddModal();
  ['f-subject','f-predicate','f-object'].forEach(id=>document.getElementById(id).value='');
  await refresh();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer;
function toast(msg) {
  const el=document.getElementById('toast');
  el.textContent=msg; el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>el.classList.remove('show'),2500);
}

// ── Refresh ───────────────────────────────────────────────────────────────────
async function refresh() {
  try {
    const r = await fetch('/api/graph');
    buildNetwork(await r.json());
  } catch(e) { console.error(e); }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""

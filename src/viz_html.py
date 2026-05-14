VIZ_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Graph Memory</title>
  <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f1117;color:#e0e0e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}

    header{display:flex;align-items:center;justify-content:space-between;padding:11px 18px;background:#1a1d27;border-bottom:1px solid #2a2d3e;flex-shrink:0;gap:12px}
    header h1{font-size:15px;font-weight:700;color:#a78bfa;white-space:nowrap}
    .stats{display:flex;gap:14px;font-size:12px;color:#666;flex:1}
    .stats b{color:#ddd}
    .header-btns{display:flex;gap:8px}

    .btn{padding:5px 12px;border-radius:6px;border:1px solid #3a3d4e;cursor:pointer;font-size:12px;font-weight:500;transition:all .15s;background:#2a2d3e;color:#ccc}
    .btn:hover{background:#3a3d4e;color:#fff}
    .btn-purple{background:#4c1d95;border-color:#6d28d9;color:#c4b5fd}
    .btn-purple:hover{background:#5b21b6}
    .btn-red{background:#450a0a;border-color:#b91c1c;color:#fca5a5}
    .btn-red:hover{background:#7f1d1d}
    .btn-green{background:#052e16;border-color:#15803d;color:#86efac}
    .btn-green:hover{background:#14532d}
    .badge-live{padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;background:#14532d;color:#4ade80;letter-spacing:.5px;animation:pulse 2s infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}

    .main{display:flex;flex:1;overflow:hidden}
    #network{flex:1;background:radial-gradient(ellipse at center,#141720 0%,#0f1117 100%)}

    .sidebar{width:270px;background:#1a1d27;border-left:1px solid #2a2d3e;display:flex;flex-direction:column;flex-shrink:0;overflow:hidden}
    .sb-section{padding:12px 14px;border-bottom:1px solid #2a2d3e}
    .sb-section h3{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:8px}

    .legend-item{display:flex;align-items:center;gap:7px;margin-bottom:5px;font-size:12px}
    .legend-dot{width:11px;height:11px;border-radius:50%;flex-shrink:0}

    #detail-panel{flex:1;padding:12px 14px;overflow-y:auto}
    #detail-panel h3{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:8px}
    .detail-name{font-size:17px;font-weight:700;color:#fff;margin-bottom:3px}
    .detail-type{font-size:10px;color:#555;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px}
    .rel-item{display:flex;align-items:flex-start;gap:7px;margin-bottom:6px;padding:6px 8px;background:#12151f;border-radius:6px;font-size:12px;border:1px solid transparent;transition:border-color .15s}
    .rel-item:hover{border-color:#3a3d4e}
    .rel-arrow{color:#444;flex-shrink:0;margin-top:1px}
    .rel-pred{color:#a78bfa;font-weight:600;font-size:10px;display:block;margin-bottom:1px}
    .rel-target{color:#ddd}
    .rel-del{margin-left:auto;padding:2px 6px;font-size:10px;border-radius:4px;border:1px solid #7f1d1d;background:#450a0a;color:#fca5a5;cursor:pointer;flex-shrink:0;opacity:0;transition:opacity .15s}
    .rel-item:hover .rel-del{opacity:1}

    .sb-actions{padding:10px 14px;border-top:1px solid #2a2d3e;display:flex;flex-direction:column;gap:6px}

    /* Modal */
    .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}
    .overlay.open{display:flex}
    .modal{background:#1a1d27;border:1px solid #2a2d3e;border-radius:12px;padding:24px;width:380px;max-width:95vw}
    .modal h2{font-size:15px;font-weight:700;margin-bottom:18px;color:#a78bfa}
    .field{margin-bottom:14px}
    .field label{display:block;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px}
    .field input,.field select{width:100%;padding:7px 10px;background:#12151f;border:1px solid #2a2d3e;border-radius:6px;color:#ddd;font-size:13px;outline:none;transition:border-color .15s}
    .field input:focus,.field select:focus{border-color:#6d28d9}
    .field select option{background:#1a1d27}
    .modal-btns{display:flex;gap:8px;margin-top:20px}
    .modal-btns .btn{flex:1;padding:8px}

    /* Toast */
    #toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#1a1d27;border:1px solid #2a2d3e;color:#ddd;padding:8px 18px;border-radius:8px;font-size:13px;opacity:0;transition:opacity .3s;pointer-events:none;z-index:200}
    #toast.show{opacity:1}

    /* Confirm dialog */
    .confirm-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:150;align-items:center;justify-content:center}
    .confirm-overlay.open{display:flex}
    .confirm-box{background:#1a1d27;border:1px solid #b91c1c;border-radius:10px;padding:22px;width:320px;text-align:center}
    .confirm-box p{margin-bottom:16px;font-size:14px;color:#ddd;line-height:1.5}
    .confirm-btns{display:flex;gap:10px}
    .confirm-btns .btn{flex:1;padding:8px}
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
  <div class="header-btns">
    <button class="btn btn-purple" onclick="openAddModal()">+ Relación</button>
    <button class="btn" onclick="network && network.fit()">Centrar</button>
    <button class="btn" onclick="togglePhysics()">Física</button>
    <button class="btn btn-red" onclick="confirmClear()">Borrar todo</button>
  </div>
</header>

<div class="main">
  <div id="network"></div>
  <div class="sidebar">
    <div class="sb-section">
      <h3>Tipos de nodo</h3>
      <div id="legend"></div>
    </div>
    <div id="detail-panel">
      <h3>Detalle</h3>
      <div id="detail-content" style="color:#444;font-size:13px">Haz clic en un nodo o relación.</div>
    </div>
    <div class="sb-actions" id="node-actions" style="display:none">
      <button class="btn btn-red" id="del-node-btn" onclick="deleteSelectedNode()">Eliminar nodo y sus relaciones</button>
    </div>
  </div>
</div>

<!-- Modal añadir relación -->
<div class="overlay" id="add-modal">
  <div class="modal">
    <h2>Nueva relación</h2>
    <div class="field">
      <label>Sujeto</label>
      <input id="f-subject" placeholder="ej: Usuario" list="node-names">
      <datalist id="node-names"></datalist>
    </div>
    <div class="field">
      <label>Predicado</label>
      <input id="f-predicate" placeholder="ej: VIVE_EN">
    </div>
    <div class="field">
      <label>Objeto</label>
      <input id="f-object" placeholder="ej: Madrid" list="node-names">
    </div>
    <div class="field">
      <label>Tipo sujeto</label>
      <select id="f-stype">
        <option>PERSONA</option><option>MASCOTA</option><option>LUGAR</option>
        <option>HOBBIE</option><option>CONDICION</option><option>ESTADO</option>
        <option>TRABAJO</option><option>COMIDA</option><option>FECHA</option>
        <option>ENTIDAD</option>
      </select>
    </div>
    <div class="field">
      <label>Tipo objeto</label>
      <select id="f-otype">
        <option>ENTIDAD</option><option>PERSONA</option><option>MASCOTA</option>
        <option>LUGAR</option><option>HOBBIE</option><option>CONDICION</option>
        <option>ESTADO</option><option>TRABAJO</option><option>COMIDA</option>
        <option>FECHA</option>
      </select>
    </div>
    <div class="modal-btns">
      <button class="btn" onclick="closeAddModal()">Cancelar</button>
      <button class="btn btn-green" onclick="submitTriple()">Guardar</button>
    </div>
  </div>
</div>

<!-- Confirm borrar todo -->
<div class="confirm-overlay" id="confirm-overlay">
  <div class="confirm-box">
    <p id="confirm-msg">¿Borrar todo el grafo? Esta acción no se puede deshacer.</p>
    <div class="confirm-btns">
      <button class="btn" onclick="closeConfirm()">Cancelar</button>
      <button class="btn btn-red" id="confirm-ok">Borrar</button>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
const TYPE_COLORS = {
  PERSONA:   {bg:'#3b82f6',border:'#1d4ed8'},
  MASCOTA:   {bg:'#f59e0b',border:'#b45309'},
  LUGAR:     {bg:'#22c55e',border:'#15803d'},
  HOBBIE:    {bg:'#a855f7',border:'#7e22ce'},
  CONDICION: {bg:'#ef4444',border:'#b91c1c'},
  ESTADO:    {bg:'#ef4444',border:'#b91c1c'},
  TRABAJO:   {bg:'#14b8a6',border:'#0f766e'},
  COMIDA:    {bg:'#f97316',border:'#c2410c'},
  FECHA:     {bg:'#06b6d4',border:'#0e7490'},
  ENTIDAD:   {bg:'#6b7280',border:'#4b5563'},
  DEFAULT:   {bg:'#8b5cf6',border:'#6d28d9'},
};
const colorFor = t => TYPE_COLORS[t] || TYPE_COLORS.DEFAULT;

let nodesDS, edgesDS, network, allEdges=[], allNodes=[], physicsOn=true, selectedNode=null;

/* ── Network ── */
function buildNetwork(data) {
  allEdges = data.edges;
  allNodes = data.nodes;
  document.getElementById('node-count').textContent = data.nodes.length;
  document.getElementById('edge-count').textContent = data.edges.length;
  updateDatalist();

  const visNodes = data.nodes.map(n => {
    const c = colorFor(n.type);
    return {
      id: n.id, label: n.label, title: n.type,
      color:{background:c.bg,border:c.border,highlight:{background:c.bg,border:'#fff'}},
      font:{color:'#fff',size:13,face:'Segoe UI'},
      borderWidth:2,
      shape: n.type==='PERSONA'?'star':'dot',
      size: n.type==='PERSONA'?20:14,
    };
  });

  const visEdges = data.edges.map((e,i)=>({
    id: i, from:e.from, to:e.to, label:e.label,
    font:{color:'#777',size:10,face:'Segoe UI',align:'middle'},
    color:{color:'#2a2d3e',highlight:'#a78bfa'},
    arrows:{to:{enabled:true,scaleFactor:.6}},
    smooth:{type:'curvedCW',roundness:.15},
  }));

  if (!network) {
    nodesDS = new vis.DataSet(visNodes);
    edgesDS = new vis.DataSet(visEdges);
    network = new vis.Network(
      document.getElementById('network'),
      {nodes:nodesDS, edges:edgesDS},
      {
        physics:{solver:'forceAtlas2Based',forceAtlas2Based:{gravitationalConstant:-60,springLength:130,springConstant:.08},stabilization:{iterations:150}},
        interaction:{hover:true,tooltipDelay:200},
      }
    );
    network.on('click', onNetworkClick);
  } else {
    const existingNodeIds = nodesDS.getIds();
    const newNodeIds = visNodes.map(n=>n.id);
    nodesDS.remove(existingNodeIds.filter(id=>!newNodeIds.includes(id)));
    nodesDS.update(visNodes);
    const existingEdgeIds = edgesDS.getIds();
    const newEdgeIds = visEdges.map(e=>e.id);
    edgesDS.remove(existingEdgeIds.filter(id=>!newEdgeIds.includes(id)));
    edgesDS.update(visEdges);
  }
  buildLegend(data.nodes);
}

function onNetworkClick(params) {
  const panel = document.getElementById('detail-content');
  const actions = document.getElementById('node-actions');

  if (params.nodes.length) {
    selectedNode = params.nodes[0];
    actions.style.display = 'flex';
    const node = nodesDS.get(selectedNode);
    const out = allEdges.filter(e=>e.from===selectedNode);
    const inc = allEdges.filter(e=>e.to===selectedNode);
    let html = `<div class="detail-name">${node.label}</div><div class="detail-type">${node.title}</div>`;
    if (out.length) {
      html += '<div style="font-size:10px;color:#444;margin-bottom:5px;text-transform:uppercase;letter-spacing:.8px">Salientes</div>';
      out.forEach(e => {
        html += `<div class="detail-rel-row" style="display:flex;align-items:center;gap:6px;margin-bottom:5px;padding:5px 7px;background:#12151f;border-radius:5px;font-size:12px">
          <span style="color:#444">→</span>
          <div style="flex:1"><span style="color:#a78bfa;font-size:10px;font-weight:600;display:block">${e.label}</span><span style="color:#ddd">${e.to}</span></div>
          <button onclick="deleteEdge('${e.from}','${e.label}','${e.to}')" style="padding:2px 7px;font-size:10px;border-radius:4px;border:1px solid #7f1d1d;background:#450a0a;color:#fca5a5;cursor:pointer">✕</button>
        </div>`;
      });
    }
    if (inc.length) {
      html += '<div style="font-size:10px;color:#444;margin:8px 0 5px;text-transform:uppercase;letter-spacing:.8px">Entrantes</div>';
      inc.forEach(e => {
        html += `<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;padding:5px 7px;background:#12151f;border-radius:5px;font-size:12px">
          <span style="color:#444">←</span>
          <div style="flex:1"><span style="color:#a78bfa;font-size:10px;font-weight:600;display:block">${e.label}</span><span style="color:#ddd">${e.from}</span></div>
          <button onclick="deleteEdge('${e.from}','${e.label}','${e.to}')" style="padding:2px 7px;font-size:10px;border-radius:4px;border:1px solid #7f1d1d;background:#450a0a;color:#fca5a5;cursor:pointer">✕</button>
        </div>`;
      });
    }
    panel.innerHTML = html;
  } else if (params.edges.length) {
    selectedNode = null;
    actions.style.display = 'none';
    const edgeId = params.edges[0];
    const edge = edgesDS.get(edgeId);
    if (edge) {
      panel.innerHTML = `
        <div style="margin-bottom:12px">
          <div style="font-size:10px;color:#555;margin-bottom:4px">RELACIÓN</div>
          <div style="font-size:15px;font-weight:700;color:#a78bfa">${edge.label}</div>
        </div>
        <div style="font-size:12px;color:#aaa;margin-bottom:4px"><b style="color:#ddd">${edge.from}</b> → <b style="color:#ddd">${edge.to}</b></div>
        <button class="btn btn-red" style="margin-top:12px;width:100%;padding:7px" onclick="deleteEdge('${edge.from}','${edge.label}','${edge.to}')">Eliminar esta relación</button>`;
    }
  } else {
    selectedNode = null;
    actions.style.display = 'none';
    panel.innerHTML = '<span style="color:#444;font-size:13px">Haz clic en un nodo o relación.</span>';
  }
}

function buildLegend(nodes) {
  const types = [...new Set(nodes.map(n=>n.type))];
  document.getElementById('legend').innerHTML = types.map(t => {
    const c = colorFor(t);
    return `<div class="legend-item"><div class="legend-dot" style="background:${c.bg}"></div><span>${t}</span></div>`;
  }).join('');
}

function updateDatalist() {
  const dl = document.getElementById('node-names');
  dl.innerHTML = allNodes.map(n=>`<option value="${n.label}">`).join('');
}

function togglePhysics() {
  physicsOn = !physicsOn;
  network.setOptions({physics:{enabled:physicsOn}});
}

/* ── Delete ── */
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
  document.getElementById('detail-content').innerHTML = '<span style="color:#444;font-size:13px">Haz clic en un nodo o relación.</span>';
  await refresh();
}

/* ── Clear all ── */
let confirmCallback = null;
function confirmClear() {
  document.getElementById('confirm-msg').textContent = '¿Borrar TODO el grafo? Esta acción no se puede deshacer.';
  confirmCallback = async () => {
    await fetch('/graph', {method:'DELETE'});
    toast('Grafo borrado');
    await refresh();
  };
  document.getElementById('confirm-overlay').classList.add('open');
  document.getElementById('confirm-ok').onclick = async () => { closeConfirm(); await confirmCallback(); };
}
function closeConfirm() { document.getElementById('confirm-overlay').classList.remove('open'); }

/* ── Add triple modal ── */
function openAddModal() { document.getElementById('add-modal').classList.add('open'); }
function closeAddModal() { document.getElementById('add-modal').classList.remove('open'); }

async function submitTriple() {
  const s = document.getElementById('f-subject').value.trim();
  const p = document.getElementById('f-predicate').value.trim().toUpperCase().replace(/\s+/g,'_');
  const o = document.getElementById('f-object').value.trim();
  const st = document.getElementById('f-stype').value;
  const ot = document.getElementById('f-otype').value;
  if (!s || !p || !o) { toast('Completa todos los campos'); return; }
  await fetch('/api/triple', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({subject:s,subject_type:st,predicate:p,object:o,object_type:ot}),
  });
  toast(`Relación guardada: ${s} → ${p} → ${o}`);
  closeAddModal();
  ['f-subject','f-predicate','f-object'].forEach(id => document.getElementById(id).value='');
  await refresh();
}

/* ── Toast ── */
let toastTimer;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>el.classList.remove('show'), 2500);
}

/* ── Refresh ── */
async function refresh() {
  try {
    const res = await fetch('/api/graph');
    buildNetwork(await res.json());
  } catch(e) { console.error(e); }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""

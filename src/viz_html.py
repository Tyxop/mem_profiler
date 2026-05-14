VIZ_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Graph Memory — Visualización</title>
  <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0f1117;
      color: #e0e0e0;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: #1a1d27;
      border-bottom: 1px solid #2a2d3e;
      flex-shrink: 0;
    }

    header h1 { font-size: 16px; font-weight: 600; letter-spacing: 0.5px; color: #a78bfa; }

    .stats { display: flex; gap: 16px; font-size: 13px; color: #888; }
    .stats span { display: flex; align-items: center; gap: 5px; }
    .stats b { color: #e0e0e0; }

    .badge {
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }
    .badge-live { background: #14532d; color: #4ade80; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }

    .main {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    #network {
      flex: 1;
      background: radial-gradient(ellipse at center, #141720 0%, #0f1117 100%);
    }

    .sidebar {
      width: 260px;
      background: #1a1d27;
      border-left: 1px solid #2a2d3e;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    .sidebar-section {
      padding: 14px 16px;
      border-bottom: 1px solid #2a2d3e;
    }

    .sidebar-section h3 {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #666;
      margin-bottom: 10px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      font-size: 12px;
    }

    .legend-dot {
      width: 12px; height: 12px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    #detail-panel {
      flex: 1;
      padding: 14px 16px;
      overflow-y: auto;
    }

    #detail-panel h3 {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #666;
      margin-bottom: 10px;
    }

    #detail-content {
      font-size: 13px;
      color: #aaa;
    }

    .detail-node-name {
      font-size: 18px;
      font-weight: 700;
      color: #e0e0e0;
      margin-bottom: 4px;
    }

    .detail-node-type {
      font-size: 11px;
      color: #666;
      margin-bottom: 14px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .detail-relation {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 8px;
      padding: 6px 8px;
      background: #12151f;
      border-radius: 6px;
      font-size: 12px;
    }

    .detail-arrow { color: #555; flex-shrink: 0; }
    .detail-predicate { color: #a78bfa; font-weight: 600; font-size: 10px; display: block; }
    .detail-target { color: #e0e0e0; }

    .controls {
      padding: 10px 16px;
      border-top: 1px solid #2a2d3e;
      display: flex;
      gap: 8px;
    }

    button {
      flex: 1;
      padding: 6px;
      background: #2a2d3e;
      border: 1px solid #3a3d4e;
      color: #ccc;
      border-radius: 6px;
      cursor: pointer;
      font-size: 11px;
      transition: background 0.15s;
    }
    button:hover { background: #3a3d4e; color: #fff; }
  </style>
</head>
<body>

<header>
  <h1>⬡ Graph Memory</h1>
  <div class="stats">
    <span>Nodos: <b id="node-count">0</b></span>
    <span>Relaciones: <b id="edge-count">0</b></span>
    <span class="badge badge-live">● LIVE</span>
  </div>
</header>

<div class="main">
  <div id="network"></div>

  <div class="sidebar">
    <div class="sidebar-section">
      <h3>Tipos de nodo</h3>
      <div id="legend"></div>
    </div>

    <div id="detail-panel">
      <h3>Detalle</h3>
      <div id="detail-content" style="color:#555">
        Haz clic en un nodo para ver sus relaciones.
      </div>
    </div>

    <div class="controls">
      <button onclick="network.fit()">Centrar</button>
      <button onclick="togglePhysics()">Física</button>
    </div>
  </div>
</div>

<script>
const TYPE_COLORS = {
  PERSONA:   { bg: '#3b82f6', border: '#1d4ed8' },
  MASCOTA:   { bg: '#f59e0b', border: '#b45309' },
  LUGAR:     { bg: '#22c55e', border: '#15803d' },
  HOBBIE:    { bg: '#a855f7', border: '#7e22ce' },
  CONDICION: { bg: '#ef4444', border: '#b91c1c' },
  ESTADO:    { bg: '#ef4444', border: '#b91c1c' },
  TRABAJO:   { bg: '#14b8a6', border: '#0f766e' },
  COMIDA:    { bg: '#f97316', border: '#c2410c' },
  FECHA:     { bg: '#06b6d4', border: '#0e7490' },
  ENTIDAD:   { bg: '#6b7280', border: '#4b5563' },
  DEFAULT:   { bg: '#8b5cf6', border: '#6d28d9' },
};

function colorFor(type) {
  return TYPE_COLORS[type] || TYPE_COLORS.DEFAULT;
}

let nodesDS, edgesDS, network, allEdges = [], physicsOn = true;

function buildNetwork(data) {
  allEdges = data.edges;
  document.getElementById('node-count').textContent = data.nodes.length;
  document.getElementById('edge-count').textContent = data.edges.length;

  const visNodes = data.nodes.map(n => {
    const c = colorFor(n.type);
    return {
      id: n.id,
      label: n.label,
      title: n.type,
      color: { background: c.bg, border: c.border, highlight: { background: c.bg, border: '#fff' } },
      font: { color: '#fff', size: 13, face: 'Segoe UI' },
      borderWidth: 2,
      shape: n.type === 'PERSONA' ? 'star' : 'dot',
      size: n.type === 'PERSONA' ? 20 : 14,
    };
  });

  const visEdges = data.edges.map((e, i) => ({
    id: i,
    from: e.from,
    to: e.to,
    label: e.label,
    font: { color: '#888', size: 10, face: 'Segoe UI', align: 'middle' },
    color: { color: '#3a3d4e', highlight: '#a78bfa' },
    arrows: { to: { enabled: true, scaleFactor: 0.6 } },
    smooth: { type: 'curvedCW', roundness: 0.15 },
  }));

  if (!network) {
    nodesDS = new vis.DataSet(visNodes);
    edgesDS = new vis.DataSet(visEdges);

    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -60, springLength: 120, springConstant: 0.08 },
        stabilization: { iterations: 150 },
      },
      interaction: { hover: true, tooltipDelay: 200 },
    };

    network = new vis.Network(
      document.getElementById('network'),
      { nodes: nodesDS, edges: edgesDS },
      options
    );

    network.on('click', onNodeClick);
  } else {
    nodesDS.update(visNodes);
    edgesDS.update(visEdges);
    const existingIds = edgesDS.getIds();
    const newIds = visEdges.map(e => e.id);
    edgesDS.remove(existingIds.filter(id => !newIds.includes(id)));
  }

  buildLegend(data.nodes);
}

function onNodeClick(params) {
  const panel = document.getElementById('detail-content');
  if (!params.nodes.length) { panel.innerHTML = '<span style="color:#555">Haz clic en un nodo.</span>'; return; }

  const nodeId = params.nodes[0];
  const node = nodesDS.get(nodeId);
  const outgoing = allEdges.filter(e => e.from === nodeId);
  const incoming = allEdges.filter(e => e.to === nodeId);

  let html = `<div class="detail-node-name">${node.label}</div>`;
  html += `<div class="detail-node-type">${node.title}</div>`;

  if (outgoing.length) {
    html += '<div style="font-size:11px;color:#555;margin-bottom:6px">RELACIONES SALIENTES</div>';
    outgoing.forEach(e => {
      html += `<div class="detail-relation">
        <span class="detail-arrow">→</span>
        <div><span class="detail-predicate">${e.label}</span>
        <span class="detail-target">${e.to}</span></div>
      </div>`;
    });
  }

  if (incoming.length) {
    html += '<div style="font-size:11px;color:#555;margin:10px 0 6px">RELACIONES ENTRANTES</div>';
    incoming.forEach(e => {
      html += `<div class="detail-relation">
        <span class="detail-arrow">←</span>
        <div><span class="detail-predicate">${e.label}</span>
        <span class="detail-target">${e.from}</span></div>
      </div>`;
    });
  }

  panel.innerHTML = html;
}

function buildLegend(nodes) {
  const types = [...new Set(nodes.map(n => n.type))];
  const legend = document.getElementById('legend');
  legend.innerHTML = types.map(t => {
    const c = colorFor(t);
    return `<div class="legend-item">
      <div class="legend-dot" style="background:${c.bg}"></div>
      <span style="font-size:12px">${t}</span>
    </div>`;
  }).join('');
}

function togglePhysics() {
  physicsOn = !physicsOn;
  network.setOptions({ physics: { enabled: physicsOn } });
}

async function refresh() {
  try {
    const res = await fetch('/api/graph');
    const data = await res.json();
    buildNetwork(data);
  } catch(e) { console.error('Error cargando grafo:', e); }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""

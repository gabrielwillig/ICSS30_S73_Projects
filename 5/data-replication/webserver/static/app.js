
function renderQuadrant(id, files, healthy) {
  const el = document.getElementById(id+'-content');
  if (!el) return;
  const statusDot = `<span style="display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:middle;background:${healthy ? '#0f0' : '#f00'}"></span>`;
  const titleEl = document.querySelector(`#${id} .qtitle`);
  if (titleEl) {
    if (!titleEl.dataset.base) titleEl.dataset.base = titleEl.textContent.replace(/^\s*\u25CF\s*/, '');
    titleEl.innerHTML = statusDot + titleEl.dataset.base;
  }
  if (!files.length) {
    el.innerHTML = '<em>No data</em>';
    return;
  }
  el.innerHTML = files.map(f => {
    // If file data is null, show a message
    if (f.data === null) {
      return `<div><div style='color:#6cf'>${f.name}</div><pre style='color:#f66'>Arquivo ausente ou inválido</pre></div>`;
    }
    return `<div><div style='color:#6cf'>${f.name}</div><pre>${JSON.stringify(f.data, null, 2)}</pre></div>`;
  }).join('');
}

async function checkHealth(peer) {
  try {
    const res = await fetch(`/api/health?peer=${encodeURIComponent(peer)}`);
    const data = await res.json();
    return data.healthy;
  } catch {
    return false;
  }
}
async function fetchFiles() {
  const res = await fetch('/api/files');
  const data = await res.json();
  const leaderFiles = data.files.filter(f => f.name.includes('leader'));
  const r1 = data.files.filter(f => f.name.includes('replica_1'));
  const r2 = data.files.filter(f => f.name.includes('replica_2'));
  const r3 = data.files.filter(f => f.name.includes('replica_3'));

  // Health checks (parallel)
  const [leaderHealthy, r1Healthy, r2Healthy, r3Healthy] = await Promise.all([
    checkHealth('leader'),
    checkHealth('replica_1'),
    checkHealth('replica_2'),
    checkHealth('replica_3')
  ]);

  renderQuadrant('leader', leaderFiles, leaderHealthy);
  renderQuadrant('replica1', r1, r1Healthy);
  renderQuadrant('replica2', r2, r2Healthy);
  renderQuadrant('replica3', r3, r3Healthy);
}

async function writeData() {
  const input = document.getElementById('write-input');
  const value = input.value.trim();
  if (!value) return;
  await fetch('/api/write', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: value })
  });
  input.value = '';
  fetchFiles();
}

async function readFromOffset() {
  const input = document.getElementById('offset-input');
  const value = input.value.trim();
  const res = await fetch('/api/read?offset=' + encodeURIComponent(value));
  const data = await res.json();
  const el = document.getElementById('read-result');
  el.innerHTML = '<pre>' + JSON.stringify(data.entries, null, 2) + '</pre>';
}

fetchFiles();
setInterval(fetchFiles, 2000);

window.writeData = writeData;
window.readFromOffset = readFromOffset;

function renderQuadrant(id, files) {
  const el = document.getElementById(id+'-content');
  if (!el) return;
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

async function fetchFiles() {
  const res = await fetch('/api/files');
  const data = await res.json();
  const leaderFiles = data.files.filter(f => f.name.includes('leader'));
  const r1 = data.files.filter(f => f.name.includes('replica_1'));
  const r2 = data.files.filter(f => f.name.includes('replica_2'));
  const r3 = data.files.filter(f => f.name.includes('replica_3'));
  renderQuadrant('leader', leaderFiles);
  renderQuadrant('replica1', r1);
  renderQuadrant('replica2', r2);
  renderQuadrant('replica3', r3);
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

/**
 * static/js/app.js
 * AI Digital Memory Guardian — Frontend Logic
 *
 * Handles all API communication and UI state management.
 * No framework — pure vanilla JS with fetch API.
 */

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  activeTab: 'ingest',
  apiKey: localStorage.getItem('mg_api_key') || '',
  model: localStorage.getItem('mg_model') || 'claude-3-5-haiku-20241022',
  stats: { chunks: 0, sources: 0 },
};

// ── API base ───────────────────────────────────────────────────────────────
const API = {
  async post(url, body, isFormData = false) {
    const opts = {
      method: 'POST',
      body: isFormData ? body : JSON.stringify(body),
    };
    if (!isFormData) opts.headers = { 'Content-Type': 'application/json' };
    const res = await fetch(url, opts);
    return res.json();
  },
  async get(url) {
    const res = await fetch(url);
    return res.json();
  },
  async delete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    return res.json();
  },
};

// ── Navigation ─────────────────────────────────────────────────────────────
function setTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('hidden', panel.id !== `panel-${tab}`);
  });
  if (tab === 'library') loadLibrary();
}

// ── Sidebar API key ────────────────────────────────────────────────────────
function saveApiKey() {
  const val = document.getElementById('sidebar-api-key').value.trim();
  state.apiKey = val;
  localStorage.setItem('mg_api_key', val);
  showToast('API key saved', 'success');
}

function saveModel() {
  const val = document.getElementById('sidebar-model').value;
  state.model = val;
  localStorage.setItem('mg_model', val);
}

// ── Toast notifications ────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  const icons = { success: '✓', error: '✗', info: 'ℹ' };
  toast.innerHTML = `<span class="toast-icon toast-${type}">${icons[type]}</span> ${msg}`;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// ── Stats update ───────────────────────────────────────────────────────────
async function refreshStats() {
  try {
    const data = await API.get('/api/library/');
    state.stats = { chunks: data.total_chunks, sources: data.sources.length };
    document.getElementById('stat-chunks').textContent = data.total_chunks;
    document.getElementById('stat-docs').textContent   = data.sources.length;
  } catch (_) {}
}

// ── Similarity score color ─────────────────────────────────────────────────
function scoreColor(score) {
  if (score >= 0.75) return '#10b981'; // green
  if (score >= 0.50) return '#8b5cf6'; // violet
  if (score >= 0.25) return '#f59e0b'; // amber
  return '#6b7280';                    // gray
}

// ── Render a memory card ───────────────────────────────────────────────────
function renderMemoryCard(r, type = 'semantic') {
  const score     = type === 'semantic' ? r.final_score : r.kw_score;
  const scoreLabel= type === 'semantic' ? 'Relevance' : 'KW Score';
  const extra     = type === 'semantic'
    ? `<span class="chip chip-dim">sim ${r.similarity?.toFixed(3)}</span>
       <span class="chip chip-dim">×${r.retrieved_n ?? 0} retrieved</span>`
    : `<span class="chip chip-dim">terms: ${(r.matched_terms || []).join(', ') || 'none'}</span>`;

  return `
    <div class="memory-card" style="--accent: ${scoreColor(score)}">
      <div class="card-header">
        <div class="card-badges">
          <span class="chip chip-score" style="color:${scoreColor(score)}; border-color:${scoreColor(score)}33">
            ${scoreLabel} ${(score * 100).toFixed(1)}%
          </span>
          <span class="chip chip-source">📄 ${r.source}</span>
          ${extra}
        </div>
      </div>
      <p class="card-text">${escHtml(r.text)}</p>
    </div>`;
}

function escHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ══════════════════════════════════════════════════════════════════════════
// INGEST
// ══════════════════════════════════════════════════════════════════════════

// Drag & drop
const dropzone = () => document.getElementById('dropzone');

function initDropzone() {
  const dz = dropzone();
  if (!dz) return;

  dz.addEventListener('dragover', e => {
    e.preventDefault();
    dz.classList.add('dragover');
  });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('dragover');
    const files = [...e.dataTransfer.files].filter(f => f.name.match(/\.(txt|md)$/i));
    if (files.length) handleFiles(files);
    else showToast('Only .txt and .md files are accepted', 'error');
  });
}

document.getElementById('file-input')?.addEventListener('change', e => {
  handleFiles([...e.target.files]);
});

function handleFiles(files) {
  const list = document.getElementById('file-list');
  list.innerHTML = '';
  files.forEach(f => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `<span>📄 ${f.name}</span><span class="file-size">${(f.size / 1024).toFixed(1)} KB</span>`;
    item.dataset.file = f.name;
    list._files = list._files || [];
    list._files.push(f);
    list.appendChild(item);
  });
}

async function ingestFiles() {
  const list  = document.getElementById('file-list');
  const files = list._files;
  const text  = document.getElementById('paste-text').value.trim();
  const name  = document.getElementById('paste-name').value.trim() || 'pasted_text';
  const btn   = document.getElementById('btn-ingest');

  if (!files?.length && !text) {
    showToast('Upload a file or paste text first', 'error');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Ingesting…';
  const progress = document.getElementById('ingest-progress');
  progress.classList.remove('hidden');

  try {
    // Ingest files
    if (files?.length) {
      for (let i = 0; i < files.length; i++) {
        const fd = new FormData();
        fd.append('file', files[i]);
        document.getElementById('progress-label').textContent =
          `Embedding ${files[i].name} (${i + 1}/${files.length})…`;
        const data = await API.post('/api/ingest/', fd, true);
        if (data.error) { showToast(data.error, 'error'); continue; }
        showToast(`✓ ${data.source}: ${data.chunks_added} chunks stored`, 'success');
      }
    }

    // Ingest pasted text
    if (text) {
      document.getElementById('progress-label').textContent = `Embedding "${name}"…`;
      const data = await API.post('/api/ingest/', { text, name });
      if (data.error) showToast(data.error, 'error');
      else showToast(`✓ ${data.source}: ${data.chunks_added} chunks stored`, 'success');
    }

    // Reset
    list.innerHTML = '';
    list._files    = null;
    document.getElementById('paste-text').value = '';
    document.getElementById('progress-label').textContent = 'Complete!';
    await refreshStats();
    setTimeout(() => progress.classList.add('hidden'), 1500);
  } catch (e) {
    showToast('Ingest failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Embed & Store';
  }
}

// ══════════════════════════════════════════════════════════════════════════
// QUERY
// ══════════════════════════════════════════════════════════════════════════
async function runQuery() {
  const query = document.getElementById('query-input').value.trim();
  const top_k = parseInt(document.getElementById('query-topk').value);
  const btn   = document.getElementById('btn-query');

  if (!query) { showToast('Enter a query', 'error'); return; }

  btn.disabled    = true;
  btn.textContent = 'Searching…';
  document.getElementById('query-results').innerHTML = loadingHTML('Searching memory…');

  try {
    const data = await API.post('/api/query/', {
      query, top_k,
      api_key: state.apiKey,
      model:   state.model,
    });

    if (data.error) { showToast(data.error, 'error'); return; }

    let html = `<h3 class="results-title">🎯 ${data.results.length} Memory Matches</h3>`;
    html += data.results.map(r => renderMemoryCard(r, 'semantic')).join('');

    if (data.answer) {
      html += `
        <div class="answer-box">
          <div class="answer-header">
            <span class="answer-icon">🤖</span>
            <span>AI Answer <span class="answer-model">${data.usage?.model ?? ''}</span></span>
            ${data.usage ? `<span class="token-count">${data.usage.input_tokens}↑ ${data.usage.output_tokens}↓ tokens</span>` : ''}
          </div>
          <div class="answer-text">${escHtml(data.answer)}</div>
        </div>`;
    } else if (!state.apiKey) {
      html += `<p class="hint-text">💡 Add your Anthropic API key in the sidebar to get an AI-generated answer.</p>`;
    }

    document.getElementById('query-results').innerHTML = html;
    await refreshStats();
  } catch (e) {
    showToast('Query failed: ' + e.message, 'error');
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Search Memory';
  }
}

// ══════════════════════════════════════════════════════════════════════════
// COMPARE
// ══════════════════════════════════════════════════════════════════════════
async function runCompare() {
  const query = document.getElementById('compare-input').value.trim();
  const top_k = parseInt(document.getElementById('compare-topk').value);
  const btn   = document.getElementById('btn-compare');

  if (!query) { showToast('Enter a query', 'error'); return; }

  btn.disabled    = true;
  btn.textContent = 'Running…';
  document.getElementById('col-keyword').innerHTML  = loadingHTML('Running keyword search…');
  document.getElementById('col-semantic').innerHTML = loadingHTML('Running semantic search…');

  try {
    const data = await API.post('/api/compare/', {
      query, top_k,
      api_key: state.apiKey,
      model:   state.model,
    });

    // Keyword column
    const kwHtml = data.keyword.length
      ? data.keyword.map(r => renderMemoryCard(r, 'keyword')).join('')
      : `<div class="empty-state">No keyword matches found.<br><span class="hint-text">These exact words don't appear in your documents.</span></div>`;
    document.getElementById('col-keyword').innerHTML =
      `<h4 class="col-title col-title-kw">🔤 Keyword Results <span class="count-badge">${data.keyword.length}</span></h4>` + kwHtml;

    // Semantic column
    const semHtml = data.semantic.length
      ? data.semantic.map(r => renderMemoryCard(r, 'semantic')).join('')
      : `<div class="empty-state">No semantic matches found.</div>`;
    let semExtra = '';
    if (data.answer) {
      semExtra = `
        <div class="answer-box" style="margin-top:16px">
          <div class="answer-header"><span class="answer-icon">🤖</span> AI Answer</div>
          <div class="answer-text">${escHtml(data.answer)}</div>
        </div>`;
    }
    document.getElementById('col-semantic').innerHTML =
      `<h4 class="col-title col-title-sem">🧠 Semantic Results <span class="count-badge">${data.semantic.length}</span></h4>`
      + semHtml + semExtra;

    await refreshStats();
  } catch (e) {
    showToast('Compare failed: ' + e.message, 'error');
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Run Comparison';
  }
}

// ══════════════════════════════════════════════════════════════════════════
// LIBRARY
// ══════════════════════════════════════════════════════════════════════════
async function loadLibrary() {
  const container = document.getElementById('library-content');
  container.innerHTML = loadingHTML('Loading library…');

  try {
    const data = await API.get('/api/library/');
    if (!data.sources.length) {
      container.innerHTML = `<div class="empty-state">No documents yet.<br><span class="hint-text">Go to Ingest to add your first document.</span></div>`;
      return;
    }

    const rows = data.sources.map(s => `
      <div class="library-row">
        <div class="lib-info">
          <span class="lib-name">📄 ${escHtml(s.source)}</span>
          <span class="lib-meta">${s.chunk_count} chunks · retrieved ${s.total_retrieved}× · ${s.upload_date}</span>
        </div>
        <button class="btn btn-danger btn-sm" onclick="deleteSource('${encodeURIComponent(s.source)}')">Delete</button>
      </div>`).join('');

    container.innerHTML = `
      <div class="lib-stats">
        <span>${data.sources.length} documents</span>
        <span>${data.total_chunks} chunks total</span>
        <span class="lib-db-path">DB: ./chroma_db/ (persistent)</span>
      </div>
      <div class="library-list">${rows}</div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state error-text">Failed to load library.</div>`;
  }
}

async function deleteSource(encodedSource) {
  const source = decodeURIComponent(encodedSource);
  if (!confirm(`Delete all chunks from "${source}"?`)) return;
  await API.delete(`/api/library/${encodedSource}/`);
  showToast(`Deleted "${source}"`, 'success');
  await loadLibrary();
  await refreshStats();
}

// ── Utilities ──────────────────────────────────────────────────────────────
function loadingHTML(msg) {
  return `<div class="loading-state"><div class="spinner"></div><span>${msg}</span></div>`;
}

// Enter key → submit
document.getElementById('query-input')?.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runQuery(); }
});
document.getElementById('compare-input')?.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runCompare(); }
});

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Restore saved API key
  if (state.apiKey) document.getElementById('sidebar-api-key').value = state.apiKey;
  if (state.model)  document.getElementById('sidebar-model').value   = state.model;

  setTab('ingest');
  initDropzone();
  refreshStats();

  // Poll stats every 10s while app is open
  setInterval(refreshStats, 10000);
});

/* Meme Cardnews GUI */

// crypto.randomUUID() only exists in a secure context (HTTPS or localhost).
// On plain-HTTP / IP access (e.g. http://<server-ip>:8501) it is undefined and
// throws, which would kill this whole script before init() ever runs.
function genSessionId() {
  if (window.crypto && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 12);
  }
  let s = '';
  while (s.length < 12) s += Math.random().toString(16).slice(2);
  return s.slice(0, 12);
}

let sessionId = genSessionId();
let selectedPost = null;
let selectedFormat = 'classic_dark';
let hashtags = [];
let currentStep = 1;

let activeHandle = '';
let activeDemographic = '';

// --- Utilities ---
function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`${res.status} /api${path} — ${detail.slice(0, 200)}`);
  }
  return res.json();
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

// --- Init ---
async function init() {
  updateCharCounts();
  try {
    await loadAccountInfo();
  } catch (e) {
    console.error('loadAccountInfo failed:', e);
    toast('계정 정보 로드 실패 — 콘솔(F12) 확인', 'error');
  }
  try {
    await loadSettingsStatus();
  } catch (e) {
    console.error('loadSettingsStatus failed:', e);
    const el = document.getElementById('statusKeys');
    el.className = 'status-dot red';
    el.textContent = 'API 확인 실패';
  }
}

// --- Settings ---
async function loadAccountInfo() {
  const data = await api('/accounts');
  const demoSel = document.getElementById('settingDemo');

  // 밈 계정은 1개뿐이라 첫 계정으로 고정 (선택 UI 없음)
  activeHandle = (data.accounts && data.accounts[0]) ? data.accounts[0].handle : 'TBD_meme';

  demoSel.innerHTML = '';
  for (const c of (data.categories || [])) {
    // value(20s/30s/40s)는 내부용으로 백엔드에 넘기고, 화면엔 "20대"처럼 깔끔하게만
    demoSel.innerHTML += `<option value="${c.demographic}">${c.label_ko.replace(/^밈/, '')}</option>`;
  }

  activeDemographic = demoSel.value;
  updateStatusBar();

  demoSel.addEventListener('change', () => { activeDemographic = demoSel.value; updateStatusBar(); });
}

async function loadSettingsStatus() {
  const data = await api('/settings');
  const el = document.getElementById('statusKeys');

  if (data.keys_configured) {
    el.className = 'status-dot green';
    el.textContent = 'API 연결됨';
  } else {
    el.className = 'status-dot red';
    el.textContent = 'API 키 미설정';
  }
}

function updateStatusBar() {
  document.getElementById('statusAccount').textContent = `계정: ${activeHandle || '-'}`;
}

// --- Step Navigation ---
function goStep(n) {
  currentStep = n;
  document.querySelectorAll('.step-panel').forEach((p, i) => {
    p.classList.toggle('active', i + 1 === n);
  });
  document.querySelectorAll('.step-indicator').forEach((el, i) => {
    el.classList.remove('active', 'done');
    if (i + 1 === n) el.classList.add('active');
    else if (i + 1 < n) el.classList.add('done');
  });

  if (n === 3) loadFormats();
  if (n === 4) renderPreview();
}

// --- Step 1: Post Selection ---
document.getElementById('btnCrawl').addEventListener('click', async () => {
  const status = document.getElementById('crawlStatus');
  const btn = document.getElementById('btnCrawl');
  btn.disabled = true;
  status.innerHTML = '<span class="spinner"></span>크롤링 중... (30~60초 소요)';

  try {
    const data = await api('/crawl', { method: 'POST' });
    if (data.error) throw new Error(data.error);
    status.textContent = `완료: ${data.saved_count}개 새 글 저장`;
    toast(`${data.saved_count}개 새 글 크롤링 완료`, 'success');
    loadPosts();
  } catch (e) {
    status.textContent = `오류: ${e.message}`;
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('btnLoadExisting').addEventListener('click', loadPosts);

async function loadPosts() {
  const container = document.getElementById('postList');
  container.innerHTML = '<span class="loading-text"><span class="spinner"></span>불러오는 중...</span>';

  const data = await api('/posts?limit=30');
  if (!data.posts || data.posts.length === 0) {
    container.innerHTML = '<p style="color:#888">글이 없습니다. 크롤링을 먼저 실행하세요.</p>';
    return;
  }

  let html = `<table class="post-table">
    <thead><tr>
      <th style="width:40px"></th>
      <th>제목</th>
      <th>출처</th>
      <th>점수</th>
      <th>좋아요</th>
      <th>댓글</th>
      <th>링크</th>
    </tr></thead><tbody>`;

  for (const p of data.posts) {
    html += `<tr data-id="${p.id}" onclick="selectPost(${p.id}, this)">
      <td><input type="radio" name="post" value="${p.id}"></td>
      <td class="title-cell" title="${esc(p.title)}">${esc(p.title)}</td>
      <td><span class="source-badge">${esc(p.source_name)}</span></td>
      <td class="score-cell">${p.score}</td>
      <td>${p.likes}</td>
      <td>${p.comment_count}</td>
      <td><a class="link-btn" href="${esc(p.url)}" target="_blank" onclick="event.stopPropagation()">열기</a></td>
    </tr>`;
  }
  html += '</tbody></table>';
  container.innerHTML = html;
}

function selectPost(id, row) {
  document.querySelectorAll('.post-table tr.selected').forEach(r => r.classList.remove('selected'));
  row.classList.add('selected');
  row.querySelector('input[type=radio]').checked = true;

  const cells = row.querySelectorAll('td');
  selectedPost = {
    id,
    title: cells[1].textContent,
    source: cells[2].textContent,
    url: row.querySelector('.link-btn')?.href || '',
  };
  document.getElementById('btnStep1Next').disabled = false;
}

document.getElementById('btnStep1Next').addEventListener('click', () => {
  if (!selectedPost) return;
  const info = document.getElementById('selectedPostInfo');
  info.innerHTML = `
    <div>
      <div class="title">${esc(selectedPost.title)}</div>
      <div class="meta">${esc(selectedPost.source)}</div>
    </div>
    <a class="link-btn" href="${esc(selectedPost.url)}" target="_blank">원문 보기</a>`;
  goStep(2);
});

// --- Step 2: Screenshot Upload ---
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

['dragenter', 'dragover'].forEach(e => {
  dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.add('dragover'); });
});
['dragleave', 'drop'].forEach(e => {
  dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.remove('dragover'); });
});

dropZone.addEventListener('drop', ev => uploadFiles(ev.dataTransfer.files));
fileInput.addEventListener('change', ev => uploadFiles(ev.target.files));

// 클립보드 붙여넣기(Ctrl+V) — 캡처/복사한 이미지를 바로 업로드 (스크린샷 단계에서만)
document.addEventListener('paste', ev => {
  if (currentStep !== 2) return;
  const items = (ev.clipboardData && ev.clipboardData.items) || [];
  const images = [];
  for (const it of items) {
    if (it.kind === 'file' && it.type.startsWith('image/')) {
      const f = it.getAsFile();
      if (f) images.push(f);
    }
  }
  if (images.length) {
    ev.preventDefault();
    uploadFiles(images);
  }
});

async function uploadFiles(fileList) {
  if (!fileList.length) return;
  const form = new FormData();
  form.append('session_id', sessionId);
  for (const f of fileList) form.append('files', f);

  toast('업로드 중...', 'info');
  const data = await api('/uploads', { method: 'POST', body: form });
  if (data.all) {
    renderThumbs(data.all);
    toast(`${data.uploaded.length}개 업로드 완료`, 'success');
  }
  fileInput.value = '';
}

function renderThumbs(files) {
  const strip = document.getElementById('thumbStrip');
  strip.innerHTML = '';
  files.forEach((f, i) => {
    const div = document.createElement('div');
    div.className = 'thumb-item';
    div.draggable = true;
    div.dataset.filename = f.filename;
    div.innerHTML = `
      <img src="/api/uploads/${sessionId}/${f.filename}" alt="">
      <button class="thumb-del" onclick="deleteUpload('${f.filename}')">&times;</button>
      <span class="thumb-num">${i === 0 ? 'COVER' : i + 1}</span>`;
    strip.appendChild(div);
  });

  document.getElementById('btnStep2Next').disabled = files.length === 0;
  setupDragSort();
}

async function deleteUpload(filename) {
  const data = await api(`/uploads/${filename}?session_id=${sessionId}`, { method: 'DELETE' });
  renderThumbs(data.files);
}

function setupDragSort() {
  const strip = document.getElementById('thumbStrip');
  let dragged = null;

  strip.querySelectorAll('.thumb-item').forEach(item => {
    item.addEventListener('dragstart', () => { dragged = item; item.style.opacity = '0.4'; });
    item.addEventListener('dragend', () => { dragged = null; item.style.opacity = '1'; });
    item.addEventListener('dragover', e => e.preventDefault());
    item.addEventListener('drop', async e => {
      e.preventDefault();
      if (dragged && dragged !== item) {
        const items = [...strip.children];
        const fromIdx = items.indexOf(dragged);
        const toIdx = items.indexOf(item);
        if (fromIdx < toIdx) item.after(dragged);
        else item.before(dragged);

        const order = [...strip.children].map(c => c.dataset.filename).join(',');
        const form = new FormData();
        form.append('session_id', sessionId);
        form.append('order', order);
        const data = await api('/uploads/reorder', { method: 'POST', body: form });
        renderThumbs(data.files);
      }
    });
  });
}

document.getElementById('btnStep2Next').addEventListener('click', () => goStep(3));

// --- Step 3: Format & Text ---
async function loadFormats() {
  const grid = document.getElementById('formatGrid');
  const data = await api('/formats');

  grid.innerHTML = '';
  for (const f of (data.formats || [])) {
    const card = document.createElement('div');
    card.className = `format-card${f.id === selectedFormat ? ' selected' : ''}`;
    card.onclick = () => {
      selectedFormat = f.id;
      grid.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
    };
    card.innerHTML = `
      <div class="format-thumb">${f.thumbnail ? `<img src="/format-thumbnails/${f.thumbnail}" alt="">` : '?'}</div>
      <div class="format-info">
        <div class="format-name">${esc(f.name)}</div>
        <div class="format-desc">${esc(f.description)}</div>
      </div>`;
    grid.appendChild(card);
  }

  if (!data.formats || data.formats.length === 0) {
    grid.innerHTML = '<div style="color:#888;padding:20px;">기본 포맷을 사용합니다.</div>';
  }
}

document.getElementById('btnGenerate').addEventListener('click', async () => {
  if (!selectedPost) { toast('글을 먼저 선택하세요', 'error'); return; }
  const status = document.getElementById('genStatus');
  const btn = document.getElementById('btnGenerate');
  btn.disabled = true;
  status.innerHTML = '<span class="spinner"></span>AI 텍스트 생성 중... (10~20초)';

  try {
    const data = await api('/generate-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: selectedPost.id, demographic: activeDemographic || '20s' }),
    });

    if (data.error) throw new Error(data.error);

    document.getElementById('hookText').value = data.hook_text || '';
    document.getElementById('punchline').value = data.punchline || '';
    document.getElementById('caption').value = data.caption || '';
    updateCharCounts();

    hashtags = data.hashtags || [];
    renderHashtags();

    status.textContent = 'AI 텍스트 생성 완료 - 자유롭게 수정하세요';
    toast('텍스트 생성 완료', 'success');
  } catch (e) {
    status.textContent = `오류: ${e.message}`;
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
});

// Char counters
['hookText', 'punchline', 'caption'].forEach(id => {
  document.getElementById(id).addEventListener('input', updateCharCounts);
});

function updateCharCounts() {
  const h = document.getElementById('hookText').value.length;
  const p = document.getElementById('punchline').value.length;
  const c = document.getElementById('caption').value.length;
  document.getElementById('hookCount').textContent = `${h}/35`;
  document.getElementById('punchCount').textContent = `${p}/30`;
  document.getElementById('captionCount').textContent = c;
}

// Hashtags
function renderHashtags() {
  const container = document.getElementById('tagsContainer');
  container.querySelectorAll('.tag').forEach(t => t.remove());
  const input = document.getElementById('tagInput');

  for (const tag of hashtags) {
    const span = document.createElement('span');
    span.className = 'tag';
    span.innerHTML = `${esc(tag)} <button onclick="removeTag('${esc(tag)}')">&times;</button>`;
    container.insertBefore(span, input);
  }
}

function removeTag(tag) {
  hashtags = hashtags.filter(t => t !== tag);
  renderHashtags();
}

document.getElementById('tagInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    let val = e.target.value.trim();
    if (!val) return;
    if (!val.startsWith('#')) val = '#' + val;
    if (!hashtags.includes(val)) {
      hashtags.push(val);
      renderHashtags();
    }
    e.target.value = '';
  }
});

// --- Step 4: Preview ---
document.getElementById('btnPreview').addEventListener('click', () => goStep(4));
document.getElementById('btnRerender').addEventListener('click', renderPreview);

async function renderPreview() {
  const strip = document.getElementById('previewStrip');
  const status = document.getElementById('previewStatus');
  strip.innerHTML = '';
  status.innerHTML = '<span class="spinner"></span>렌더링 중... (5~10초)';

  try {
    const body = {
      session_id: sessionId,
      format_id: selectedFormat,
      hook_text: document.getElementById('hookText').value,
      punchline: document.getElementById('punchline').value,
      caption: document.getElementById('caption').value,
      hashtags: hashtags,
      handle: activeHandle || 'TBD_meme',
    };

    const data = await api('/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (data.error) throw new Error(data.error);

    for (const slide of (data.slides || [])) {
      const div = document.createElement('div');
      div.className = 'preview-slide';
      div.innerHTML = `
        <img src="data:image/jpeg;base64,${slide.base64}" alt="slide ${slide.index}">
        <span class="slide-num">${slide.index}</span>`;
      strip.appendChild(div);
    }

    status.textContent = `${data.slides.length}장 렌더링 완료 - 확인 후 업로드하세요`;
    toast('미리보기 완료', 'success');
  } catch (e) {
    status.textContent = `오류: ${e.message}`;
    toast(e.message, 'error');
  }
}

// --- Step 5: Finalize ---
document.getElementById('btnFinalize').addEventListener('click', async () => {
  const btn = document.getElementById('btnFinalize');
  btn.disabled = true;
  btn.textContent = '업로드 중...';

  try {
    const body = {
      session_id: sessionId,
      format_id: selectedFormat,
      hook_text: document.getElementById('hookText').value,
      punchline: document.getElementById('punchline').value,
      caption: document.getElementById('caption').value,
      hashtags: hashtags,
      handle: activeHandle || 'TBD_meme',
      demographic: activeDemographic || '20s',
      post_id: selectedPost?.id || null,
    };

    const data = await api('/finalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (data.error) throw new Error(data.error);

    const box = document.getElementById('resultBox');
    if (data.drive_url) {
      box.innerHTML = `
        <div class="check">&#10003;</div>
        <h2 style="color:#fff;margin-bottom:12px;">업로드 완료!</h2>
        <a class="drive-link" href="${data.drive_url}" target="_blank">Google Drive에서 보기</a>
        <br><br>
        <button class="btn btn-secondary" onclick="resetAll()">새 포스트 만들기</button>`;
    } else {
      box.innerHTML = `
        <div class="check">&#10003;</div>
        <h2 style="color:#fff;margin-bottom:12px;">렌더링 완료</h2>
        <p style="color:#999;margin-bottom:12px;">로컬 저장: ${esc(data.output_dir || '')}</p>
        <button class="btn btn-secondary" onclick="resetAll()">새 포스트 만들기</button>`;
    }

    goStep(5);
    toast('업로드 완료!', 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '확정 & 업로드';
  }
});

function resetAll() {
  sessionId = genSessionId();
  selectedPost = null;
  hashtags = [];
  document.getElementById('hookText').value = '';
  document.getElementById('punchline').value = '';
  document.getElementById('caption').value = '';
  document.getElementById('thumbStrip').innerHTML = '';
  document.getElementById('previewStrip').innerHTML = '';
  document.getElementById('btnStep1Next').disabled = true;
  document.getElementById('btnStep2Next').disabled = true;
  document.getElementById('genStatus').textContent = '';
  document.getElementById('crawlStatus').textContent = '';
  updateCharCounts();
  renderHashtags();
  goStep(1);
}

// Init on load
init();

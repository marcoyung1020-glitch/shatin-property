(() => {
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = (n, d = 0) => n == null || isNaN(n) ? '—' : Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const money = n => '$' + fmt(Math.round(n));
const wan = n => fmt(n, n % 1 ? 1 : 0) + '萬';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SRC = { midland: '美聯', centanet: '中原', ricacorp: '利嘉閣' };
const H_CAP = 3.25, H_SPREAD = 1.3;
let DATA, EST = {}, charts = {};

/* ---------- 分頁 ---------- */
const TABS = ['market', 'listings', 'estates', 'calc'];
function route() {
  const h = (location.hash || '#market').slice(1).split('?')[0];
  const t = TABS.includes(h) ? h : 'market';
  TABS.forEach(x => { $('#view-' + x).hidden = x !== t; });
  $$('.tabs a').forEach(a => a.classList.toggle('on', a.dataset.tab === t));
  if (t === 'calc') calc();
  window.scrollTo({ top: 0 });
}
window.addEventListener('hashchange', route);

/* ---------- 載入 ---------- */
fetch('data/app.json').then(r => r.json()).then(d => {
  DATA = d;
  d.estates.forEach(e => EST[e.id] = e);
  enrich(d);
  const g = (d.generated || '').replace('T', ' ').slice(0, 16);
  $('#stamp').textContent = '數據更新：' + g;
  route();
  initMarket(); initListings(); initEstates(); initCalc();
}).catch(err => { $('#stamp').textContent = '數據載入失敗'; console.error(err); });

/* ---------- 市場追蹤 ---------- */
function kpi(l, v, d, cls = '', dcls = '') {
  return `<div class="kpi ${cls}"><span class="l">${l}</span><span class="v">${v}</span><span class="d ${dcls}">${d}</span></div>`;
}
const pct = x => (x > 0 ? '▲ ' : x < 0 ? '▼ ' : '') + fmt(Math.abs(x), 2) + '%';
const dir = x => x > 0 ? 'up' : x < 0 ? 'down' : '';

function initMarket() {
  const m = DATA.market, c = m.ccl_latest || {};
  const hb = m.hibor_daily || [], hl = hb[hb.length - 1] || [];
  const lr = m.landreg || [], l1 = lr[lr.length - 1], l0 = lr[lr.length - 2], l12 = lr.find(r => l1 && r[0] === (Number(l1[0].slice(0, 4)) - 1) + l1[0].slice(4));
  const rv = m.rvd_index || [], r1 = rv[rv.length - 1], r0 = rv[rv.length - 2];
  const hEff = hl[2] != null ? Math.min(hl[2] + H_SPREAD, H_CAP) : null;
  const cw = c.ccl || {}, ne = c.nte || {};
  const ccl1 = (m.ccl_weekly || []).slice(-1)[0];
  const ytd0 = (m.ccl_weekly || []).filter(r => r[0] < ccl1[0].slice(0, 4) + '-01-01').pop();
  const ytd = ytd0 ? (ccl1[1] / ytd0[1] - 1) * 100 : null;
  const pub = (cw.publishDate || '').slice(5, 10).replace('-', '/');
  $('#kpis').innerHTML = [
    kpi('CCL 整體', fmt(cw.index, 2), `<span class="${dir(cw.trendChangeWeek)}">${pct(cw.trendChangeWeek)}</span> 按週 · 今年 ${ytd != null ? (ytd > 0 ? '+' : '') + fmt(ytd, 1) + '%' : '—'}`, 'accent'),
    kpi('CCL 新界東', fmt(ne.index, 2), `<span class="${dir(ne.trendChangeWeek)}">${pct(ne.trendChangeWeek)}</span> 按週 · ${pub} 公佈`),
    kpi('1個月 HIBOR', fmt(hl[2], 3) + '%', `${(hl[0] || '').slice(5).replace('-', '/')} 定價 · 隔夜 ${fmt(hl[1], 2)}%`),
    kpi('H按實際息率', fmt(hEff, 2) + '%', hEff >= H_CAP ? '已觸及封頂 P − 1.75%' : `H + 1.3%，未觸封頂`),
    kpi(`${l1 ? Number(l1[0].slice(5)) : ''}月住宅買賣登記`, fmt(l1 && l1[1]), l1 && l0 ? `<span class="${dir(l1[1] - l0[1])}">${pct((l1[1] / l0[1] - 1) * 100)}</span> 按月${l12 ? ` · ${pct((l1[1] / l12[1] - 1) * 100)} 按年` : ''}` : ''),
    kpi('差估署樓價指數', fmt(r1 && r1[1], 1), r1 && r0 ? `${r1[0].replace('-', '年')}月 · <span class="${dir(r1[1] - r0[1])}">${pct((r1[1] / r0[1] - 1) * 100)}</span> 按月` : '')
  ].join('');
  $('#r-h').textContent = fmt(hEff, 2) + '%';
  if (!window.Chart) { setTimeout(initMarket, 200); return; }
  drawCharts();
}

const X = () => ({ grid: { display: false }, ticks: { maxTicksLimit: innerWidth < 560 ? 4 : 7, maxRotation: 0, autoSkipPadding: 16,
  callback(v) { const l = String(this.getLabelForValue(v)); return l.length >= 7 ? l.slice(2, 7).replace('-', '/') : l; } } });
function baseOpts(extra = {}) {
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue('--color-text-muted').trim(), grid = css.getPropertyValue('--color-divider').trim();
  Chart.defaults.font.family = css.getPropertyValue('--font-body');
  Chart.defaults.font.size = 12;
  Chart.defaults.color = muted;
  return Object.assign({
    responsive: true, maintainAspectRatio: false, animation: { duration: 600 },
    interaction: { mode: 'index', intersect: false },
    plugins: { legend: { position: 'top', align: innerWidth < 560 ? 'start' : 'end', labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: 'circle', pointStyleWidth: 8, padding: 10, font: { size: 11 } } }, tooltip: { padding: 10 } },
    scales: { x: X(), y: { grid: { color: grid }, border: { display: false } } }
  }, extra);
}
const line = (label, data, color, o = {}) => Object.assign({ label, data, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 0, tension: .2 }, o);

function drawCharts() {
  const m = DATA.market;
  // CCL
  const drawCCL = n => {
    const w = (m.ccl_weekly || []).slice(-n);
    charts.ccl && charts.ccl.destroy();
    charts.ccl = new Chart($('#c-ccl'), { type: 'line', data: { labels: w.map(r => r[0]), datasets: [line('CCL 整體', w.map(r => r[1]), '#0b5f63'), line('新界東', w.map(r => r[2]), '#c9650a')] }, options: baseOpts() });
  };
  drawCCL(156);
  $$('[data-ccl]').forEach(b => b.onclick = () => { $$('[data-ccl]').forEach(x => x.classList.toggle('on', x === b)); drawCCL(+b.dataset.ccl); });
  // HIBOR
  const hb = m.hibor_daily || [];
  charts.h = new Chart($('#c-hibor'), { type: 'line', data: { labels: hb.map(r => r[0]), datasets: [
    line('1M HIBOR', hb.map(r => r[2]), '#1f5f8b'),
    line('H按實際（H+1.3%）', hb.map(r => Math.min(r[2] + H_SPREAD, H_CAP)), '#0b5f63', { borderWidth: 4, order: 2 }),
    line('封頂 3.25%', hb.map(() => H_CAP), '#a3324a', { borderDash: [5, 4], borderWidth: 1.5, order: 0 })
  ] }, options: baseOpts({ scales: { x: X(), y: { ticks: { callback: v => v + '%' } } } }) });
  // 土地註冊處
  const lr = (m.landreg || []).slice(-36);
  charts.lr = new Chart($('#c-lr'), { type: 'bar', data: { labels: lr.map(r => r[0]), datasets: [
    { type: 'bar', label: '住宅買賣宗數', data: lr.map(r => r[1]), backgroundColor: '#9fc3bf', borderRadius: 2, yAxisID: 'y' },
    line('總值（億元）', lr.map(r => r[3] ? r[3] / 100 : null), '#c9650a', { yAxisID: 'y1', type: 'line' })
  ] }, options: baseOpts({ scales: { x: X(), y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } } }) });
  // RVD
  const rv = (m.rvd_index || []).filter(r => r[0] >= '2018-01');
  charts.rv = new Chart($('#c-rvd'), { type: 'line', data: { labels: rv.map(r => r[0]), datasets: [
    line('樓價指數（全港）', rv.map(r => r[1]), '#0b5f63'),
    line('租金指數（全港）', rv.map(r => r[2]), '#c9650a', { yAxisID: 'y1' })
  ] }, options: baseOpts({ scales: { x: X(), y: { title: { display: true, text: '樓價' } }, y1: { position: 'right', grid: { display: false }, title: { display: true, text: '租金' } } } }) });
}

/* ---------- 租金回報、市價基準 ---------- */
const median = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const BELOW = 5, BELOW_STRONG = 10;
const roomKey = r => r == null ? '?' : r >= 3 ? 3 : r;
function enrich(d) {
  // 呎租：屋苑樣本 ≥3 用屋苑，否則用同區屋苑中位
  const areaRent = {};
  d.estates.forEach(e => { if (e.rent_psf && e.rent_n >= 3) (areaRent[e.area] ||= []).push(e.rent_psf); });
  const allRent = median(d.estates.filter(e => e.rent_psf && e.rent_n >= 3).map(e => e.rent_psf));
  d.estates.forEach(e => {
    if (e.rent_psf && e.rent_n >= 3) { e._rent = e.rent_psf; e._rentEst = false; }
    else { e._rent = median(areaRent[e.area] || []) || allRent; e._rentEst = true; }
  });
  // 市價基準：同屋苑同房數放盤中位呎價（≥5 個），否則全屋苑中位
  const byE = {}, byER = {};
  d.listings.forEach(x => { if (!x.f) return; (byE[x.e] ||= []).push(x.f); (byER[x.e + '|' + roomKey(x.r)] ||= []).push(x.f); });
  const mE = {}, mER = {};
  Object.entries(byE).forEach(([k, v]) => mE[k] = median(v));
  Object.entries(byER).forEach(([k, v]) => mER[k] = v.length >= 5 ? { m: median(v), n: v.length } : null);
  d.listings.forEach(x => {
    const e = EST[x.e] || {};
    x.y = e._rent && x.a && x.p ? +(e._rent * x.a * 12 / (x.p * 1e4) * 100).toFixed(2) : null;
    x.yEst = !!e._rentEst;
    const g = r => mER[x.e + '|' + roomKey(x.r)];
    const b = x.r != null && g() ? g() : null;
    x.bm = b ? b.m : mE[x.e] || null;
    x.bmBy = b ? (x.r >= 3 ? '3房或以上' : x.r === 0 ? '開放式' : x.r + '房') : '全屋苑';
    x.dc = x.f && x.bm ? +((1 - x.f / x.bm) * 100).toFixed(1) : null;
  });
}
function belowTag(x) {
  if (x.dc == null || x.dc < BELOW) return '';
  return `<span class="below${x.dc >= BELOW_STRONG ? ' strong' : ''}" title="同屋苑${x.bmBy}放盤中位呎價 $${fmt(x.bm)}">低於市價 ${fmt(x.dc, 0)}%</span>`;
}
const yieldTxt = x => x.y == null ? '—' : fmt(x.y, 2) + '%' + (x.yEst ? '<span class="est-mark" title="屋苑放租樣本不足，用同區屋苑中位呎租估算">估</span>' : '');

/* ---------- 放盤 ---------- */
let shown = 60;
function initListings() {
  const sel = $('#f-estate');
  DATA.estates.forEach(e => sel.insertAdjacentHTML('beforeend', `<option value="${e.id}">${esc(e.name)}（${esc(e.area)}）</option>`));
  $('#filters').addEventListener('input', () => { shown = 60; renderListings(); });
  $('#more').onclick = () => { shown += 60; renderListings(); };
  // 撳表頭排序；再撳一次倒轉
  const first = { p: 'asc', f: 'asc', a: 'desc', pd: 'desc', y: 'desc' };
  $$('#tbl-list th[data-sort] button').forEach(b => b.onclick = () => {
    const k = b.parentElement.dataset.sort, [ck, cd] = $('#f-sort').value.split(':');
    const d = ck === k ? (cd === 'asc' ? 'desc' : 'asc') : first[k];
    $('#f-sort').value = `${k}:${d}`; shown = 60; renderListings();
  });
  const q = new URLSearchParams((location.hash.split('?')[1]) || '');
  if (q.get('e')) sel.value = q.get('e');
  const n = DATA.listings.length;
  const stale = Object.entries(DATA.status || {}).filter(([, v]) => !v.ok).map(([k, v]) => `${SRC[k]}（資料停留喺 ${(v.last_ok || '').replace('T', ' ')}）`);
  if (stale.length) { const w = $('#stale-note'); w.hidden = false; w.textContent = `注意：今次更新讀唔到 ${stale.join('、')}，暫時顯示上次資料。`; }
  $('#list-sub').textContent = `${n.toLocaleString()} 條放盤記錄 · 3 間代理 · 15 個屋苑`;
  renderListings();
}
function filtered() {
  const e = $('#f-estate').value, max = +$('#f-max').value || Infinity, rooms = $('#f-rooms').value,
    area = +$('#f-area').value || 0, psf = +$('#f-psf').value || Infinity, srcs = new Set($$('.srcs input:checked').map(i => i.value)), below = $('#f-below').checked;
  return DATA.listings.filter(x => (!e || x.e === e) && x.p <= max && srcs.has(x.s) && (!area || (x.a || 0) >= area) && (psf === Infinity || (x.f && x.f <= psf)) &&
    (rooms === '' || (rooms === '3' ? x.r >= 3 : x.r === +rooms)) && (!below || x.dc >= BELOW));
}
const floorKey = f => /高/.test(f) ? '高' : /中/.test(f) ? '中' : /低|地/.test(f) ? '低' : '';
function renderListings() {
  let L = filtered();
  const merge = $('#f-merge').checked;
  let rows;
  if (merge) {
    const g = new Map();
    L.forEach(x => {
      const k = x.a ? [x.e, x.a, x.r ?? '?'].join('|') : 'u' + Math.random();
      if (!g.has(k)) g.set(k, []);
      g.get(k).push(x);
    });
    // 同面積同房數再按樓層細分；冇樓層資料嘅歸入最大組
    const g2 = new Map();
    g.forEach((arr, k) => {
      const b = {};
      arr.filter(x => floorKey(x.fl)).forEach(x => (b[floorKey(x.fl)] ||= []).push(x));
      const keys = Object.keys(b);
      const blank = arr.filter(x => !floorKey(x.fl));
      if (!keys.length) { g2.set(k, blank); return; }
      const big = keys.sort((a, c) => b[c].length - b[a].length)[0];
      b[big].push(...blank);
      keys.forEach(f => g2.set(k + f, b[f]));
    });
    rows = [...g2.values()].map(arr => { arr.sort((a, b) => a.p - b.p); return { ...arr[0], all: arr }; });
  } else rows = L.map(x => ({ ...x, all: [x] }));
  // 首次出現：同一單位取各網站最早嘅日期
  const rank = y => (y.pq === 'base' ? '~' : '') + (y.pd || '9');
  rows.forEach(x => { x.first = x.all.reduce((m, y) => (!m || rank(y) < rank(m)) ? y : m, null); });
  const [key, dir] = $('#f-sort').value.split(':');
  const sgn = dir === 'asc' ? 1 : -1;
  const val = x => key === 'p' ? x.p : key === 'a' ? x.a : key === 'f' ? x.f : key === 'pd' ? sortPd(x) : key === 'y' ? x.y : key === 'dc' ? x.dc : x.d;
  rows.sort((a, b) => {
    const va = val(a), vb = val(b);
    const ea = va == null || va === '', eb = vb == null || vb === '';
    if (ea || eb) return ea - eb;  // 冇資料嘅永遠排最後
    return (typeof va === 'string' ? va.localeCompare(vb) : va - vb) * sgn || a.p - b.p;
  });
  $$('#tbl-list th[data-sort]').forEach(th => {
    const on = th.dataset.sort === key;
    th.setAttribute('aria-sort', on ? (dir === 'asc' ? 'ascending' : 'descending') : 'none');
    th.querySelector('.arr').textContent = on ? (dir === 'asc' ? ' ↑' : ' ↓') : '';
  });
  $('#res-count').textContent = merge ? `${rows.length} 個單位（${L.length} 條放盤）` : `${rows.length} 條放盤`;
  const ps = L.map(x => x.f).filter(Boolean).sort((a, b) => a - b);
  $('#res-note').textContent = ps.length ? `中位呎價 $${fmt(ps[Math.floor(ps.length / 2)])}` : '';
  const tb = $('#tbl-list tbody');
  tb.innerHTML = rows.slice(0, shown).map(x => {
    const e = EST[x.e] || {};
    const srcMap = new Map();
    x.all.forEach(y => { if (!srcMap.has(y.s)) srcMap.set(y.s, y); });
    const srcs = [...srcMap.values()].map(y => `<a class="src s-${y.s}" href="${esc(y.u)}" target="_blank" rel="noopener"><i></i>${SRC[y.s]}${x.all.length > 1 ? ' ' + wan(y.p) : ''}</a>`).join('');
    const tags = [...new Set(x.all.flatMap(y => y.t || []))].slice(0, 3).map(t => `<span class="chip">${esc(t)}</span>`).join('') + (x.ls ? '<span class="chip">連租約</span>' : '') + (x.o ? '<span class="chip">業主盤</span>' : '');
    const rooms = x.r == null ? '—' : x.r === 0 ? '開放式' : x.r + '房';
    const spread = x.all.length > 1 && x.all[x.all.length - 1].p !== x.p ? `<span class="sub2">叫價 ${wan(x.p)}–${wan(x.all[x.all.length - 1].p)}</span>` : '';
    return `<tr>
      <td class="c-est"><span class="est-name">${esc(e.name)}</span><span class="sub2">${esc(x.b) || '&nbsp;'}</span></td>
      <td class="num c-price"><span class="price">${wan(x.p)}</span>${spread}</td>
      <td class="num c-hide">${x.a ? fmt(x.a) + '呎' : '—'}</td>
      <td class="num c-hide">${x.f ? '$' + fmt(x.f) : '—'}${belowTag(x)}</td>
      <td class="num c-hide">${yieldTxt(x)}</td>
      <td class="c-hide">${rooms}</td>
      <td class="c-hide">${esc(x.fl) || '—'}</td>
      <td class="c-first">${firstCell(x.first, x.all.length > 1)}</td>
      <td class="c-meta">${x.a ? fmt(x.a) + '呎' : ''} · ${x.f ? '$' + fmt(x.f) + '/呎' : ''} · ${rooms} · ${esc(x.fl)}${x.y != null ? ' · 回報 ' + yieldTxt(x) : ''}${belowTag(x)}</td>
      <td class="c-src">${srcs}</td>
      <td class="c-tags"><div class="chips">${tags}</div></td>
      <td class="c-act"><button class="btn ghost sm" data-calc="${x.p}">計按揭</button></td>
    </tr>`;
  }).join('') || `<tr><td colspan="11" class="muted">冇符合條件嘅放盤，試下放寬篩選。</td></tr>`;
  $('#more').hidden = rows.length <= shown;
  $$('[data-calc]', tb).forEach(b => b.onclick = () => { $('#c-price').value = b.dataset.calc; location.hash = '#calc'; });
}

/* 首次出現日期 */
const sortPd = x => (x.first && x.first.pq !== 'base' && x.first.pd) || '';
function daysAgo(pd) {
  const now = new Date(DATA.listings_generated || Date.now());
  const d = new Date(pd.length === 10 ? pd + 'T12:00:00+08:00' : pd + ':00+08:00');
  const n = Math.max(0, Math.floor((now - d) / 864e5));
  if (n === 0) return '今日';
  if (n < 60) return n + '日前';
  if (n < 730) return Math.round(n / 30.4) + '個月前';
  return Math.floor(n / 365) + '年前';
}
function firstCell(y, multi) {
  if (!y || !y.pd) return '—';
  const [dd, tt] = y.pd.split('T');
  const [yr, mo, da] = dd.split('-').map(Number);
  const thisYr = new Date(DATA.listings_generated || Date.now()).getFullYear();
  const date = `${yr !== thisYr ? yr + '年' : ''}${mo}月${da}日`;
  let main, note;
  if (y.pq === 'exact') { main = `${date} ${tt}`; note = daysAgo(y.pd); }
    else if (y.pq === 'base') { main = `${date}前`; note = '開始追蹤前已放盤'; }
  else { main = `${date} ${tt || ''}`.trim(); note = '本平台首次收錄'; }
  const by = multi ? `最早：${SRC[y.s]}` : '';
  return `<span class="first-date">${main}</span><span class="sub2">${[note, by].filter(Boolean).join(' · ')}</span>`;
}

/* ---------- 屋苑比較 ---------- */
let estSort = 'u500';
function initEstates() {
  DATA.estates.forEach(e => { const m = DATA.listings.filter(x => x.e === e.id); e.u500 = m.filter(x => x.p <= 500).length; e.u400 = m.filter(x => x.p <= 400).length; });
  $$('#tbl-est th.sortable').forEach(th => th.onclick = () => { estSort = th.dataset.k; renderEstates(); });
  renderEstates();
}
function renderEstates() {
  const E = [...DATA.estates].sort((a, b) => estSort === 'med_psf' || estSort === 'med_price' ? (a[estSort] || 1e9) - (b[estSort] || 1e9) : (b[estSort] || 0) - (a[estSort] || 0));
  $$('#tbl-est th').forEach(th => th.classList.toggle('sorted', th.dataset.k === estSort));
  $('#tbl-est tbody').innerHTML = E.map(e => {
    const c = e.counts, L = e.links;
    const lk = (k, lab, n) => L[k] ? `<a class="src s-${k}" href="${esc(L[k])}" target="_blank" rel="noopener"><i></i>${lab} ${n ?? '—'}</a>` : '';
    const mtr = (e.mtr || []).map(a => `${esc(a.name)}${a.walking_minute ? ' ' + a.walking_minute + '分鐘' : ''}`).join('<br>') || '—';
    return `<tr class="est-row" data-id="${e.id}" tabindex="0">
      <td><span class="est-name">${esc(e.name)}</span><span class="sub2">${esc(e.area)}</span></td>
      <td>${esc(e.op_year) || '—'}</td>
      <td class="num">${esc((e.flats || '').replace('伙', '')) || '—'}</td>
      <td><span class="sub2" style="white-space:nowrap">${mtr}</span></td>
      <td class="num">${e.med_psf ? '$' + fmt(e.med_psf) : '—'}</td>
      <td class="num">${e.med_price ? wan(e.med_price) : '—'}</td>
      <td class="num"><a href="#listings?e=${e.id}" data-goto="${e.id}" data-max="400">${e.u400}</a></td>
      <td class="num"><a href="#listings?e=${e.id}" data-goto="${e.id}" data-max="500">${e.u500}</a></td>
      <td class="num">${e.rent_psf ? '$' + fmt(e.rent_psf, 1) : '—'}</td>
      <td class="num">${e.yield_ ? fmt(e.yield_, 2) + '%' : '—'}</td>
      <td style="min-width:260px">${lk('midland', '美聯', c.midland)}${lk('centanet', '中原', c.centanet)}${lk('ricacorp', '利嘉閣', c.ricacorp)}</td>
    </tr>`;
  }).join('');
  $$('.est-row').forEach(r => {
    r.onclick = ev => { if (ev.target.closest('a')) return; showEstate(r.dataset.id); };
    r.onkeydown = ev => { if (ev.key === 'Enter') showEstate(r.dataset.id); };
  });
  $$('[data-goto]').forEach(a => a.onclick = ev => { ev.preventDefault(); $('#f-estate').value = a.dataset.goto; $('#f-max').value = a.dataset.max; shown = 60; renderListings(); location.hash = '#listings'; });
}
function showEstate(id) {
  const e = EST[id];
  $$('.est-row').forEach(r => r.classList.toggle('sel', r.dataset.id === id));
  const st = e.stat || {};
  const sold = (e.sold || []).map(s => `<tr><td>${esc(s.bldg)} ${esc(s.floor)}樓</td><td class="num">${fmt(s.area)}呎</td><td class="num">${s.rooms ?? '—'}房</td><td class="num">${wan(s.price / 1e4)}</td><td class="num">${s.area ? '$' + fmt(s.price / s.area) : '—'}</td></tr>`).join('');
  const mine = DATA.listings.filter(x => x.e === id && x.p <= 500).length;
  $('#est-detail').innerHTML = `<article class="card detail">
    <div class="card-head"><h2>${esc(e.name)}</h2><div class="btn-row"><button class="btn ghost sm" data-goto2="400">睇 ≤400萬放盤（${e.u400}）</button><button class="btn sm" data-goto2="500">睇 ≤500萬放盤（${mine}）</button></div></div>
    <div class="detail-grid">
      <dl class="facts">
        <div><dt>地址</dt><dd>${esc(e.address) || '—'}</dd></div>
        <div><dt>發展商</dt><dd>${esc(e.developer) || '—'}</dd></div>
        <div><dt>座數／伙數</dt><dd>${esc(e.blocks) || '—'}／${esc(e.flats) || '—'}</dd></div>
        <div><dt>入伙</dt><dd>${esc(e.op_year) || '—'}</dd></div>
        <div><dt>小學校網</dt><dd>${e.school ? esc(e.school) + ' 校網' : '—'}</dd></div>
        <div><dt>就近商場</dt><dd>${(e.mall || []).map(a => esc(a.name) + (a.walking_minute ? `（步行 ${a.walking_minute} 分鐘）` : '')).join('') || '—'}</dd></div>
        <div><dt>美聯平均實用呎價</dt><dd>${e.mid_avg ? '$' + fmt(e.mid_avg) : '—'}</dd></div>
        <div><dt>近期成交呎價</dt><dd>${st.net_ft_price ? '$' + fmt(st.net_ft_price) + `（${st.tx_count} 宗${st.net_ft_price_chg != null ? '，' + (st.net_ft_price_chg > 0 ? '+' : '') + fmt(st.net_ft_price_chg, 1) + '%' : ''}）` : '—'}</dd></div>
      </dl>
      <div>
        <h3 class="muted" style="font-size:var(--text-xs);font-weight:500;margin-bottom:var(--space-2)">近期成交（美聯資料）</h3>
        <div class="table-wrap"><table class="tbl"><thead><tr><th>單位</th><th class="num">實用</th><th class="num">間隔</th><th class="num">成交價</th><th class="num">呎價</th></tr></thead><tbody>${sold || '<tr><td colspan="5" class="muted">暫無資料</td></tr>'}</tbody></table></div>
      </div>
    </div>
  </article>`;
  $$('[data-goto2]').forEach(b => b.onclick = () => { $('#f-estate').value = id; $('#f-max').value = b.dataset.goto2; shown = 60; renderListings(); location.hash = '#listings'; });
  $('#est-detail').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------- 按揭計算 ---------- */
function stampDuty(p) { // 第2標準（2026年2月26日起）
  const B = [[4e6, null], [4323780, x => 100 + .2 * (x - 4e6)], [4.5e6, x => x * .015], [4935480, x => 67500 + .1 * (x - 4.5e6)], [6e6, x => x * .0225],
    [6642860, x => 135000 + .1 * (x - 6e6)], [9e6, x => x * .03], [10080000, x => 270000 + .1 * (x - 9e6)], [2e7, x => x * .0375],
    [21739120, x => 750000 + .1 * (x - 2e7)], [1e8, x => x * .0425], [109574470, x => 4250000 + .3 * (x - 1e8)], [Infinity, x => x * .065]];
  if (p <= 4e6) return 100;
  for (const [cap, f] of B) if (f && p <= cap) return Math.ceil(f(p));
  return Math.ceil(p * .065);
}
const pmt = (P, r, n) => r === 0 ? P / n : P * (r / 12) / (1 - Math.pow(1 + r / 12, -n));
function initCalc() {
  $('#calc').addEventListener('input', ev => {
    if (ev.target.id === 'c-plan' && ev.target.value !== 'custom') $('#c-rate').value = ev.target.value;
    if (ev.target.id === 'c-rate') $('#c-plan').value = [...$('#c-plan').options].some(o => o.value === ev.target.value) ? ev.target.value : 'custom';
    calc();
  });
  calc();
}
function calc() {
  if (!$('#c-price')) return;
  const price = (+$('#c-price').value || 0) * 1e4;
  const type = ($('[name=c-type]:checked') || {}).value;
  let ltv = type === 'mip' ? .9 : type === 'mip8' ? .8 : .7;
  const notes = [];
  if (type !== 'std' && price > 1e7) { ltv = .7; notes.push('樓價超過 1,000萬，按保 9 成不適用，改以 7 成計。'); }
  const rate = (+$('#c-rate').value || 0) / 100, yrs = +$('#c-years').value, n = yrs * 12;
  const inc = +$('#c-income').value || 0, debt = +$('#c-debt').value || 0, agentPct = (+$('#c-agent').value || 0) / 100, rent = +$('#c-rent').value || 0;
  const loan = Math.round(price * ltv), down = price - loan, pay = pmt(loan, rate, n);
  const sd = stampDuty(price), agent = price * agentPct, legal = 10000;
  const cash = down + sd + agent + legal;
  const dsr = inc ? (pay + debt) / inc : null;
  $('#o-pay').textContent = money(pay);
  $('#o-pay-sub').textContent = `貸款 ${money(loan)}（${Math.round(ltv * 100)}%）· ${fmt(rate * 100, 2)}% · ${yrs} 年`;
  const box = (l, v, d = '') => `<div class="kpi"><span class="l">${l}</span><span class="v">${v}</span><span class="d">${d}</span></div>`;
  const interest = pay * n - loan;
  const items = [
    box('首期', money(down), `樓價 ${100 - Math.round(ltv * 100)}%`),
    box('印花稅', money(sd), price ? fmt(sd / price * 100, 2) + '% 樓價' : ''),
    box('代理佣金＋律師費', money(agent + legal), '律師費以約 $10,000 估算'),
    box('入市現金合計', money(cash), '未計按保保費及裝修'),
    box('DSR', dsr == null ? '—' : `<span class="${dsr <= .5 ? 'ok' : 'bad'}">${fmt(dsr * 100, 1)}%</span>`, dsr == null ? '輸入月入計算' : dsr <= .5 ? '符合 50% 上限' : '超出 50% 上限'),
    box('總利息', money(interest), `供滿 ${yrs} 年`)
  ];
  if (rent) {
    const gy = rent * 12 / price * 100;
    items.push(box('租金回報（毛）', fmt(gy, 2) + '%', `月租減供款 ${money(rent - pay)}`));
  }
  $('#o-grid').innerHTML = items.join('') + (notes.length ? `<p class="note" style="grid-column:1/-1">${notes.join(' ')}</p>` : '');
  const rows = [0, 1, 2].map(add => {
    const r = rate + add / 100, p = pmt(loan, r, n), need = (p + debt) / .5, d = inc ? (p + debt) / inc : null;
    return `<tr><td>${fmt(r * 100, 2)}%${add ? `（+${add} 厘）` : '（現時）'}</td><td class="num">${money(p)}</td><td class="num">${d == null ? '—' : `<span class="${d <= .5 ? 'ok' : 'bad'}">${fmt(d * 100, 1)}%</span>`}</td><td class="num">${money(need)}</td></tr>`;
  });
  $('#o-sens tbody').innerHTML = rows.join('');
  $('#o-sd-text').textContent = `樓價 ${wan(price / 1e4)} 嘅印花稅為 ${money(sd)}。` + (price > 4e6 && price <= 4323780 ? '剛過 400萬，屬 20% 邊際寬免區，每多 1 萬樓價多付 $2,000 稅。' : price <= 4e6 ? '400萬或以下只需 $100。' : '');
}
})();

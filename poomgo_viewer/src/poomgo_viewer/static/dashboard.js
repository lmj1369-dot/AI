const status = document.querySelector('#status');
const count = document.querySelector('#count');
const content = document.querySelector('#content');
const refresh = document.querySelector('#refresh');
const download = document.querySelector('#download');
const saveDatabase = document.querySelector('#save-database');
const saveResult = document.querySelector('#save-result');
const showLogs = document.querySelector('#show-logs');
const closeLogs = document.querySelector('#close-logs');
const logsDialog = document.querySelector('#logs-dialog');
const logsContent = document.querySelector('#logs-content');
const filters = document.querySelector('#filters');
const gridPager = document.querySelector('#grid-pager');
const previousPage = document.querySelector('#previous-page');
const nextPage = document.querySelector('#next-page');
const gridPageLabel = document.querySelector('#grid-page-label');
const pageJump = document.querySelector('#page-jump');
const pageNumber = document.querySelector('#page-number');
const autoSettingsForm = document.querySelector('#auto-settings-form');
const autoEnabled = document.querySelector('#auto-enabled');
const autoTimes = document.querySelector('#auto-times');
const autoSettingsStatus = document.querySelector('#auto-settings-status');
const currentKoreaTime = document.querySelector('#current-korea-time');
const nextRunCountdown = document.querySelector('#next-run-countdown');
const databaseSettingsForm = document.querySelector('#database-settings-form');
const dbHost = document.querySelector('#db-host');
const dbPort = document.querySelector('#db-port');
const dbName = document.querySelector('#db-name');
const dbUsername = document.querySelector('#db-username');
const dbPassword = document.querySelector('#db-password');
const databaseSettingsStatus = document.querySelector('#database-settings-status');
const testDatabase = document.querySelector('#test-database');
const progressPanel = document.querySelector('#progress-panel');
const progressLabel = document.querySelector('#progress-label');
const progressPercent = document.querySelector('#progress-percent');
const progressBar = document.querySelector('#progress-bar');
let gridRows = [];
let gridColumns = [];
let gridCell = () => '-';
let gridRawCell = () => '';
let gridPage = 1;
const gridPageSize = 100;
let autoScheduleTimes = '08:00,18:00';

function koreaParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, hourCycle: 'h23',
  }).formatToParts(date);
  return Object.fromEntries(parts.filter(({ type }) => type !== 'literal').map(({ type, value }) => [type, Number(value)]));
}

function nextKoreaRun(now, schedule) {
  const current = koreaParts(now);
  const currentSeconds = current.hour * 3600 + current.minute * 60 + current.second;
  const times = schedule.split(',').map((value) => value.trim()).filter(Boolean).map((value) => {
    const [hour, minute] = value.split(':').map(Number);
    return { value, hour, minute, seconds: hour * 3600 + minute * 60 };
  }).filter(({ hour, minute }) => Number.isInteger(hour) && Number.isInteger(minute) && hour >= 0 && hour < 24 && minute >= 0 && minute < 60).sort((a, b) => a.seconds - b.seconds);
  let selected = times.find(({ seconds }) => seconds > currentSeconds);
  let dayOffset = 0;
  if (!selected && times.length) {
    selected = times[0];
    dayOffset = 1;
  }
  if (!selected) return null;
  const target = new Date(Date.UTC(current.year, current.month - 1, current.day + dayOffset, selected.hour - 9, selected.minute, 0));
  return { target, label: selected.value };
}

function updateScheduleClock() {
  const now = new Date();
  currentKoreaTime.textContent = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', dateStyle: 'medium', timeStyle: 'medium' }).format(now);
  if (!autoEnabled.checked) {
    nextRunCountdown.textContent = '자동 저장 꺼짐';
    return;
  }
  const next = nextKoreaRun(now, autoScheduleTimes);
  if (!next) {
    nextRunCountdown.textContent = '실행 시각을 설정하세요';
    return;
  }
  const seconds = Math.max(0, Math.ceil((next.target - now) / 1000));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  nextRunCountdown.textContent = `${hours}시간 ${minutes}분 ${String(remainingSeconds).padStart(2, '0')}초 후 (${next.label})`;
}

function setProgress(page, totalPage, label = '조회 중') {
  const percent = totalPage > 0 ? Math.min(100, Math.round((page / totalPage) * 100)) : 0;
  progressPanel.hidden = false;
  progressLabel.textContent = `${label} · ${page} / ${totalPage} 페이지`;
  progressPercent.textContent = `${percent}%`;
  progressBar.style.width = `${percent}%`;
  progressBar.classList.toggle('is-active', percent < 100);
  progressBar.classList.remove('is-error');
}

function finishProgress(label, isError = false) {
  progressPanel.hidden = false;
  progressLabel.textContent = label;
  progressPercent.textContent = '100%';
  progressBar.style.width = '100%';
  progressBar.classList.remove('is-active');
  progressBar.classList.toggle('is-error', isError);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'
  })[character]);
}

function rowsFromPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.data)) return payload.data;
  if (Array.isArray(payload.result)) return payload.result;
  return [payload];
}

function text(value) {
  return value === null || value === undefined || value === '' ? '-' : escapeHtml(value);
}

function formatLogValue(value) {
  return value === null || value === undefined || value === '' ? '-' : escapeHtml(value);
}

function formatLogDate(value) {
  if (!value) return '-';
  try {
    const date = new Date(value);
    if (isNaN(date.getTime())) return escapeHtml(value);
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Seoul',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      hourCycle: 'h23',
    }).formatToParts(date);
    const p = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
  } catch {
    return escapeHtml(value);
  }
}

async function openLogs() {
  logsContent.innerHTML = '<div class="logs-loading">로그를 불러오는 중...</div>';
  logsDialog.showModal();
  try {
    const response = await fetch('/api/logs');
    if (!response.ok) throw new Error('로그를 불러오지 못했습니다.');
    const logs = await response.json();
    if (!logs.length) {
      logsContent.innerHTML = '<div class="empty">기록된 실행 로그가 없습니다.</div>';
      return;
    }
    logsContent.innerHTML = `<table class="logs-table"><thead><tr><th>실행</th><th>상태</th><th>시작</th><th>조회</th><th>신규 저장</th><th>중복</th><th>오류</th></tr></thead><tbody>${logs.map((log) => `<tr><td>${formatLogValue(log.run_type)}</td><td class="log-${formatLogValue(log.status)}">${formatLogValue(log.status)}</td><td>${formatLogDate(log.started_at)}</td><td>${formatLogValue(log.fetched_count)}</td><td>${formatLogValue(log.saved_count)}</td><td>${formatLogValue(log.skipped_count)}</td><td>${formatLogValue(log.error_message)}</td></tr>`).join('')}</tbody></table>`;
  } catch (error) {
    logsContent.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
  }
}

function today() {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function setDefaultDates() {
  const date = today();
  filters.elements.closedAtGte.value = date;
  filters.elements.closedAtLte.value = date;
}

async function loadAutoSettings() {
  try {
    const response = await fetch('/api/settings/auto');
    const settings = await response.json();
    autoEnabled.checked = settings.enabled;
    autoTimes.value = settings.times;
    autoScheduleTimes = settings.times;
    updateScheduleClock();
  } catch {
    autoSettingsStatus.textContent = '자동 저장 설정을 불러오지 못했습니다.';
  }
}

async function saveAutoSettings(event) {
  event.preventDefault();
  autoSettingsStatus.textContent = '저장 중...';
  try {
    const response = await fetch('/api/settings/auto', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: autoEnabled.checked, times: autoTimes.value }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '설정 저장에 실패했습니다.');
    autoTimes.value = result.times;
    autoScheduleTimes = result.times;
    updateScheduleClock();
    autoSettingsStatus.textContent = '자동 저장 설정을 저장했습니다.';
  } catch (error) {
    autoSettingsStatus.textContent = error.message;
  }
}

async function loadDatabaseSettings() {
  try {
    const response = await fetch('/api/settings/database');
    const settings = await response.json();
    dbHost.value = settings.host || '';
    dbPort.value = settings.port || 3306;
    dbName.value = settings.database || '';
    dbUsername.value = settings.username || '';
    dbPassword.placeholder = settings.has_password ? '기존 값 유지' : '필수 입력';
  } catch {
    databaseSettingsStatus.textContent = 'DB 설정을 불러오지 못했습니다.';
  }
}

async function saveDatabaseSettings(event) {
  event.preventDefault();
  databaseSettingsStatus.textContent = '저장 중...';
  try {
    const response = await fetch('/api/settings/database', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host: dbHost.value,
        port: Number(dbPort.value),
        database: dbName.value,
        username: dbUsername.value,
        password: dbPassword.value,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'DB 설정 저장에 실패했습니다.');
    dbPassword.value = '';
    dbPassword.placeholder = '기존 값 유지';
    databaseSettingsStatus.textContent = 'DB 접속 설정을 저장했습니다.';
  } catch (error) {
    databaseSettingsStatus.textContent = error.message;
  }
}

async function testDatabaseConnection() {
  testDatabase.disabled = true;
  databaseSettingsStatus.className = 'database-settings-status is-saving';
  databaseSettingsStatus.textContent = '접속 테스트 중...';
  try {
    const response = await fetch('/api/settings/database/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host: dbHost.value,
        port: Number(dbPort.value),
        database: dbName.value,
        username: dbUsername.value,
        password: dbPassword.value,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '접속 테스트에 실패했습니다.');
    databaseSettingsStatus.className = 'database-settings-status is-success';
    databaseSettingsStatus.textContent = result.message;
  } catch (error) {
    databaseSettingsStatus.className = 'database-settings-status is-error';
    databaseSettingsStatus.textContent = error.message;
  } finally {
    testDatabase.disabled = false;
  }
}

function koreaMidnightAsUtc(dateValue) {
  const [year, month, day] = dateValue.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day, -9, 0, 0)).toISOString();
}

function locationText(location) {
  if (!location) return '-';
  return `${text(location.countryCode)} / ${text(location.administrativeArea)}`;
}

function render(payload) {
  const invoices = rowsFromPayload(payload).filter((row) => row && typeof row === 'object');
  if (!invoices.length) {
    content.innerHTML = '<div class="empty">표시할 데이터가 없습니다.</div>';
    return;
  }
  const rows = invoices.flatMap((invoice) => {
    const items = Array.isArray(invoice.items) && invoice.items.length ? invoice.items : [{}];
    return items.map((item) => ({ invoice, item }));
  });
  const columns = [
    ['invoiceId', '송장 ID'],
    ['invoiceSerial', '송장번호'],
    ['brandName', '브랜드'],
    ['trackingNumber', '운송장번호'],
    ['recipient', '수취인'],
    ['itemName', '상품명'],
    ['quantity', '수량(개)'],
    ['itemCode', '상품코드'],
    ['itemNumber', '관리번호'],
    ['itemOption', '옵션'],
    ['isGift', '사은품'],
    ['lot', '로트'],
    ['expiry', '소비기한'],
    ['dimensions', '규격/중량'],
    ['order', '주문'],
    ['createdAt', '생성일시'],
    ['closedAt', '마감일시'],
  ];
  const rawCell = ({ invoice, item }, key) => {
    if (key === 'recipient') return invoice[key]?.name;
    if (key === 'order') return invoice[key] ? `${invoice[key].channelName || '-'} / ${invoice[key].channelOrderId || '-'}` : '-';
    if (key === 'itemName') return item.name;
    if (key === 'itemCode') return item.code;
    if (key === 'itemNumber') return item.itemNumber;
    if (key === 'itemOption') return item.option;
    if (key === 'quantity') return item.quantity ?? item.qty ?? item.count ?? item.itemQuantity;
    if (key === 'isGift') return item.isGift === true ? '예' : item.isGift === false ? '아니오' : '-';
    if (key === 'lot') return item.lot;
    if (key === 'expiry') return item.expiry;
    if (key === 'dimensions') return item.width === undefined ? '-' : `${item.width} × ${item.depth} × ${item.height} / ${item.weight}g`;
    return invoice[key];
  };
  gridRows = rows;
  gridColumns = columns;
  gridRawCell = (row, key) => rawCell(row, key);
  gridCell = (row, key) => text(gridRawCell(row, key));
  renderGrid();
  count.textContent = `${rows.length}행 · 송장 ${invoices.length}건${payload.total ? ` / 전체 ${payload.total}건` : ''}`;
}

function renderGrid() {
  const totalPages = Math.max(1, Math.ceil(gridRows.length / gridPageSize));
  gridPage = Math.min(gridPage, totalPages);
  const start = (gridPage - 1) * gridPageSize;
  const visibleRows = gridRows.slice(start, start + gridPageSize);
  content.innerHTML = `<table><thead><tr>${gridColumns.map(([, label]) => `<th>${label}</th>`).join('')}</tr></thead><tbody>${visibleRows.map((row) => `<tr>${gridColumns.map(([key]) => `<td>${gridCell(row, key)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  gridPager.hidden = gridRows.length <= gridPageSize;
  pageNumber.value = gridPage;
  pageNumber.max = totalPages;
  gridPageLabel.textContent = `${gridPage} / ${totalPages} 페이지 · ${start + 1}-${Math.min(start + gridPageSize, gridRows.length)}행`;
  previousPage.disabled = gridPage === 1;
  nextPage.disabled = gridPage === totalPages;
}

function csvValue(value) {
  return `"${String(value ?? '').replace(/"/g, '""')}"`;
}

function downloadCsv() {
  if (!gridRows.length) return;
  const header = gridColumns.map(([, label]) => csvValue(label));
  const lines = [header, ...gridRows.map((row) => gridColumns.map(([key]) => csvValue(gridRawCell(row, key))))];
  const blob = new Blob([`\uFEFF${lines.map((line) => line.join(',')).join('\r\n')}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `poomgo-invoices-${today()}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function load(event) {
  event?.preventDefault();
  if (!filters.elements.closedAtGte.value || !filters.elements.closedAtLte.value) {
    status.textContent = '기간 입력 필요';
    content.innerHTML = '<div class="error">마감 시작일과 마감 종료일은 필수 입력입니다.</div>';
    count.textContent = '';
    filters.elements.closedAtGte.focus();
    return;
  }
  refresh.disabled = true;
  download.disabled = true;
  saveDatabase.disabled = true;
  saveResult.textContent = '';
  saveResult.className = 'save-result';
  setProgress(0, 1, '품고 API 연결 중');
  status.textContent = '품고 API에 연결하는 중...';
  try {
    const form = new FormData(filters);
    const params = new URLSearchParams();
    for (const [key, value] of form.entries()) {
      if (!value) continue;
      if (key === 'closedAtGte') {
        params.set(key, koreaMidnightAsUtc(value));
      } else if (key === 'closedAtLte') {
        params.set(key, koreaMidnightAsUtc(value));
      } else {
        params.set(key, value);
      }
    }
    const response = await fetch(`/api/invoices/stream?${params}`);
    if (!response.ok) throw new Error('API 호출에 실패했습니다.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let payload = { data: [], total: 0 };
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const events = buffer.split('\n');
      buffer = events.pop();
      for (const event of events.filter(Boolean)) {
        const page = JSON.parse(event);
        payload = { data: [...payload.data, ...page.data], total: page.total };
        render(payload);
        setProgress(page.page, page.totalPage);
        status.textContent = `조회 중 · ${page.page} / ${page.totalPage} 페이지`;
      }
      if (done) break;
    }
    download.disabled = false;
    saveDatabase.disabled = false;
    finishProgress('조회 완료');
    status.textContent = `조회 완료 · ${new Date().toLocaleTimeString('ko-KR')}`;
  } catch (error) {
    download.disabled = true;
    saveDatabase.disabled = true;
    gridPager.hidden = true;
    content.innerHTML = `<div class="error">${escapeHtml(error.message)}</div>`;
    count.textContent = '';
    progressPanel.hidden = true;
    status.textContent = '조회 실패';
  } finally {
    refresh.disabled = false;
  }
}

async function saveCurrentResults() {
  if (!gridRows.length) return;
  saveDatabase.disabled = true;
  saveResult.className = 'save-result is-saving';
  saveResult.textContent = '저장 중...';
  setProgress(0, 1, 'DB 저장 중');
  status.textContent = 'DB에 저장하는 중...';
  const invoices = [...new Map(gridRows.map(({ invoice }) => [String(invoice.invoiceId), invoice])).values()];
  try {
    const response = await fetch('/api/invoices/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows: invoices }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'DB 저장에 실패했습니다.');
    const saved = result.saved || 0;
    const skipped = result.skipped || 0;
    saveResult.className = 'save-result is-success';
    saveResult.textContent = `저장 완료 · 신규 ${saved} · 중복 ${skipped}`;
    finishProgress('DB 저장 완료');
    status.textContent = `DB 저장 완료 · 신규 ${saved}건 · 중복 ${skipped}건`;
  } catch (error) {
    saveResult.className = 'save-result is-error';
    saveResult.textContent = `저장 실패 · ${error.message}`;
    finishProgress('DB 저장 실패', true);
    status.textContent = `DB 저장 실패: ${error.message}`;
  } finally {
    saveDatabase.disabled = false;
  }
}

refresh.addEventListener('click', load);
saveDatabase.addEventListener('click', saveCurrentResults);
download.addEventListener('click', downloadCsv);
filters.addEventListener('submit', load);
previousPage.addEventListener('click', () => {
  if (gridPage > 1) {
    gridPage -= 1;
    renderGrid();
  }
});
nextPage.addEventListener('click', () => {
  if (gridPage < Math.ceil(gridRows.length / gridPageSize)) {
    gridPage += 1;
    renderGrid();
  }
});
pageJump.addEventListener('submit', (event) => {
  event.preventDefault();
  const totalPages = Math.max(1, Math.ceil(gridRows.length / gridPageSize));
  const requestedPage = Number.parseInt(pageNumber.value, 10);
  gridPage = Number.isFinite(requestedPage) ? Math.min(Math.max(requestedPage, 1), totalPages) : 1;
  renderGrid();
});
autoSettingsForm.addEventListener('submit', saveAutoSettings);
databaseSettingsForm.addEventListener('submit', saveDatabaseSettings);
showLogs.addEventListener('click', openLogs);
closeLogs.addEventListener('click', () => logsDialog.close());
testDatabase.addEventListener('click', testDatabaseConnection);
setDefaultDates();
loadAutoSettings();
loadDatabaseSettings();
updateScheduleClock();
setInterval(updateScheduleClock, 1000);

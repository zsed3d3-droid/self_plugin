// Playwright 페이지에 붙이는 안전 장치: 쓰기 요청 차단, 개인정보 가림, 콘솔 오류 수집.
// 로그인된 전용 Chrome에 연결해 쓴다:
//   const { chromium } = await import(process.env.PLAYWRIGHT_CORE || 'playwright-core');
//   const browser = await chromium.connectOverCDP('http://127.0.0.1:9333');
//   const page = await browser.contexts()[0].newPage();   // 사용자가 로그인한 컨텍스트
//   const blocked = await guardWrites(page, { allow: [/^POST \/api\/demo\/switch\//] });
//   ... 작업 ...
//   await page.close(); await browser.close();             // 연결만 끊는다. Chrome은 stop으로 닫는다.

const READ_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

// 읽기 요청이거나 허용 목록("METHOD /path" 정규식)에 맞으면 통과시킨다.
export function isAllowed(method, path, allow = []) {
  const upper = String(method).toUpperCase();
  if (READ_METHODS.has(upper)) return true;
  return allow.some(pattern => pattern.test(`${upper} ${path}`));
}

// 허용하지 않은 쓰기 요청을 막고, 막은 요청 목록(배열)을 돌려준다. 결과 보고에 그대로 쓴다.
export async function guardWrites(page, { allow = [] } = {}) {
  const blocked = [];
  await page.route('**/*', route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (isAllowed(request.method(), path, allow)) return route.continue();
    blocked.push(`${request.method()} ${path}`);
    return route.abort('blockedbyclient');
  });
  return blocked;
}

// 화면 글자 중 이메일·사번(9자리 숫자)·지정한 이름을 흐리게 한다. 이름은 글자 전체가 같을 때만 가린다.
export async function maskPersonalData(page, { names = [], keep = [] } = {}) {
  return page.evaluate(({ names, keep }) => {
    const exact = new Set(names.filter(name => !keep.includes(name)));
    const hits = new Set();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const text = walker.currentNode.nodeValue.trim();
      if (!text) continue;
      if (/[\w.+-]+@[\w-]+\.[\w.]+/.test(text) || /(^|\D)\d{9}(\D|$)/.test(text) ||
          [...exact].some(name => text === name || text.split(/[\s,·/()]+/).includes(name))) {
        hits.add(walker.currentNode.parentElement);
      }
    }
    for (const input of document.querySelectorAll('input, textarea')) {
      if (exact.has((input.value || '').trim())) hits.add(input);
    }
    for (const element of hits) element.style.filter = 'blur(5px)';
    return hits.size;
  }, { names, keep });
}

// 페이지 오류·콘솔 오류·실패한 요청을 모은다. guardWrites가 막은 요청과 취소된 이동은 빼고 모은다.
export function collectErrors(page) {
  const errors = [];
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error' && !message.text().includes('ERR_BLOCKED_BY_CLIENT')) errors.push(`console: ${message.text()}`);
  });
  page.on('requestfailed', request => {
    const reason = request.failure()?.errorText || '';
    if (!/ERR_ABORTED|ERR_BLOCKED_BY_CLIENT/.test(reason)) errors.push(`requestfailed: ${request.method()} ${request.url()} ${reason}`);
  });
  return errors;
}

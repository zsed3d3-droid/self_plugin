// CDP Browser.close로 원격 디버깅 Chrome을 닫는다. Node 22+ 내장 WebSocket만 사용한다.
// 사용: node cdp-close.mjs [port]
const port = process.argv[2] || process.env.LBS_PORT || '9333';

if (typeof WebSocket === 'undefined') {
  console.error('이 Node에는 내장 WebSocket이 없습니다(Node 22 이상 필요). 브라우저 종료는 프로세스 종료로 대신합니다.');
  process.exit(1);
}

const { webSocketDebuggerUrl } = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
const socket = new WebSocket(webSocketDebuggerUrl);
const done = code => { try { socket.close(); } catch {} process.exit(code); };
socket.onopen = () => socket.send(JSON.stringify({ id: 1, method: 'Browser.close' }));
socket.onmessage = () => done(0);
socket.onclose = () => done(0);
socket.onerror = () => done(1);
setTimeout(() => done(0), 5000);

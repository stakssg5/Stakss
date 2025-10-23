// Require auth token; redirect to login if missing/invalid
(async () => {
  const token = (() => { try { return localStorage.getItem('auth_token'); } catch { return null; }})();
  if (!token) {
    location.href = `/login.html?next=${encodeURIComponent(location.pathname || '/')}`;
    return;
  }
  try {
    const resp = await fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` }});
    if (!resp.ok) throw new Error('unauthorized');
  } catch {
    location.href = `/login.html?next=${encodeURIComponent(location.pathname || '/')}`;
    return;
  }
})();

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const chainButtons = document.querySelectorAll('.chip');
let currentChain = 'btc';
chainButtons.forEach(btn => btn.addEventListener('click', () => {
  chainButtons.forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentChain = btn.dataset.chain;
}));

const addressInput = document.getElementById('address');
const startBtn = document.getElementById('start');
const result = document.getElementById('result');
const amountEl = document.getElementById('amount');
const usdEl = document.getElementById('usd');
const addrEl = document.getElementById('addr');
const copyBtn = document.getElementById('copy');

copyBtn.addEventListener('click', async () => {
  const text = addrEl.textContent.replace(/\u2026/g, '');
  try { await navigator.clipboard.writeText(text); } catch {}
});

startBtn.addEventListener('click', async () => {
  const address = addressInput.value.trim();
  if (!address) { alert('Enter a wallet address'); return; }
  startBtn.disabled = true;
  startBtn.textContent = 'Checking…';
  try {
    const resp = await fetch(`/api/check?address=${encodeURIComponent(address)}&chain=${encodeURIComponent(currentChain)}`);
    if (!resp.ok) throw new Error('Request failed');
    const data = await resp.json();
    const symbol = data.symbol || currentChain.toUpperCase();
    amountEl.textContent = `${Number(data.balance).toFixed(8)} ${symbol}`;
    usdEl.textContent = `$${Number(data.balance_usd || 0).toFixed(2)}`;
    addrEl.textContent = `${address.slice(0, 6)}…${address.slice(-4)}`;
    result.hidden = false;
  } catch (e) {
    alert('Unable to check this address');
  } finally {
    startBtn.disabled = false;
    startBtn.textContent = 'Start search';
  }
});

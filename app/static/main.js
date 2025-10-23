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

// ---- CC generator ----
const ccBtn = document.getElementById('cc-generate');
const ccOut = document.getElementById('cc-output');
const ccNetwork = document.getElementById('cc-network');
const ccBin = document.getElementById('cc-bin');
const ccLen = document.getElementById('cc-length');
const ccQty = document.getElementById('cc-qty');
const ccZip = document.getElementById('cc-zip');
const ccZip4 = document.getElementById('cc-zip4');

if (ccBtn) {
  ccBtn.addEventListener('click', async () => {
    ccBtn.disabled = true;
    ccBtn.textContent = 'Generating…';
    ccOut.textContent = '';
    try {
      const payload = {
        network: ccNetwork.value || null,
        bin: ccBin.value || null,
        length: ccLen.value ? Number(ccLen.value) : null,
        quantity: ccQty.value ? Number(ccQty.value) : 5,
        include_zip: ccZip ? !!ccZip.checked : false,
        zip_plus4: ccZip4 ? !!ccZip4.checked : false,
      };
      const resp = await fetch('/api/cc/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error('Request failed');
      const data = await resp.json();
      const lines = (data.cards || []).join('\n');
      ccOut.textContent = lines;
    } catch (e) {
      ccOut.textContent = 'Error generating numbers';
    } finally {
      ccBtn.disabled = false;
      ccBtn.textContent = 'Generate CC numbers';
    }
  });
}

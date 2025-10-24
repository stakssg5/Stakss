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

// ---- Test card generator ----
const cardBrandSel = document.getElementById('cardBrand');
const cardCountInput = document.getElementById('cardCount');
const genCardsBtn = document.getElementById('genCards');
const cardListEl = document.getElementById('cardList');

async function loadBrands() {
  try {
    const resp = await fetch('/api/cards/brands');
    if (!resp.ok) return;
    const data = await resp.json();
    (data.brands || []).forEach(({ key, label }) => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = label;
      cardBrandSel.appendChild(opt);
    });
  } catch {}
}

function formatCardLine(c) {
  const mm = String(c.expiry_month).padStart(2, '0');
  const yy = String(c.expiry_year).slice(-2);
  const zip = c.zip ? `  ZIP ${c.zip}` : '';
  return `${c.brand}  ${c.number}  ${mm}/${yy}  CVV ${c.cvv}${zip}`;
}

async function generateCards() {
  const count = Math.max(1, Math.min(20, Number(cardCountInput.value) || 1));
  const brand = cardBrandSel.value || '';
  genCardsBtn.disabled = true;
  genCardsBtn.textContent = 'Generating…';
  try {
    const qs = new URLSearchParams({ count: String(count) });
    if (brand) qs.set('brand', brand);
    const resp = await fetch(`/api/cards?${qs.toString()}`);
    if (!resp.ok) throw new Error('Request failed');
    const data = await resp.json();
    const cards = data.cards || [];
    cardListEl.innerHTML = '';
    cards.forEach(c => {
      const row = document.createElement('div');
      row.className = 'card-row';
      const span = document.createElement('div');
      span.className = 'card-line';
      span.textContent = formatCardLine(c);
      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Copy';
      btn.addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(span.textContent); } catch {}
      });
      row.appendChild(span);
      row.appendChild(btn);
      cardListEl.appendChild(row);
    });
  } catch (e) {
    alert('Unable to generate cards');
  } finally {
    genCardsBtn.disabled = false;
    genCardsBtn.textContent = 'Generate';
  }
}

genCardsBtn.addEventListener('click', generateCards);
loadBrands();

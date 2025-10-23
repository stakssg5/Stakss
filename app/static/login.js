(function(){
  const email = document.getElementById('email');
  const cvv = document.getElementById('cvv');
  const form = document.getElementById('login-form');
  const errorBox = document.getElementById('error');
  const shutdown = document.getElementById('shutdown');

  function setError(msg){
    errorBox.textContent = msg;
    errorBox.hidden = !msg;
  }

  function storeToken(token){
    try{ localStorage.setItem('auth_token', token); }catch{}
  }

  function getRedirect(){
    const params = new URLSearchParams(location.search);
    return params.get('next') || '/';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const emailVal = email.value.trim();
    const cvvVal = cvv.value.trim();
    if (!emailVal || !cvvVal){ setError('Enter email and PIN'); return; }
    setError('');
    try{
      const resp = await fetch('/api/auth/login',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ email: emailVal, cvv: cvvVal })
      });
      if(!resp.ok){ throw new Error('Invalid credentials'); }
      const data = await resp.json();
      if (!data.token){ throw new Error('No token'); }
      storeToken(data.token);
      location.href = getRedirect();
    }catch(err){
      setError('Access denied. Check credentials.');
    }
  });

  shutdown.addEventListener('click', () => {
    window.close();
  });
})();

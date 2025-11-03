(() => {
  const printers = window.PRINTERS || [];

  const modoSelect    = document.getElementById('modo');
  const printerSelect = document.getElementById('printer_ip');
  const copiesInput   = document.getElementById('copies');

  function populatePrinters(mode, selectedIp) {
    printerSelect.innerHTML = '';
    const avail = printers.filter(p => p.funcao.includes(mode));
    if (avail.length) {
      avail.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.ip;
        opt.textContent = `${p.nome || p.ip} (${p.funcao.join(', ')})`;
        if (p.ip === selectedIp) opt.selected = true;
        printerSelect.append(opt);
      });
      printerSelect.disabled = false;
    } else {
      const opt = document.createElement('option');
      opt.disabled = true;
      opt.textContent = 'Nenhuma impressora disponível';
      printerSelect.append(opt);
      printerSelect.disabled = true;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    // --- Sempre começa com 1 cópia ---
    copiesInput.value = 1;
    localStorage.removeItem('copies'); // limpa o cache antigo

    const savedModo = localStorage.getItem('modo') || modoSelect.value;
    modoSelect.value = savedModo;
    const savedIp = localStorage.getItem('printer_ip');
    populatePrinters(savedModo, savedIp);
  });

  modoSelect.addEventListener('change', e => {
    const m = e.target.value;
    localStorage.setItem('modo', m);
    const lastIp = localStorage.getItem('printer_ip');
    populatePrinters(m, lastIp);
  });

  printerSelect.addEventListener('change', e => {
    localStorage.setItem('printer_ip', e.target.value);
  });

  copiesInput.addEventListener('change', e => {
    let v = parseInt(e.target.value, 10);
    if (isNaN(v) || v < 1) v = 1;
    if (v > 100) v = 100;
    e.target.value = v;
    // ❌ Removido o localStorage.setItem('copies', v);
  });
})();
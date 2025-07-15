(() => {
  const printers = window.PRINTERS || [];

  const modoRadios    = document.querySelectorAll('input[name="modo"]');
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
    // Restaura modo e printer_ip
    const savedModo = localStorage.getItem('modo')
                    || document.querySelector('input[name="modo"]:checked').value;
    const savedIp   = localStorage.getItem('printer_ip');

    modoRadios.forEach(r => { if (r.value === savedModo) r.checked = true; });
    populatePrinters(savedModo, savedIp);

    // Restaura copies
    const savedCopies = parseInt(localStorage.getItem('copies'), 10);
    if (!isNaN(savedCopies)) {
      copiesInput.value = savedCopies;
    } else {
      copiesInput.value = 1;
    }
  });

  // Sempre que o usuário trocar de modo…
  modoRadios.forEach(radio => {
    radio.addEventListener('change', e => {
      const m = e.target.value;
      localStorage.setItem('modo', m);
      const lastIp = localStorage.getItem('printer_ip');
      populatePrinters(m, lastIp);
    });
  });

  // Sempre que trocar impressora…
  printerSelect.addEventListener('change', e => {
    localStorage.setItem('printer_ip', e.target.value);
  });

  // salvar cópias no localStorage
  copiesInput.addEventListener('change', e => {
    let v = parseInt(e.target.value, 10);
    if (isNaN(v) || v < 1) v = 1;
    if (v > 100) v = 100;
    e.target.value = v;
    localStorage.setItem('copies', v);
  });

  document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", () => {
      const codigo = document.getElementById("codigo");
      if (codigo) codigo.value = "";
    });
  }

  // Se a página for exibida após um redirect (PRG), limpa o campo código
  window.addEventListener("pageshow", function () {
    const codigo = document.getElementById("codigo");
    if (codigo) codigo.value = "";
  });
});

})();
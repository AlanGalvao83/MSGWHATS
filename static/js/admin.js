let mensalistasData = [];
let configuracoesData = {};

document.addEventListener('DOMContentLoaded', () => {
  loadData();
  loadConfiguracoes();
});

async function loadData() {
  try {
    const res = await fetch('/api/mensalistas');
    mensalistasData = await res.json();
    renderStats();
    renderMensalistasTable();
    renderVeiculosTable();
    updateLotePreview();
  } catch (err) {
    console.error("Erro ao carregar mensalistas:", err);
  }
}

async function loadConfiguracoes() {
  try {
    const res = await fetch('/api/configuracoes');
    configuracoesData = await res.json();
    document.getElementById('config-nome-estacionamento').value = configuracoesData.nome_estacionamento || '';
    document.getElementById('config-dominio-publico').value = configuracoesData.dominio_publico || 'https://msgwhats.vercel.app';
    
    let templateText = configuracoesData.mensagem_template || '';
    templateText = templateText.replace(/\\n/g, '\n');
    document.getElementById('config-mensagem-template').value = templateText;
    
    atualizarPréviaMensagem();
  } catch (err) {
    console.error("Erro ao carregar configurações:", err);
  }
}

function renderStats() {
  const total = mensalistasData.length;
  const enviados = mensalistasData.filter(m => m.status_envio === 'Enviado').length;
  const atualizados = mensalistasData.filter(m => m.status_cadastro === 'Atualizado').length;
  
  let totalVeiculos = 0;
  mensalistasData.forEach(m => {
    totalVeiculos += (m.veiculos ? m.veiculos.length : 0);
  });

  document.getElementById('stat-total').innerText = total;
  document.getElementById('stat-enviados').innerText = enviados;
  document.getElementById('stat-atualizados').innerText = atualizados;
  document.getElementById('stat-veiculos').innerText = totalVeiculos;
}

function switchTab(tabId, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  
  document.getElementById(tabId).classList.add('active');
  btn.classList.add('active');
}

function renderMensalistasTable() {
  const tbody = document.getElementById('table-mensalistas-body');
  const searchInput = document.getElementById('search-input');
  const search = searchInput && searchInput.value ? searchInput.value.toLowerCase().trim() : '';
  
  const filtered = mensalistasData.filter(m => {
    const cartaoStr = m.numero_cartao || '';
    const lojaStr = m.nome_loja || '';
    const vinculoStr = m.tipo_vinculo || '';
    const cpfStr = m.cpf || '';
    const emailStr = m.email || '';
    return m.nome.toLowerCase().includes(search) || 
           m.telefone.includes(search) || 
           cpfStr.includes(search) ||
           emailStr.toLowerCase().includes(search) ||
           cartaoStr.includes(search) ||
           lojaStr.toLowerCase().includes(search) ||
           vinculoStr.toLowerCase().includes(search) ||
           m.status_envio.toLowerCase().includes(search) ||
           m.status_cadastro.toLowerCase().includes(search);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
          Nenhum mensalista encontrado.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map(m => {
    const nomeLimpo = m.nome ? m.nome.split(';')[0].trim() : '';
    const envioBadge = m.status_envio === 'Enviado' 
      ? `<span class="badge badge-green"><i class="fa-solid fa-check"></i> Enviado</span>`
      : `<span class="badge badge-amber"><i class="fa-solid fa-clock"></i> Pendente</span>`;
      
    const cadastroBadge = m.status_cadastro === 'Atualizado'
      ? `<span class="badge badge-green"><i class="fa-solid fa-circle-check"></i> Atualizado</span>`
      : `<span class="badge badge-amber"><i class="fa-solid fa-circle-notch"></i> Pendente</span>`;

    const qtdVeiculos = m.veiculos ? m.veiculos.length : 0;
    const veiculosTexto = qtdVeiculos > 0 
      ? `<strong style="color: #34d399;">${qtdVeiculos} veículo(s)</strong>` 
      : `<span style="color: var(--text-muted);">-</span>`;

    const cartaoDisplay = m.numero_cartao 
      ? `<code style="font-size: 0.95rem; font-weight: bold; color: #818cf8; letter-spacing: 1px;">${m.numero_cartao}</code>` 
      : `<span style="color: var(--text-muted); font-size: 0.8rem;">Pendente</span>`;

    const isExterno = m.tipo_vinculo === 'Mensalista Externo';
    const vinculoDisplay = isExterno 
      ? `<span class="badge badge-amber"><i class="fa-solid fa-car"></i> Externo</span>` 
      : `<div style="font-weight: 600; color: #e2e8f0; font-size: 0.85rem;">🏬 ${m.nome_loja || 'Lojista'}</div>`;

    const cpfEmailDisplay = `
      <div style="font-weight: 600; font-family: monospace; font-size: 0.82rem; color: #cbd5e1;">${m.cpf || '-'}</div>
      <small style="color: var(--text-muted); font-size: 0.73rem;">${m.email || '-'}</small>
    `;

    return `
      <tr>
        <td>
          <div style="font-weight: 600; font-size: 0.88rem;">${nomeLimpo}</div>
          <small style="color: var(--text-muted); font-size: 0.72rem;">ID: #${m.id}</small>
        </td>
        <td>${cpfEmailDisplay}</td>
        <td>${vinculoDisplay}</td>
        <td>${cartaoDisplay}</td>
        <td><code style="font-size: 0.82rem;">${formatPhone(m.telefone)}</code></td>
        <td>${envioBadge}</td>
        <td>${cadastroBadge}</td>
        <td style="text-align: center;">${veiculosTexto}</td>
        <td>
          <div class="table-actions">
            <a href="${m.whatsapp_url}" target="_blank" onclick="marcarComoEnviado(${m.id})" class="btn btn-success btn-sm" title="Enviar WhatsApp Web">
              <i class="fa-brands fa-whatsapp"></i> WhatsApp
            </a>
            <button onclick="copiarLink('${m.link_atualizacao}')" class="btn btn-secondary btn-sm" title="Copiar Link Individual">
              <i class="fa-solid fa-copy"></i> Link
            </button>
            <button onclick="deletarMensalista(${m.id})" class="btn btn-danger btn-sm" title="Excluir">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderVeiculosTable() {
  const tbody = document.getElementById('table-veiculos-body');
  let rows = [];

  mensalistasData.forEach(m => {
    if (m.veiculos && m.veiculos.length > 0) {
      m.veiculos.forEach(v => {
        rows.push({
          mensalista: m.nome,
          cpf: m.cpf || '-',
          loja: m.nome_loja || m.tipo_vinculo || 'Lojista',
          cartao: m.numero_cartao || 'Pendente',
          telefone: m.telefone,
          modelo: v.modelo,
          ano: v.ano,
          cor: v.cor,
          placa: v.placa,
          data: m.data_atualizacao || 'Sim'
        });
      });
    }
  });

  if (rows.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">
          Nenhum veículo cadastrado pelos mensalistas até o momento.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><strong>${r.mensalista}</strong></td>
      <td><code style="color: #94a3b8; font-size: 0.85rem;">${r.cpf}</code></td>
      <td><span style="color: #cbd5e1; font-weight: 600;">${r.loja}</span></td>
      <td><code style="color: #818cf8; font-weight: bold;">${r.cartao}</code></td>
      <td><code>${formatPhone(r.telefone)}</code></td>
      <td>${r.modelo}</td>
      <td>${r.ano}</td>
      <td>${r.cor}</td>
      <td><span class="plate-preview">${formatPlaca(r.placa)}</span></td>
      <td><small style="color: var(--text-muted);">${r.data}</small></td>
    </tr>
  `).join('');
}

function formatPhone(phone) {
  if (!phone) return '';
  if (phone.length === 13) {
    return `+${phone.slice(0,2)} (${phone.slice(2,4)}) ${phone.slice(4,9)}-${phone.slice(9)}`;
  }
  return phone;
}

function formatPlaca(placa) {
  if (!placa) return '';
  const clean = placa.toUpperCase().replace(/[^A-Z0-9]/g, '');
  if (clean.length === 7) {
    if (/^[A-Z]{3}[0-9]{4}$/.test(clean)) {
      return `${clean.slice(0,3)}-${clean.slice(3)}`;
    }
  }
  return clean;
}

async function marcarComoEnviado(mId) {
  try {
    await fetch(`/api/marcar-enviado/${mId}`, { method: 'POST' });
    loadData();
  } catch (err) {
    console.error("Erro ao marcar envio:", err);
  }
}

function copiarLink(link) {
  navigator.clipboard.writeText(link);
  alert("Link de atualização copiado para a área de transferência!");
}

async function deletarMensalista(mId) {
  if (confirm("Tem certeza que deseja excluir este mensalista?")) {
    await fetch(`/api/mensalistas/${mId}`, { method: 'DELETE' });
    loadData();
  }
}

function openImportModal() {
  document.getElementById('modal-import').classList.add('active');
}
function closeImportModal() {
  document.getElementById('modal-import').classList.remove('active');
}

function openAddModal() {
  document.getElementById('modal-add').classList.add('active');
}
function closeAddModal() {
  document.getElementById('modal-add').classList.remove('active');
}

function toggleAddModalLoja(val) {
  const group = document.getElementById('add-group-loja');
  if (group) {
    group.style.display = val === 'Mensalista Externo' ? 'none' : 'block';
  }
}

async function handleAddSubmit(e) {
  e.preventDefault();
  const nome = document.getElementById('add-nome').value;
  const telefone = document.getElementById('add-telefone').value;
  const cpf = document.getElementById('add-cpf').value;
  const email = document.getElementById('add-email').value;
  const tipo_vinculo = document.getElementById('add-vinculo').value;
  const nome_loja = tipo_vinculo === 'Mensalista Externo' ? 'Mensalista Externo' : document.getElementById('add-loja').value;
  const numero_cartao = document.getElementById('add-cartao').value;

  const res = await fetch('/api/mensalistas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome, telefone, numero_cartao, tipo_vinculo, nome_loja, cpf, email })
  });

  if (res.ok) {
    closeAddModal();
    document.getElementById('add-nome').value = '';
    document.getElementById('add-telefone').value = '';
    document.getElementById('add-cpf').value = '';
    document.getElementById('add-email').value = '';
    document.getElementById('add-loja').value = '';
    document.getElementById('add-cartao').value = '';
    loadData();
  } else {
    alert("Erro ao adicionar mensalista.");
  }
}

async function handleImportSubmit(e) {
  e.preventDefault();
  const fileInput = document.getElementById('file-import');
  if (fileInput.files.length === 0) return;

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  try {
    const res = await fetch('/api/importar-csv', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      alert(`Importação concluída! ${data.importados} mensalistas importados.`);
      closeImportModal();
      loadData();
    } else {
      alert(data.error || "Erro na importação.");
    }
  } catch (err) {
    alert("Falha na requisição de importação.");
  }
}

function atualizarPréviaMensagem() {
  const nomeEst = document.getElementById('config-nome-estacionamento').value || 'Estacionamento Iguatemi Brasília';
  const template = document.getElementById('config-mensagem-template').value || '';
  
  const previa = template.replace('{nome}', 'Carlos Silva')
                         .replace('{link}', 'https://estacionamento.com/atualizar/TOKEN_DEMO')
                         .replace('{nome_estacionamento}', nomeEst);
                         
  document.getElementById('previa-mensagem-texto').innerText = previa;
}

async function salvarConfiguracoes() {
  const nome_estacionamento = document.getElementById('config-nome-estacionamento').value;
  const dominio_publico = document.getElementById('config-dominio-publico').value;
  const mensagem_template = document.getElementById('config-mensagem-template').value;

  const res = await fetch('/api/configuracoes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome_estacionamento, dominio_publico, mensagem_template })
  });

  if (res.ok) {
    alert("Configurações salvas com sucesso!");
    await loadConfiguracoes();
    await loadData();
  }
}

function updateLotePreview() {
  const filtro = document.getElementById('lote-filtro').value;
  let selecionados = [];

  if (filtro === 'pendentes') {
    selecionados = mensalistasData.filter(m => m.status_envio !== 'Enviado');
  } else if (filtro === 'nao_recadastrados') {
    selecionados = mensalistasData.filter(m => m.status_cadastro !== 'Atualizado');
  } else {
    selecionados = [...mensalistasData];
  }

  document.getElementById('lote-resumo-texto').innerHTML = `
    Existem <strong>${selecionados.length} mensalistas</strong> aptos para receber a mensagem nesta seleção.
  `;
}

async function iniciarDisparoLote() {
  const filtro = document.getElementById('lote-filtro').value;
  const delaySec = parseInt(document.getElementById('lote-delay').value) || 8;
  
  let lista = [];
  if (filtro === 'pendentes') {
    lista = mensalistasData.filter(m => m.status_envio !== 'Enviado');
  } else if (filtro === 'nao_recadastrados') {
    lista = mensalistasData.filter(m => m.status_cadastro !== 'Atualizado');
  } else {
    lista = [...mensalistasData];
  }

  if (lista.length === 0) {
    alert("Nenhum mensalista para enviar com este filtro.");
    return;
  }

  if (!confirm(`Iniciar envio sequencial para ${lista.length} pessoas com intervalo de ${delaySec} segundos?`)) {
    return;
  }

  const btn = document.getElementById('btn-iniciar-lote');
  btn.disabled = true;

  for (let i = 0; i < lista.length; i++) {
    const item = lista[i];
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Enviando ${i + 1}/${lista.length}: ${item.nome}...`;
    
    window.open(item.whatsapp_url, '_blank');
    await marcarComoEnviado(item.id);
    
    await new Promise(resolve => setTimeout(resolve, delaySec * 1000));
  }

  btn.disabled = false;
  btn.innerHTML = `<i class="fa-brands fa-whatsapp"></i> Iniciar Sequência de Disparo`;
  alert("Sequência de disparos em lote finalizada!");
  loadData();
}

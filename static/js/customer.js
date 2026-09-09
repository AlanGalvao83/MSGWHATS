let vehicleCount = 0;

document.addEventListener('DOMContentLoaded', () => {
  if (INITIAL_VEHICLES && INITIAL_VEHICLES.length > 0) {
    INITIAL_VEHICLES.forEach(v => addVehicleForm(v));
  } else {
    addVehicleForm();
  }
});

function addVehicleForm(data = {}) {
  vehicleCount++;
  const container = document.getElementById('vehicles-container');
  const card = document.createElement('div');
  card.className = 'vehicle-card';
  card.id = `vehicle-card-${vehicleCount}`;

  const isFirst = container.children.length === 0;

  card.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
      <h4 style="color: var(--text-main); font-weight: 700; font-size: 1.05rem;">
        <i class="fa-solid fa-car"></i> Veículo ${vehicleCount}
      </h4>
      ${!isFirst ? `<button type="button" class="btn btn-danger btn-sm remove-btn" onclick="removeVehicleForm(${vehicleCount})"><i class="fa-solid fa-trash"></i> Remover</button>` : ''}
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
      <div class="form-group" style="grid-column: span 2;">
        <label class="form-label">Modelo do Veículo *</label>
        <input type="text" class="form-control input-modelo" placeholder="Ex: Toyota Corolla / Fiat Uno" value="${data.modelo || ''}" required>
      </div>

      <div class="form-group">
        <label class="form-label">Ano *</label>
        <input type="text" class="form-control input-ano" placeholder="Ex: 2022" value="${data.ano || ''}" required>
      </div>

      <div class="form-group">
        <label class="form-label">Cor *</label>
        <input type="text" class="form-control input-cor" placeholder="Ex: Prata" value="${data.cor || ''}" required>
      </div>

      <div class="form-group" style="grid-column: span 2;">
        <label class="form-label">Placa do Veículo (Liberada para LPR) *</label>
        <div style="display: flex; gap: 0.75rem; align-items: center;">
          <input type="text" class="form-control input-placa" placeholder="Ex: ABC1D23 ou ABC-1234" value="${data.placa || ''}" oninput="handlePlacaInput(this)" maxlength="8" required style="font-family: monospace; font-size: 1.1rem; font-weight: bold; letter-spacing: 2px; text-transform: uppercase;">
        </div>
        <small style="color: var(--text-muted); margin-top: 4px; display: block;">
          Aceita padrão Mercosul (ABC1D23) ou tradicional (ABC-1234).
        </small>
      </div>
    </div>
  `;

  container.appendChild(card);
  if (data.placa) {
    const input = card.querySelector('.input-placa');
    handlePlacaInput(input);
  }
}

function removeVehicleForm(id) {
  const card = document.getElementById(`vehicle-card-${id}`);
  if (card) {
    card.remove();
  }
}

function handlePlacaInput(input) {
  let val = input.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  if (val.length > 7) {
    val = val.slice(0, 7);
  }
  input.value = val;
}

async function handleCustomerSubmit(e) {
  e.preventDefault();

  const numeroCartaoInput = document.getElementById('numero-cartao');
  const numero_cartao = numeroCartaoInput ? numeroCartaoInput.value.trim() : '';

  if (!numero_cartao || numero_cartao.length !== 6 || !/^\d{6}$/.test(numero_cartao)) {
    alert("Por favor, informe os 6 dígitos numéricos do seu cartão de estacionamento.");
    if (numeroCartaoInput) numeroCartaoInput.focus();
    return;
  }

  const cards = document.querySelectorAll('.vehicle-card');
  const veiculos = [];

  cards.forEach(card => {
    const modelo = card.querySelector('.input-modelo').value.trim();
    const ano = card.querySelector('.input-ano').value.trim();
    const cor = card.querySelector('.input-cor').value.trim();
    const placa = card.querySelector('.input-placa').value.trim().toUpperCase();

    if (modelo && placa) {
      veiculos.push({ modelo, ano, cor, placa });
    }
  });

  if (veiculos.length === 0) {
    alert("Por favor, preencha ao menos 1 veículo com Modelo e Placa.");
    return;
  }

  const btn = document.getElementById('btn-submit-customer');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Salvando Cadastro...`;

  try {
    const res = await fetch(`/api/recadastro/${TOKEN}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ veiculos, numero_cartao })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      window.location.href = '/sucesso';
    } else {
      alert(data.error || "Erro ao salvar recadastro. Verifique os dados e tente novamente.");
      btn.disabled = false;
      btn.innerHTML = `<i class="fa-solid fa-check-circle"></i> Confirmar e Salvar Cadastro`;
    }
  } catch (err) {
    alert("Erro na conexão com o servidor.");
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-check-circle"></i> Confirmar e Salvar Cadastro`;
  }
}

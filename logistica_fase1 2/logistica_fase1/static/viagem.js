// Formulário de viagem: linhas de carga dinâmicas e ocupação do caminhão em tempo real.
(function () {
    const bruto = document.getElementById('dados-viagem');
    if (!bruto) return;

    const dados = JSON.parse(bruto.textContent);
    const container = document.getElementById('cargas');
    const modelo = document.getElementById('modelo-carga');
    const selCaminhao = document.getElementById('sel-caminhao');
    const form = document.getElementById('form-viagem');
    const kmIni = document.getElementById('km-ini');
    const kmFim = document.getElementById('km-fim');
    const aviso = document.getElementById('aviso-ocupacao');

    const numero = (v) => {
        const n = parseFloat(String(v).replace(',', '.'));
        return Number.isFinite(n) ? n : 0;
    };
    const fmt = (n, casas = 0) =>
        n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

    function renumerar() {
        const linhas = container.querySelectorAll('.carga');
        linhas.forEach((linha, i) => {
            linha.querySelector('.carga-num').textContent = 'Carga ' + (i + 1);
            linha.querySelector('.remover').hidden = linhas.length === 1;
        });
    }

    function atualizarBarra(id, usado, capacidade, unidade, casas) {
        const barra = document.getElementById('barra-' + id);
        const txt = document.getElementById('txt-' + id);
        if (!capacidade) {
            barra.style.width = '0';
            barra.className = '';
            txt.textContent = fmt(usado, casas) + ' ' + unidade + ' (escolha o caminhão)';
            return 0;
        }
        const pct = (usado / capacidade) * 100;
        barra.style.width = Math.min(pct, 100) + '%';
        barra.className = pct > 100 ? 'excesso' : pct >= 90 ? 'alerta' : '';
        txt.textContent =
            fmt(usado, casas) + ' de ' + fmt(capacidade, casas) + ' ' + unidade + ' (' + fmt(pct) + '%)';
        return pct;
    }

    function recalcular() {
        let pesoTotal = 0;
        let cubTotal = 0;

        container.querySelectorAll('.carga').forEach((linha) => {
            const produto = dados.produtos[linha.querySelector('[name=produto_id]').value];
            const qtd = numero(linha.querySelector('[name=quantidade]').value);
            const campoNf = linha.querySelector('[name=valor_nf]');
            const info = linha.querySelector('.carga-info');
            const valido = produto && qtd > 0;

            // O valor da NF acompanha quantidade x valor do produto, a não ser que a pessoa digite outro
            if (campoNf.dataset.manual !== '1') {
                campoNf.value = valido ? (qtd * produto.valor).toFixed(2) : '';
            }

            if (!valido) {
                info.textContent = '';
                return;
            }
            const peso = qtd * produto.peso;
            const cub = qtd * produto.cubagem;
            pesoTotal += peso;
            cubTotal += cub;
            info.textContent = 'Esta carga: ' + fmt(peso, 1) + ' kg e ' + fmt(cub, 2) + ' m³';
        });

        const caminhao = dados.caminhoes[selCaminhao.value];
        const pctPeso = atualizarBarra('peso', pesoTotal, caminhao && caminhao.capacidade_kg, 'kg', 0);
        const pctCub = atualizarBarra('cub', cubTotal, caminhao && caminhao.cubagem_m3, 'm³', 2);

        const avisos = [];
        if (pctPeso > 100) {
            avisos.push('Excesso de peso: ' + fmt(pesoTotal - caminhao.capacidade_kg, 1) +
                ' kg acima da capacidade. Isso pode gerar multa na balança.');
        }
        if (pctCub > 100) {
            avisos.push('A cubagem passa da capacidade do caminhão em ' +
                fmt(cubTotal - caminhao.cubagem_m3, 2) + ' m³.');
        }
        aviso.hidden = avisos.length === 0;
        aviso.textContent = avisos.join(' ');
    }

    function adicionarLinha() {
        container.append(modelo.content.cloneNode(true));
        renumerar();
        recalcular();
    }

    container.addEventListener('input', (e) => {
        if (e.target.name === 'valor_nf') {
            e.target.dataset.manual = e.target.value === '' ? '0' : '1';
        }
        recalcular();
    });
    container.addEventListener('change', recalcular);
    container.addEventListener('click', (e) => {
        if (e.target.classList.contains('remover')) {
            e.target.closest('.carga').remove();
            renumerar();
            recalcular();
        }
    });
    selCaminhao.addEventListener('change', recalcular);
    document.getElementById('add-carga').addEventListener('click', adicionarLinha);

    form.addEventListener('submit', (e) => {
        if (numero(kmFim.value) < numero(kmIni.value)) {
            e.preventDefault();
            alert('O km final não pode ser menor que o km inicial.');
            kmFim.focus();
        }
    });

    adicionarLinha();
})();

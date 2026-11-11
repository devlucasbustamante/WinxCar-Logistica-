/* ============================================================
   Controle de cargas e ocupação da viagem
   - Adiciona/remove cargas dinamicamente
   - Calcula peso e cubagem em tempo real
   - Atualiza a capacidade conforme o caminhão selecionado
   - Mostra aviso quando passa de 100%
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

    const btnAddCarga = document.getElementById('add-carga');
    const contCargas  = document.getElementById('cargas');
    const tplCarga    = document.getElementById('modelo-carga');

    // Se não há formulário de viagem nesta página, não faz nada
    if (!btnAddCarga || !contCargas || !tplCarga) return;

    // ---------- Dados vindos do backend ----------
    const dadosEl = document.getElementById('dados-viagem');
    const dados = dadosEl ? JSON.parse(dadosEl.textContent) : {};

    const produtos    = dados.produtos || {};
    const capacidades = dados.capacidades || {};

    // ---------- Elementos de UI ----------
    const selectCaminhao = document.getElementById('select-caminhao');
    const painelOcupacao = document.getElementById('painel-ocupacao');

    const barraPeso = document.getElementById('barra-peso');
    const barraCub  = document.getElementById('barra-cub');
    const txtPeso   = document.getElementById('txt-peso');
    const txtCub    = document.getElementById('txt-cub');
    const aviso     = document.getElementById('aviso-ocupacao');

    // ---------- Estado ----------
    let capacidadePesoAtual = Number(dados.capacidade_peso) || 0;
    let capacidadeCubAtual  = Number(dados.capacidade_cub)  || 0;

    let contador = 0;
    let excedido = false;   // true quando peso ou cubagem passa de 100%

    /* --------------------------------------------------------
       Lê a capacidade do caminhão selecionado e atualiza o estado
       -------------------------------------------------------- */
    function atualizarCapacidadeDoCaminhao() {
        if (!selectCaminhao) return;

        const id = selectCaminhao.value;

        if (!id) {
            // Nenhum caminhão selecionado
            capacidadePesoAtual = 0;
            capacidadeCubAtual  = 0;
            if (painelOcupacao) painelOcupacao.style.opacity = '0.5';
            return;
        }

        // 1) Tenta pelo JSON do backend
        const cap = capacidades[id];

        if (cap) {
            capacidadePesoAtual = Number(cap.peso) || 0;
            capacidadeCubAtual  = Number(cap.cub)  || 0;
        } else {
            // 2) Fallback: lê dos atributos data-* do <option>
            const option = selectCaminhao.querySelector(`option[value="${id}"]`);
            if (option) {
                capacidadePesoAtual = Number(option.dataset.capacidadePeso) || 0;
                capacidadeCubAtual  = Number(option.dataset.capacidadeCub)  || 0;
            } else {
                capacidadePesoAtual = 0;
                capacidadeCubAtual  = 0;
            }
        }

        if (painelOcupacao) painelOcupacao.style.opacity = '1';
    }

    /* --------------------------------------------------------
       Recalcula peso, cubagem e atualiza barras/avisos
       -------------------------------------------------------- */
    function atualizar() {
        let peso = 0;
        let cub  = 0;

        contCargas.querySelectorAll('.carga').forEach(bloco => {
            const selProd = bloco.querySelector('select[name="produto_id"]');
            const inpQtd  = bloco.querySelector('input[name="quantidade"]');
            const qtd = parseFloat(inpQtd?.value || 0);

            const id = selProd?.value;
            const produto = id ? produtos[id] : null;

            if (produto && qtd > 0) {
                peso += Number(produto.peso_kg)   * qtd;
                cub  += Number(produto.cubagem_m3) * qtd;
            }
        });

        // ---- Texto ----
        if (txtPeso) txtPeso.textContent = `${peso.toFixed(1).replace('.', ',')} kg`;
        if (txtCub)  txtCub.textContent  = `${cub.toFixed(3).replace('.', ',')} m³`;

        // ---- Percentuais ----
        let pctPeso = capacidadePesoAtual > 0 ? (peso / capacidadePesoAtual) * 100 : 0;
        let pctCub  = capacidadeCubAtual  > 0 ? (cub  / capacidadeCubAtual)  * 100 : 0;

        // Limita visualmente em 150% (para a barra não explodir)
        const pctPesoVis = Math.min(pctPeso, 150);
        const pctCubVis  = Math.min(pctCub, 150);

        // ---- Barras ----
        if (barraPeso) {
            barraPeso.style.width = pctPesoVis + '%';
            barraPeso.classList.remove('alerta', 'excesso');
        }
        if (barraCub) {
            barraCub.style.width = pctCubVis + '%';
            barraCub.classList.remove('alerta', 'excesso');
        }

        excedido = pctPeso > 100 || pctCub > 100;

        // ---- Aviso ----
        if (aviso) aviso.hidden = true;

        const semCaminhao = selectCaminhao && !selectCaminhao.value;

        if (semCaminhao && (peso > 0 || cub > 0)) {
            if (aviso) {
                aviso.hidden = false;
                aviso.textContent = 'Selecione o caminhão para calcular a ocupação.';
                aviso.classList.add('aviso-info');
                aviso.classList.remove('aviso-erro');
            }
            return;
        }

        if (pctPeso > 100 || pctCub > 100) {
            if (aviso) {
                aviso.hidden = false;
                aviso.textContent = 'Capacidade excedida! Reduza a carga ou troque de caminhão.';
                aviso.classList.remove('aviso-info');
                aviso.classList.add('aviso-erro');
            }
            if (barraPeso) barraPeso.classList.add('excesso');
            if (barraCub)  barraCub.classList.add('excesso');
        } else if (pctPeso > 85 || pctCub > 85) {
            if (barraPeso) barraPeso.classList.add('alerta');
            if (barraCub)  barraCub.classList.add('alerta');
        }
    }

    /* --------------------------------------------------------
       Adiciona bloco de carga a partir do <template>
       -------------------------------------------------------- */
    function adicionarCarga() {
        contador++;
        const clone = tplCarga.content.cloneNode(true);
        const bloco = clone.querySelector('.carga');

        if (!bloco) return;

        const numEl = bloco.querySelector('.carga-num');
        if (numEl) numEl.textContent = `Carga ${contador}`;

        const selProd    = bloco.querySelector('select[name="produto_id"]');
        const inpQtd     = bloco.querySelector('input[name="quantidade"]');
        const inpValorNF = bloco.querySelector('input[name="valor_nf"]');
        const info       = bloco.querySelector('.carga-info');
        const btnRemover = bloco.querySelector('.remover');

        // Ao trocar o produto, preenche info e valor NF
        if (selProd) {
            selProd.addEventListener('change', () => {
                const id = selProd.value;
                const p = id ? produtos[id] : null;

                if (p) {
                    if (info) {
                        info.textContent =
                            `Peso unitário: ${Number(p.peso_kg).toFixed(1)} kg` +
                            ` • Cubagem: ${Number(p.cubagem_m3).toFixed(3)} m³` +
                            ` • Valor NF base: R$ ${Number(p.valor_nf).toFixed(2)}`;
                    }
                    if (inpValorNF && !inpValorNF.value) {
                        inpValorNF.value = Number(p.valor_nf).toFixed(2);
                    }
                } else if (info) {
                    info.textContent = '';
                }

                atualizar();
            });
        }

        // Ao mudar quantidade, recalcula
        if (inpQtd) inpQtd.addEventListener('input', atualizar);

        // Botão remover
        if (btnRemover) {
            btnRemover.addEventListener('click', () => {
                bloco.remove();
                renumerar();
                atualizar();
            });
        }

        contCargas.appendChild(clone);
        atualizar();
    }

    /* --------------------------------------------------------
       Renumera os blocos de carga após remoção
       -------------------------------------------------------- */
    function renumerar() {
        const blocos = contCargas.querySelectorAll('.carga');
        blocos.forEach((b, i) => {
            const numEl = b.querySelector('.carga-num');
            if (numEl) numEl.textContent = `Carga ${i + 1}`;
        });
        contador = blocos.length;
    }

    /* --------------------------------------------------------
       Listeners iniciais
       -------------------------------------------------------- */
    if (selectCaminhao) {
        selectCaminhao.addEventListener('change', () => {
            atualizarCapacidadeDoCaminhao();
            atualizar();
        });
    }

    btnAddCarga.addEventListener('click', adicionarCarga);

    // Impede salvar viagem acima da capacidade ou sem carga
    const form = btnAddCarga.closest('form');
    if (form) {
        form.addEventListener('submit', (ev) => {
            const temCarga = [...contCargas.querySelectorAll('select[name="produto_id"]')]
                .some(s => s.value);
            if (!temCarga) {
                ev.preventDefault();
                alert('Adicione pelo menos uma carga (nota fiscal) à viagem.');
            } else if (excedido) {
                ev.preventDefault();
                alert('Capacidade do caminhão excedida! Reduza a carga ou troque de caminhão.');
            }
        });
    }

    // Estado inicial
    atualizarCapacidadeDoCaminhao();
    adicionarCarga();
});
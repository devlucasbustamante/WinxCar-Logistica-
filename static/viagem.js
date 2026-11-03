// Controle de cargas e ocupação da viagem

document.addEventListener('DOMContentLoaded', () => {

    const btnAddCarga = document.getElementById('add-carga');
    const contCargas = document.getElementById('cargas');
    const tplCarga = document.getElementById('modelo-carga');

    const dadosEl = document.getElementById('dados-viagem');
    const dados = dadosEl ? JSON.parse(dadosEl.textContent) : {};

    const produtos = dados.produtos || {};
    const capacidadePeso = dados.capacidade_peso || 0;
    const capacidadeCub = dados.capacidade_cub || 0;

    const barraPeso = document.getElementById('barra-peso');
    const barraCub = document.getElementById('barra-cub');
    const txtPeso = document.getElementById('txt-peso');
    const txtCub = document.getElementById('txt-cub');
    const aviso = document.getElementById('aviso-ocupacao');

    let contador = 0;

    function atualizar() {
        let peso = 0;
        let cub = 0;

        contCargas.querySelectorAll('.carga').forEach(bloco => {
            const selProd = bloco.querySelector('select[name="produto_id"]');
            const qtd = parseFloat(bloco.querySelector('input[name="quantidade"]').value || 0);

            const id = selProd.value;
            if (id && produtos[id] && qtd > 0) {
                peso += produtos[id].peso_kg * qtd;
                cub += produtos[id].cubagem_m3 * qtd;
            }
        });

        txtPeso.textContent = `${peso.toFixed(1)} kg`;
        txtCub.textContent = `${cub.toFixed(3)} m³`;

        let pctPeso = capacidadePeso ? (peso / capacidadePeso) * 100 : 0;
        let pctCub = capacidadeCub ? (cub / capacidadeCub) * 100 : 0;

        pctPeso = Math.min(pctPeso, 150);
        pctCub = Math.min(pctCub, 150);

        barraPeso.style.width = pctPeso + '%';
        barraCub.style.width = pctCub + '%';

        barraPeso.classList.remove('alerta', 'excesso');
        barraCub.classList.remove('alerta', 'excesso');
        aviso.hidden = true;

        if (pctPeso > 100 || pctCub > 100) {
            aviso.hidden = false;
            aviso.textContent = 'Capacidade excedida!';
            barraPeso.classList.add('excesso');
            barraCub.classList.add('excesso');
        } else if (pctPeso > 85 || pctCub > 85) {
            barraPeso.classList.add('alerta');
            barraCub.classList.add('alerta');
        }
    }

    function adicionarCarga() {
        contador++;
        const clone = tplCarga.content.cloneNode(true);
        const bloco = clone.querySelector('.carga');

        bloco.querySelector('.carga-num').textContent = `Carga ${contador}`;

        const selProd = bloco.querySelector('select[name="produto_id"]');
        const inpQtd = bloco.querySelector('input[name="quantidade"]');
        const inpValorNF = bloco.querySelector('input[name="valor_nf"]');
        const info = bloco.querySelector('.carga-info');

        selProd.addEventListener('change', () => {
            const id = selProd.value;
            if (id && produtos[id]) {
                const p = produtos[id];
                info.textContent = `Peso unitário: ${p.peso_kg} kg • Cubagem: ${p.cubagem_m3} m³ • Valor NF base: R$ ${p.valor_nf}`;
                if (!inpValorNF.value) inpValorNF.value = p.valor_nf;
            } else {
                info.textContent = '';
            }
            atualizar();
        });

        inpQtd.addEventListener('input', atualizar);

        bloco.querySelector('.remover').addEventListener('click', () => {
            bloco.remove();
            atualizar();
        });

        contCargas.appendChild(clone);
        atualizar();
    }

    btnAddCarga.addEventListener('click', adicionarCarga);

    // Começa com 1 carga
    adicionarCarga();
});

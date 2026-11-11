"""
Preenche o banco (logistica.db) com DADOS FICTÍCIOS para demonstração.

Uso:
    python popular_dados.py            -> só popula se o banco estiver vazio
    python popular_dados.py --limpar   -> APAGA tudo e popula de novo
    python popular_dados.py --se-vazio -> igual ao primeiro, mas sem mensagem
                                          quando já há dados (usado pelo iniciar.bat)

As datas são geradas a partir de HOJE (últimos 30 dias), então o
"Resumo do Dia" da tela de Viagens sempre terá dados.
"""
import random
import sqlite3
import sys
from datetime import date, timedelta

import app  # garante que as tabelas existam (app.init_db roda ao importar)

random.seed(2026)  # mesmos dados toda vez que rodar
HOJE = date.today()

CAMINHOES = [
    # placa,    categoria, cv,  eixos, capacidade_kg, cubagem_m3
    ("FTC2A26", "Carreta", 540, 6, 32000, 90),
    ("WXC1B34", "Truck",   330, 3, 14000, 48),
    ("LOG4C21", "Bitrem",  580, 7, 37000, 105),
    ("RTA7D88", "VUC",     156, 2,  3500, 18),
    ("SPX3E45", "3/4",     185, 2,  4500, 22),
    ("FRT9F12", "Truck",   310, 3, 13000, 45),
]

MOTORISTAS = [
    ("Carlos Eduardo Ramos", "04587123690", "(11) 98734-2210"),
    ("Mariana Souza Lima",   "07812369451", "(11) 97621-4589"),
    ("João Pedro Almeida",   "02369874512", "(19) 99812-3344"),
    ("Ana Beatriz Costa",    "05698712340", "(11) 96543-7788"),
    ("Rafael Nogueira",      "08741236985", "(13) 98123-5566"),
    ("Luciana Ferreira",     "01236547890", "(15) 99654-1122"),
]

NOTAS = [
    # numero,   descrição,                              peso_kg, volume_m3, valor_R$
    ("NF-10231", "Eletrodomésticos (geladeiras)",         1850,  12.5,  42500.00),
    ("NF-10232", "Cimento CP-II 50kg (100 sacos)",        5000,   3.8,   3450.00),
    ("NF-10233", "Bebidas - fardos de água mineral",      2400,   4.2,   2880.00),
    ("NF-10234", "Peças automotivas",                      620,   2.1,  18700.00),
    ("NF-10235", "Móveis planejados desmontados",         1300,  15.0,  27900.00),
    ("NF-10236", "Grãos - café em sacas (40 sacas)",      2400,   3.6,  52000.00),
    ("NF-10237", "Produtos de limpeza",                    950,   5.4,   6350.00),
    ("NF-10238", "Pneus de caminhão (20 un.)",            1200,   9.0,  38000.00),
    ("NF-10239", "Embalagens de papelão",                  700,  10.5,   4200.00),
    ("NF-10240", "Medicamentos (carga refrigerada)",       300,   1.8,  65400.00),
    ("NF-10241", "Aço em barras",                         6500,   2.5,  31200.00),
    ("NF-10242", "Eletrônicos (TVs e notebooks)",          480,   4.0,  96800.00),
]

DESTINOS = [
    ("Distribuidora Paulista Ltda", "São Paulo / SP"),
    ("Atacadão Vale do Paraíba",    "São José dos Campos / SP"),
    ("Centro Logístico Interior",   "Campinas / SP"),
    ("Mercado Bom Preço",           "Sorocaba / SP"),
    ("Porto Seco Santos",           "Santos / SP"),
    ("Rede Construir Materiais",    "Ribeirão Preto / SP"),
    ("Farma Sul Distribuição",      "Curitiba / PR"),
    ("Casa & Lar Magazine",         "Belo Horizonte / MG"),
    ("Comercial Rio Sul",           "Rio de Janeiro / RJ"),
]

MANUTENCOES = [
    # peça,                 custo,   status,         empresa
    ("Troca de óleo e filtros", 1250.00, "Concluído",    "Mecânica São Lucas"),
    ("Pneu",                    2890.00, "Concluído",    "Pneus Rodovia"),
    ("Pastilha de Freio",        980.00, "Concluído",    "Freios Brasil"),
    ("Correia",                  640.00, "Pendente",     "Mecânica São Lucas"),
    ("Alinhamento e balanceamento", 420.00, "Concluído", "Pneus Rodovia"),
    ("Filtro de ar",             310.00, "Em andamento", "Auto Diesel Center"),
    ("Revisão do sistema elétrico", 1580.00, "Pendente", "Auto Diesel Center"),
    ("Embreagem",               4350.00, "Em andamento", "Truck Service SP"),
    ("Pneu",                    3120.00, "Concluído",    "Pneus Rodovia"),
    ("Óleo",                     890.00, "Concluído",    "Truck Service SP"),
]


def tem_dados(db):
    return any(
        db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("caminhoes", "motoristas", "notas_fiscais", "viagens", "manutencoes")
    )


def limpar(db):
    for t in ("viagem_cargas", "viagens", "manutencoes",
              "notas_fiscais", "motoristas", "caminhoes"):
        db.execute(f"DELETE FROM {t}")
    db.execute("DELETE FROM sqlite_sequence")  # reinicia os IDs


def popular(db):
    db.executemany(
        "INSERT INTO caminhoes (placa, categoria, potencia_cv, eixos, capacidade_kg, cubagem_m3) "
        "VALUES (?,?,?,?,?,?)", CAMINHOES)
    db.executemany(
        "INSERT INTO motoristas (nome, cnh, telefone) VALUES (?,?,?)", MOTORISTAS)
    db.executemany(
        "INSERT INTO notas_fiscais (numero_nf, descricao_carga, peso_total_kg, "
        "volume_total_m3, valor_total) VALUES (?,?,?,?,?)", NOTAS)

    caminhoes = db.execute("SELECT id, capacidade_kg, cubagem_m3 FROM caminhoes").fetchall()
    motoristas = [r[0] for r in db.execute("SELECT id FROM motoristas")]
    notas = db.execute(
        "SELECT id, numero_nf, peso_total_kg, volume_total_m3, valor_total FROM notas_fiscais"
    ).fetchall()

    odometro = {c[0]: random.randint(80_000, 350_000) for c in caminhoes}

    # ---- Viagens: últimos 30 dias, garantindo 3 viagens HOJE ----
    dias = sorted([random.randint(1, 30) for _ in range(25)], reverse=True) + [0, 0, 0]
    total_viagens = 0
    for d in dias:
        dia = HOJE - timedelta(days=d)
        cam_id, cap_kg, cap_m3 = random.choice(caminhoes)

        # Monta de 1 a 3 cargas que caibam no caminhão
        cargas, peso, cub = [], 0.0, 0.0
        qtd_cargas = random.randint(1, 3)
        for nota in random.sample(notas, k=len(notas)):
            if len(cargas) == qtd_cargas:
                break
            qtd = random.choice([1, 1, 1, 2])
            p, v = nota[2] * qtd, nota[3] * qtd
            if peso + p <= cap_kg and cub + v <= cap_m3:
                cargas.append((nota, qtd, p, v))
                peso, cub = peso + p, cub + v
        if not cargas:
            continue

        km = random.randint(60, 900)
        km_ini = odometro[cam_id]
        odometro[cam_id] += km
        destino, cidade = random.choice(DESTINOS)

        if d == 0:
            status = "Em rota"
        elif d <= 2:
            status = random.choice(["Em rota", "Finalizada", "Atrasada"])
        else:
            status = random.choice(["Finalizada"] * 8 + ["Atrasada", "Cancelada"])

        frete = round(km * random.uniform(6.5, 9.5) + peso * 0.04, 2)

        cur = db.execute(
            "INSERT INTO viagens (data, caminhao_id, motorista_id, km_inicial, km_final, "
            "destino, cidade_uf, tempo_estimado, status_viagem, valor_frete) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (dia.isoformat(), cam_id, random.choice(motoristas), km_ini, km_ini + km,
             destino, cidade, round(km / 65 * 2) / 2 or 0.5, status, frete),
        )
        db.executemany(
            "INSERT INTO viagem_cargas (viagem_id, nota_id, numero_nf, quantidade, "
            "peso_kg, cubagem_m3, valor_nf) VALUES (?,?,?,?,?,?,?)",
            [(cur.lastrowid, n[0], n[1], q, p, v, n[4] * q) for n, q, p, v in cargas],
        )
        total_viagens += 1

    # ---- Manutenções: espalhadas nos últimos 45 dias ----
    for i, (peca, custo, status, empresa) in enumerate(MANUTENCOES, start=1):
        dia = HOJE - timedelta(days=random.randint(0, 45))
        db.execute(
            "INSERT INTO manutencoes (data, caminhao_id, motorista_id, peca, custo, "
            "status, numero_os, empresa) VALUES (?,?,?,?,?,?,?,?)",
            (dia.isoformat(), random.choice(caminhoes)[0],
             random.choice(motoristas + [None]), peca, custo, status,
             f"OS-{HOJE.year}-{i:03d}", empresa),
        )

    return total_viagens


def main():
    db = sqlite3.connect(app.DB_PATH)
    if "--limpar" in sys.argv:
        limpar(db)
    elif tem_dados(db):
        if "--se-vazio" in sys.argv:
            return
        print("O banco já tem dados. Nada foi alterado.")
        print("Para APAGAR tudo e recarregar os dados fictícios: python popular_dados.py --limpar")
        return
    n = popular(db)
    db.commit()
    print(f"Pronto! Inseridos: {len(CAMINHOES)} caminhões, {len(MOTORISTAS)} motoristas, "
          f"{len(NOTAS)} notas fiscais, {n} viagens e {len(MANUTENCOES)} manutenções.")


if __name__ == "__main__":
    main()

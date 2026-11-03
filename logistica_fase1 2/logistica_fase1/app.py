"""Painel de Logística - Fase 1 (Arquitetura de Páginas Independentes)"""
import math
import os
import re
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from dotenv import load_dotenv

import webbrowser
from threading import Timer

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave-padrao-insegura")

BANCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logistica.db")

CATEGORIAS = ["VUC", "3/4", "Toco", "Truck", "Bitruck", "Carreta", "Bitrem", "Rodotrem"]
STATUS_MANUTENCAO = ["Trocado", "Revisado", "Reparado", "Pendente"]
PECAS_COMUNS = [
    "Pneu", "Pastilha de freio", "Lona de freio", "Óleo do motor", "Filtro de óleo",
    "Filtro de ar", "Filtro de combustível", "Correia", "Bateria", "Amortecedor", "Embreagem",
]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS caminhoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placa TEXT NOT NULL UNIQUE,
    potencia_cv INTEGER NOT NULL,
    eixos INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    capacidade_kg REAL NOT NULL,
    cubagem_m3 REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS motoristas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cnh TEXT,
    telefone TEXT
);
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    peso_unit_kg REAL NOT NULL,
    cubagem_unit_m3 REAL NOT NULL,
    valor_unit REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS viagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    caminhao_id INTEGER NOT NULL REFERENCES caminhoes(id),
    motorista_id INTEGER NOT NULL REFERENCES motoristas(id),
    km_inicial REAL NOT NULL,
    km_final REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS cargas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    viagem_id INTEGER NOT NULL REFERENCES viagens(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    nota_fiscal TEXT NOT NULL,
    quantidade REAL NOT NULL,
    peso_kg REAL NOT NULL,
    cubagem_m3 REAL NOT NULL,
    valor_nf REAL NOT NULL,
    valor_frete REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS manutencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    caminhao_id INTEGER NOT NULL REFERENCES caminhoes(id),
    motorista_id INTEGER REFERENCES motoristas(id),
    peca TEXT NOT NULL,
    custo REAL NOT NULL,
    status TEXT NOT NULL
);
DROP VIEW IF EXISTS vw_viagens;
CREATE VIEW vw_viagens AS
SELECT v.id, v.data, v.caminhao_id, v.motorista_id,
       c.placa, m.nome AS motorista,
       v.km_inicial, v.km_final, (v.km_final - v.km_inicial) AS km,
       c.capacidade_kg, c.cubagem_m3 AS capacidade_m3,
       COALESCE(SUM(g.peso_kg), 0)    AS peso_kg,
       COALESCE(SUM(g.cubagem_m3), 0)  AS cubagem_m3,
       COALESCE(SUM(g.valor_nf), 0)    AS valor_nf,
       COALESCE(SUM(g.valor_frete), 0) AS valor_frete,
       COUNT(g.id) AS n_cargas
FROM viagens v
JOIN caminhoes c  ON c.id = v.caminhao_id
JOIN motoristas m ON m.id = v.motorista_id
LEFT JOIN cargas g ON g.viagem_id = v.id
GROUP BY v.id;
"""

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(BANCO)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def fechar_db(_erro):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def iniciar_banco():
    with app.app_context():
        get_db().executescript(ESQUEMA)

# ---------------------------------------------------------------------------
# Sistema de Login e Segurança
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logado"):
            flash("Acesso negado. Por favor, faça login.", "aviso")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == "fatec2026":
            session["logado"] = True
            flash("Bem-vindo ao Painel de Logística!", "ok")
            return redirect(url_for("home"))
        else:
            flash("Senha incorreta.", "erro")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada com segurança.", "ok")
    return redirect(url_for("login"))

class ErroValidacao(Exception): pass

def texto(valor, campo, max_len=80, obrigatorio=True):
    t = " ".join((valor or "").split())
    if obrigatorio and not t: raise ErroValidacao(f"Preencha o campo «{campo}».")
    if len(t) > max_len: raise ErroValidacao(f"«{campo}» aceita no máximo {max_len} caracteres.")
    return t

def numero(valor, campo, minimo=0.0, estrito=False):
    t = (valor or "").strip().replace(",", ".")
    if not t: raise ErroValidacao(f"Preencha o campo «{campo}».")
    try: n = float(t)
    except ValueError: raise ErroValidacao(f"«{campo}» precisa ser um número.")
    if not math.isfinite(n): raise ErroValidacao(f"«{campo}» tem valor inválido.")
    if estrito and n <= minimo: raise ErroValidacao(f"«{campo}» precisa ser maior que {minimo:g}.")
    if not estrito and n < minimo: raise ErroValidacao(f"«{campo}» não pode ser menor que {minimo:g}.")
    return n

def numero_opcional(valor, campo, padrao):
    if not (valor or "").strip(): return padrao
    return numero(valor, campo)

def inteiro(valor, campo, minimo=1):
    n = numero(valor, campo, minimo)
    if n != int(n): raise ErroValidacao(f"«{campo}» precisa ser inteiro.")
    return int(n)

def normalizar_placa(valor):
    placa = re.sub(r"[\s\-]", "", (valor or "").upper())
    if not re.fullmatch(r"[A-Z]{3}\d[A-Z0-9]\d{2}", placa):
        raise ErroValidacao("Placa inválida. Use ABC-1234 ou ABC1D23.")
    return placa

def data_iso(valor, campo="Data"):
    try: return datetime.strptime((valor or "").strip(), "%Y-%m-%d").date().isoformat()
    except ValueError: raise ErroValidacao(f"«{campo}» inválida.")

def escolher_opcao(valor, opcoes, campo):
    if valor not in opcoes: raise ErroValidacao(f"Escolha opção válida em «{campo}».")
    return valor

def buscar(db, tabela, valor, rotulo):
    try: registro_id = int(valor)
    except (TypeError, ValueError): raise ErroValidacao(f"Escolha {rotulo}.")
    linha = db.execute(f"SELECT * FROM {tabela} WHERE id = ?", (registro_id,)).fetchone()
    if linha is None: raise ErroValidacao(f"Não encontrei {rotulo}.")
    return linha

def fmt_num(valor, casas=0):
    s = f"{(valor or 0):,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

@app.template_filter("num")
def filtro_num(valor, casas=0): return fmt_num(valor, casas)

@app.template_filter("brl")
def filtro_brl(valor): return "R$ " + fmt_num(valor, 2)

@app.template_filter("placa")
def filtro_placa(valor):
    if valor and re.fullmatch(r"[A-Z]{3}\d{4}", valor): return f"{valor[:3]}-{valor[3:]}"
    return valor

@app.template_filter("data_br")
def filtro_data_br(valor):
    try: return datetime.strptime(valor, "%Y-%m-%d").strftime("%d/%m/%Y")
    except: return valor

@app.template_filter("faixa")
def filtro_faixa(percentual):
    if percentual > 100: return "excesso"
    if percentual >= 90: return "alerta"
    return "ok"

def percentual(valor, capacidade): return (valor / capacidade * 100) if capacidade else 0.0

def voltar(rota_destino, ancora=""):
    url = url_for(rota_destino)
    if ancora: url += "#" + ancora
    return redirect(url)

# --- 1. ROTA DASHBOARD INICIAL ---
@app.get("/")
@login_required
def home():
    db = get_db()
    totais = db.execute('''
        SELECT
            (SELECT COUNT(*) FROM caminhoes) as caminhoes,
            (SELECT COUNT(*) FROM motoristas) as motoristas,
            (SELECT COUNT(*) FROM viagens) as viagens,
            (SELECT COALESCE(SUM(custo), 0) FROM manutencoes) as custo_manutencao
    ''').fetchone()
    return render_template("index.html", totais=totais)

# --- 2. ROTA CADASTRAR/LISTAR ENTIDADES ---
@app.get("/cadastros")
@login_required
def cadastros():
    db = get_db()
    return render_template(
        "cadastros.html",
        caminhoes=db.execute("SELECT * FROM caminhoes ORDER BY placa").fetchall(),
        motoristas=db.execute("SELECT * FROM motoristas ORDER BY nome").fetchall(),
        produtos=db.execute("SELECT * FROM produtos ORDER BY nome").fetchall(),
        categorias=CATEGORIAS
    )

@app.post("/caminhoes")
@login_required
def novo_caminhao():
    f = request.form
    try:
        placa = normalizar_placa(f.get("placa"))
        potencia = inteiro(f.get("potencia_cv"), "Potência")
        eixos = inteiro(f.get("eixos"), "Nº eixos", minimo=2)
        categoria = escolher_opcao(f.get("categoria"), CATEGORIAS, "Categoria")
        capacidade = numero(f.get("capacidade_kg"), "Capacidade", estrito=True)
        cubagem = numero(f.get("cubagem_m3"), "Cubagem", estrito=True)
        db = get_db()
        with db:
            db.execute("INSERT INTO caminhoes (placa, potencia_cv, eixos, categoria, capacidade_kg, cubagem_m3) VALUES (?, ?, ?, ?, ?, ?)",
                       (placa, potencia, eixos, categoria, capacidade, cubagem))
        flash(f"Caminhão {filtro_placa(placa)} cadastrado.", "ok")
    except Exception as erro: flash(str(erro), "erro")
    return voltar("cadastros", "caminhoes")

@app.post("/motoristas")
@login_required
def novo_motorista():
    f = request.form
    try:
        nome = texto(f.get("nome"), "Nome", 80)
        cnh = texto(f.get("cnh"), "CNH", 20, False)
        telefone = texto(f.get("telefone"), "Telefone", 20, False)
        db = get_db()
        with db: db.execute("INSERT INTO motoristas (nome, cnh, telefone) VALUES (?, ?, ?)", (nome, cnh or None, telefone or None))
        flash(f"Motorista {nome} cadastrado.", "ok")
    except Exception as erro: flash(str(erro), "erro")
    return voltar("cadastros", "motoristas")

@app.post("/produtos")
@login_required
def novo_produto():
    f = request.form
    try:
        nome = texto(f.get("nome"), "Nome", 80)
        peso = numero(f.get("peso_unit_kg"), "Peso", estrito=True)
        cubagem = numero(f.get("cubagem_unit_m3"), "Cubagem", estrito=True)
        valor = numero(f.get("valor_unit"), "Valor")
        db = get_db()
        with db: db.execute("INSERT INTO produtos (nome, peso_unit_kg, cubagem_unit_m3, valor_unit) VALUES (?, ?, ?, ?)", (nome, peso, cubagem, valor))
        flash(f"Produto {nome} cadastrado.", "ok")
    except Exception as erro: flash(str(erro), "erro")
    return voltar("cadastros", "produtos")

# --- 3. ROTA VIAGENS ---
@app.get("/viagens")
@login_required
def viagens_page():
    db = get_db()
    try: dia = data_iso(request.args.get("data"))
    except ErroValidacao: dia = date.today().isoformat()

    def resumo(where="", params=()):
        return db.execute(f"SELECT COUNT(*) AS viagens, COALESCE(SUM(km), 0) AS km, COALESCE(SUM(peso_kg), 0) AS peso_kg, COALESCE(SUM(cubagem_m3), 0) AS cubagem_m3, COALESCE(SUM(valor_nf), 0) AS valor_nf, COALESCE(SUM(valor_frete), 0) AS valor_frete FROM vw_viagens {where}", params).fetchone()

    def agrupar(coluna, where="", params=()):
        return db.execute(f"SELECT {coluna} AS nome, COUNT(*) AS viagens, SUM(km) AS km, SUM(peso_kg) AS peso_kg, SUM(cubagem_m3) AS cubagem_m3, SUM(valor_nf) AS valor_nf, SUM(valor_frete) AS valor_frete FROM vw_viagens {where} GROUP BY {coluna} ORDER BY km DESC", params).fetchall()

    def listar(where="", params=(), limite=None):
        sufixo = f" LIMIT {int(limite)}" if limite else ""
        viagens = []
        for linha in db.execute(f"SELECT * FROM vw_viagens {where} ORDER BY data DESC, id DESC{sufixo}", params):
            v = dict(linha); v["pct_peso"] = percentual(v["peso_kg"], v["capacidade_kg"]); v["pct_cub"] = percentual(v["cubagem_m3"], v["capacidade_m3"]); v["cargas"] = []
            viagens.append(v)
        por_id = {v["id"]: v for v in viagens}
        if por_id:
            marcas = ",".join("?" * len(por_id))
            for c in db.execute(f"SELECT g.*, p.nome AS produto FROM cargas g JOIN produtos p ON p.id = g.produto_id WHERE g.viagem_id IN ({marcas}) ORDER BY g.id", list(por_id)).fetchall():
                d = dict(c); v = por_id[d["viagem_id"]]
                d["pct_peso"] = percentual(d["peso_kg"], v["capacidade_kg"]); d["pct_cub"] = percentual(d["cubagem_m3"], v["capacidade_m3"])
                v["cargas"].append(d)
        return viagens

    caminhoes_bd = db.execute("SELECT * FROM caminhoes ORDER BY placa").fetchall()
    produtos_bd = db.execute("SELECT * FROM produtos ORDER BY nome").fetchall()
    dados_js = {
        "caminhoes": {str(c["id"]): {"capacidade_kg": c["capacidade_kg"], "cubagem_m3": c["cubagem_m3"]} for c in caminhoes_bd},
        "produtos": {str(p["id"]): {"peso": p["peso_unit_kg"], "cubagem": p["cubagem_unit_m3"], "valor": p["valor_unit"]} for p in produtos_bd}
    }

    caminhoes_acum = agrupar("placa")
    motoristas_acum = agrupar("motorista")
    
    grafico = {
        "caminhoes": {"labels": [filtro_placa(r["nome"]) for r in caminhoes_acum], "km": [r["km"] for r in caminhoes_acum]},
        "motoristas": {"labels": [r["nome"] for r in motoristas_acum], "peso": [r["peso_kg"] for r in motoristas_acum]},
    }

    return render_template(
        "resultados_viagens.html", dia=dia, resumo_dia=resumo("WHERE data = ?", (dia,)), caminhoes_dia=agrupar("placa", "WHERE data = ?", (dia,)),
        motoristas_dia=agrupar("motorista", "WHERE data = ?", (dia,)), viagens_dia=listar("WHERE data = ?", (dia,)),
        resumo_acum=resumo(), caminhoes_acum=caminhoes_acum, motoristas_acum=motoristas_acum,
        por_produto=db.execute("SELECT c.placa, p.nome AS produto, SUM(g.quantidade) AS quantidade, SUM(g.peso_kg) AS peso_kg, SUM(g.cubagem_m3) AS cubagem_m3, SUM(g.valor_nf) AS valor_nf, SUM(g.valor_frete) AS valor_frete FROM cargas g JOIN viagens v ON v.id = g.viagem_id JOIN caminhoes c ON c.id = v.caminhao_id JOIN produtos p ON p.id = g.produto_id GROUP BY c.id, p.id ORDER BY c.placa, valor_frete DESC, valor_nf DESC").fetchall(),
        ultimas=listar(limite=30), grafico=grafico,
        caminhoes=caminhoes_bd, motoristas=db.execute("SELECT * FROM motoristas ORDER BY nome").fetchall(), produtos=produtos_bd,
        dados_js=dados_js, hoje=date.today().isoformat()
    )

@app.post("/viagens")
@login_required
def nova_viagem():
    f = request.form
    db = get_db()
    try:
        data = data_iso(f.get("data"))
        caminhao = buscar(db, "caminhoes", f.get("caminhao_id"), "caminhão")
        motorista = buscar(db, "motoristas", f.get("motorista_id"), "motorista")
        km_inicial = numero(f.get("km_inicial"), "Km inicial")
        km_final = numero(f.get("km_final"), "Km final")
        if km_final < km_inicial: raise ErroValidacao("Km final menor que inicial.")

        linhas = zip(f.getlist("produto_id"), f.getlist("nota_fiscal"), f.getlist("quantidade"), f.getlist("valor_nf"), f.getlist("valor_frete"))
        cargas = []
        for n, (produto_id, nota, qtd, valor_nf, frete) in enumerate(linhas, 1):
            if not (produto_id or nota.strip() or qtd.strip()): continue
            try:
                produto = buscar(db, "produtos", produto_id, "produto")
                quantidade = numero(qtd, "Quantidade", estrito=True)
                v_nf = numero_opcional(valor_nf, "Valor NF", quantidade * produto["valor_unit"])
                v_fr = numero_opcional(frete, "Frete", 0.0)
            except Exception as e: raise ErroValidacao(f"Carga {n}: {e}")
            cargas.append((produto["id"], texto(nota, "NF", 30), quantidade, round(quantidade * produto["peso_unit_kg"], 3), round(quantidade * produto["cubagem_unit_m3"], 4), round(v_nf, 2), round(v_fr, 2)))
        
        if not cargas: raise ErroValidacao("Informe pelo menos uma carga.")
        with db:
            cur = db.execute("INSERT INTO viagens (data, caminhao_id, motorista_id, km_inicial, km_final) VALUES (?, ?, ?, ?, ?)", (data, caminhao["id"], motorista["id"], km_inicial, km_final))
            db.executemany("INSERT INTO cargas (viagem_id, produto_id, nota_fiscal, quantidade, peso_kg, cubagem_m3, valor_nf, valor_frete) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [(cur.lastrowid, *c) for c in cargas])
        flash("Viagem salva com sucesso!", "ok")
    except Exception as erro: flash(str(erro), "erro")
    return voltar("viagens_page", "form-viagens")

# --- 4. ROTA MANUTENÇÕES ---
@app.get("/manutencao")
@login_required
def manutencao_page():
    db = get_db()
    lancamentos = db.execute("SELECT mn.id, mn.data, c.placa, m.nome AS motorista, mn.peca, mn.custo, mn.status FROM manutencoes mn JOIN caminhoes c ON c.id = mn.caminhao_id LEFT JOIN motoristas m ON m.id = mn.motorista_id ORDER BY mn.data DESC, mn.id DESC").fetchall()
    por_caminhao = db.execute("SELECT c.placa, COUNT(*) AS quantidade, SUM(mn.custo) AS custo FROM manutencoes mn JOIN caminhoes c ON c.id = mn.caminhao_id GROUP BY c.id ORDER BY custo DESC").fetchall()
    grafico = {
        "labels": [filtro_placa(r["placa"]) for r in por_caminhao],
        "custo": [r["custo"] for r in por_caminhao],
        "quantidade": [r["quantidade"] for r in por_caminhao],
    }
    return render_template(
        "resultados_manutencao.html",
        lancamentos=lancamentos, por_caminhao=por_caminhao, grafico=grafico,
        total_gasto=sum(r["custo"] for r in lancamentos), pendentes=sum(1 for r in lancamentos if r["status"] == "Pendente"),
        caminhoes=db.execute("SELECT * FROM caminhoes ORDER BY placa").fetchall(),
        motoristas=db.execute("SELECT * FROM motoristas ORDER BY nome").fetchall(),
        hoje=date.today().isoformat(), status_lista=STATUS_MANUTENCAO, pecas=PECAS_COMUNS
    )

@app.post("/manutencoes")
@login_required
def nova_manutencao():
    f = request.form
    db = get_db()
    try:
        data = data_iso(f.get("data"))
        caminhao = buscar(db, "caminhoes", f.get("caminhao_id"), "caminhão")
        mot_id = buscar(db, "motoristas", f.get("motorista_id"), "motorista")["id"] if f.get("motorista_id") else None
        peca = texto(f.get("peca"), "Peça", 80)
        custo = numero(f.get("custo"), "Custo")
        status = escolher_opcao(f.get("status"), STATUS_MANUTENCAO, "Status")
        with db: db.execute("INSERT INTO manutencoes (data, caminhao_id, motorista_id, peca, custo, status) VALUES (?, ?, ?, ?, ?, ?)", (data, caminhao["id"], mot_id, peca, round(custo, 2), status))
        flash(f"Preventiva registrada: {peca}.", "ok")
    except Exception as erro: flash(str(erro), "erro")
    return voltar("manutencao_page", "form-manutencao")

# --- 5. EXCLUSÃO ---
DESTINO_EXCLUSAO = {
    "caminhoes": "cadastros", "motoristas": "cadastros", "produtos": "cadastros",
    "viagens": "viagens_page", "manutencoes": "manutencao_page",
}
@app.post("/excluir/<tabela>/<int:registro_id>")
@login_required
def excluir(tabela, registro_id):
    if tabela not in DESTINO_EXCLUSAO: abort(404)
    db = get_db()
    try:
        with db: db.execute(f"DELETE FROM {tabela} WHERE id = ?", (registro_id,))
        flash("Registro excluído.", "ok")
    except sqlite3.IntegrityError: flash("Não é possível excluir um item que já possui histórico no sistema.", "erro")
    return voltar(DESTINO_EXCLUSAO[tabela])

def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")

iniciar_banco()

if __name__ == "__main__":
    Timer(1, abrir_navegador).start()
    # Forçamos o use_reloader=False para o terminal não limpar o ecrã e mostrar o erro completo
    app.run(debug=True, use_reloader=False, port=5000)
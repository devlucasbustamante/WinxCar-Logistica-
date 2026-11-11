from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
import unicodedata
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask, flash, g, redirect, render_template,
    request, session, url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "logistica.db")

# Senha e chave vêm do .env; se não existir .env, usa os valores padrão
SENHA_ADMIN = os.environ.get("SENHA_ADMIN") or "fatec2026"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "chave-local-logistica-fatec-2026"


# ============================================================
# BANCO (SQLite puro)
# ============================================================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    # Sempre roda: "IF NOT EXISTS" cria só o que faltar, então bancos
    # antigos também recebem as tabelas novas (ex.: viagem_cargas).
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS caminhoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa TEXT NOT NULL UNIQUE,
        categoria TEXT,
        potencia_cv INTEGER,
        eixos INTEGER,
        capacidade_kg REAL,
        cubagem_m3 REAL
    );
    CREATE TABLE IF NOT EXISTS motoristas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnh TEXT,
        telefone TEXT
    );
    CREATE TABLE IF NOT EXISTS notas_fiscais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_nf TEXT NOT NULL UNIQUE,
        descricao_carga TEXT,
        peso_total_kg REAL,
        volume_total_m3 REAL,
        valor_total REAL
    );
    CREATE TABLE IF NOT EXISTS viagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        caminhao_id INTEGER,
        motorista_id INTEGER,
        km_inicial REAL,
        km_final REAL,
        destino TEXT,
        cidade_uf TEXT,
        tempo_estimado REAL,
        status_viagem TEXT,
        valor_frete REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS manutencoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT,
        caminhao_id INTEGER,
        motorista_id INTEGER,
        peca TEXT,
        custo REAL,
        status TEXT,
        numero_os TEXT,
        empresa TEXT
    );
    -- Cargas (notas fiscais) de cada viagem.
    -- Peso/cubagem/valor são gravados no momento da viagem (histórico fiel),
    -- então excluir a NF depois não altera viagens antigas.
    CREATE TABLE IF NOT EXISTS viagem_cargas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viagem_id INTEGER NOT NULL REFERENCES viagens(id) ON DELETE CASCADE,
        nota_id INTEGER,
        numero_nf TEXT,
        quantidade REAL,
        peso_kg REAL,
        cubagem_m3 REAL,
        valor_nf REAL
    );
    """)
    db.commit()
    db.close()


init_db()


# ============================================================
# FILTROS JINJA
# ============================================================
def _to_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


@app.template_filter("slug")
def filtro_slug(v):
    """'Em andamento' -> 'em-andamento', 'Concluído' -> 'concluido' (para classes CSS)."""
    s = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode()
    return "-".join(s.lower().split())


@app.template_filter("placa")
def filtro_placa(v):
    if not v:
        return ""
    s = str(v).replace("-", "").replace(" ", "").upper()
    if len(s) == 7:
        return f"{s[:3]}-{s[3:]}"
    return str(v)


@app.template_filter("data_br")
def filtro_data_br(v):
    if not v:
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(v)


@app.template_filter("num")
def filtro_num(v, casas=0):
    if v is None:
        return "0"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    fmt = f"{{:,.{int(casas)}f}}"
    return fmt.format(n).replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("brl")
def filtro_brl(v):
    try:
        n = float(v or 0)
    except (TypeError, ValueError):
        n = 0
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


# ============================================================
# AUTENTICAÇÃO
# ============================================================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ============================================================
# HELPERS
# ============================================================
def _dicts(rows):
    return [dict(r) for r in rows]


def _caminhoes():
    return _dicts(get_db().execute(
        "SELECT * FROM caminhoes ORDER BY placa"
    ).fetchall())


def _motoristas():
    return _dicts(get_db().execute(
        "SELECT * FROM motoristas ORDER BY nome"
    ).fetchall())


def _notas():
    return _dicts(get_db().execute(
        "SELECT * FROM notas_fiscais ORDER BY numero_nf"
    ).fetchall())


# ============================================================
# ROTAS
# ============================================================

# 1. Rota Raiz (Força ir para o login ou para o dashboard)
@app.route("/")
def raiz():
    if not session.get("logado"):
        return redirect(url_for("login"))
    return redirect(url_for("home"))


# 2. Rota de Login (Apenas UMA vez)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("senha") == SENHA_ADMIN:
            session["logado"] = True
            flash("Bem-vindo!", "ok")
            return redirect(url_for("home"))
        flash("Senha incorreta.", "erro")
    return render_template("login.html")


# 3. Rota de Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada.", "ok")
    return redirect(url_for("login"))


# 4. Dashboard
@app.route("/dashboard")
@login_required
def home():
    db = get_db()
    totais = {
        "caminhoes": db.execute("SELECT COUNT(*) FROM caminhoes").fetchone()[0],
        "viagens": db.execute("SELECT COUNT(*) FROM viagens").fetchone()[0],
        "motoristas": db.execute("SELECT COUNT(*) FROM motoristas").fetchone()[0],
        "custo_manutencao": db.execute(
            "SELECT COALESCE(SUM(custo),0) FROM manutencoes"
        ).fetchone()[0],
    }
    return render_template("index.html", totais=totais)


# ---------------- Cadastros ----------------
@app.route("/cadastros")
@login_required
def cadastros():
    return render_template(
        "cadastros.html",
        caminhoes=_caminhoes(),
        motoristas=_motoristas(),
        notas_fiscais=_notas(),
        categorias=["Truck", "Carreta", "Bitrem", "VUC", "3/4"],
    )


@app.route("/caminhoes/novo", methods=["POST"])
@login_required
def novo_caminhao():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO caminhoes (placa, categoria, potencia_cv, eixos, capacidade_kg, cubagem_m3) "
            "VALUES (?,?,?,?,?,?)",
            (
                request.form["placa"].upper().replace("-", "").strip(),
                request.form["categoria"],
                request.form.get("potencia_cv"),
                request.form.get("eixos"),
                request.form.get("capacidade_kg"),
                request.form.get("cubagem_m3"),
            ),
        )
        db.commit()
        flash("Caminhão cadastrado.", "ok")
    except sqlite3.IntegrityError:
        flash("Placa já cadastrada.", "erro")
    except Exception as e:
        flash(f"Erro ao cadastrar: {e}", "erro")
    return redirect(url_for("cadastros"))


@app.route("/motoristas/novo", methods=["POST"])
@login_required
def novo_motorista():
    nome = (request.form.get("nome") or "").strip()
    if not nome:
        flash("Informe o nome do motorista.", "erro")
        return redirect(url_for("cadastros"))
    db = get_db()
    db.execute(
        "INSERT INTO motoristas (nome, cnh, telefone) VALUES (?,?,?)",
        (nome, request.form.get("cnh"), request.form.get("telefone")),
    )
    db.commit()
    flash("Motorista cadastrado.", "ok")
    return redirect(url_for("cadastros"))


@app.route("/notas/nova", methods=["POST"])
@login_required
def nova_nota():
    db = get_db()
    try:
        db.execute(
            "INSERT INTO notas_fiscais "
            "(numero_nf, descricao_carga, peso_total_kg, volume_total_m3, valor_total) "
            "VALUES (?,?,?,?,?)",
            (
                request.form["numero_nf"],
                request.form["descricao_carga"],
                request.form.get("peso_total_kg"),
                request.form.get("volume_total_m3"),
                request.form.get("valor_total"),
            ),
        )
        db.commit()
        flash("Nota fiscal cadastrada.", "ok")
    except sqlite3.IntegrityError:
        flash("Número de NF já cadastrado.", "erro")
    return redirect(url_for("cadastros"))


@app.route("/excluir/<tabela>/<int:registro_id>", methods=["POST"])
@login_required
def excluir(tabela, registro_id):
    destinos = {
        "caminhoes": "cadastros",
        "motoristas": "cadastros",
        "notas_fiscais": "cadastros",
        "manutencoes": "manutencao_page",
        "viagens": "viagens_page",
    }
    if tabela not in destinos:
        flash("Tabela inválida.", "erro")
        return redirect(url_for("home"))

    db = get_db()

    # Não deixa apagar caminhão/motorista que já tem viagem ou manutenção,
    # senão o histórico ficaria com registros "órfãos" (sem placa/nome).
    vinculos = {
        "caminhoes": "caminhao_id",
        "motoristas": "motorista_id",
    }
    if tabela in vinculos:
        col = vinculos[tabela]
        usos = (
            db.execute(f"SELECT COUNT(*) FROM viagens WHERE {col} = ?", (registro_id,)).fetchone()[0]
            + db.execute(f"SELECT COUNT(*) FROM manutencoes WHERE {col} = ?", (registro_id,)).fetchone()[0]
        )
        if usos:
            flash(
                "Não é possível excluir: existem viagens ou manutenções ligadas a este registro. "
                "Exclua-as primeiro.", "erro",
            )
            return redirect(url_for(destinos[tabela]))

    if tabela == "viagens":
        db.execute("DELETE FROM viagem_cargas WHERE viagem_id = ?", (registro_id,))
    db.execute(f"DELETE FROM {tabela} WHERE id = ?", (registro_id,))
    db.commit()
    flash("Registro excluído.", "ok")
    return redirect(url_for(destinos[tabela]))


# ---------------- Viagens ----------------
def _salvar_viagem(db):
    """Valida e grava a viagem + suas cargas (notas fiscais)."""
    f = request.form
    voltar = redirect(url_for("viagens_page"))

    caminhao = db.execute(
        "SELECT * FROM caminhoes WHERE id = ?", (f.get("caminhao"),)
    ).fetchone()
    motorista = db.execute(
        "SELECT id FROM motoristas WHERE id = ?", (f.get("motorista"),)
    ).fetchone()
    if not caminhao or not motorista:
        flash("Selecione um caminhão e um motorista válidos.", "erro")
        return voltar

    km_i = _to_float(f.get("km_inicial"))
    km_f = _to_float(f.get("km_final"))
    if km_f < km_i:
        flash("O km final não pode ser menor que o km inicial.", "erro")
        return voltar

    # Cada bloco de carga envia produto_id, quantidade e valor_nf (listas paralelas)
    notas = {str(n["id"]): n for n in _notas()}
    cargas = []
    for prod_id, qtd, valor in zip(
        f.getlist("produto_id"), f.getlist("quantidade"), f.getlist("valor_nf")
    ):
        if not prod_id:
            continue
        nota = notas.get(prod_id)
        qtd = _to_float(qtd)
        if not nota or qtd <= 0:
            flash("Há uma carga com nota fiscal ou quantidade inválida.", "erro")
            return voltar
        cargas.append({
            "nota_id": nota["id"],
            "numero_nf": nota["numero_nf"],
            "quantidade": qtd,
            "peso_kg": _to_float(nota["peso_total_kg"]) * qtd,
            "cubagem_m3": _to_float(nota["volume_total_m3"]) * qtd,
            "valor_nf": _to_float(valor, _to_float(nota["valor_total"])),
        })

    if not cargas:
        flash("Adicione pelo menos uma carga (nota fiscal) à viagem.", "erro")
        return voltar

    # Verificação de capacidade também no servidor (não só na tela)
    peso = sum(c["peso_kg"] for c in cargas)
    cub = sum(c["cubagem_m3"] for c in cargas)
    cap_peso = _to_float(caminhao["capacidade_kg"])
    cap_cub = _to_float(caminhao["cubagem_m3"])
    if (cap_peso and peso > cap_peso) or (cap_cub and cub > cap_cub):
        flash(
            f"Capacidade excedida: {filtro_num(peso)} kg / {filtro_num(cub, 2)} m³ "
            f"para um caminhão de {filtro_num(cap_peso)} kg / {filtro_num(cap_cub, 2)} m³.",
            "erro",
        )
        return voltar

    cur = db.execute(
        "INSERT INTO viagens (data, caminhao_id, motorista_id, km_inicial, km_final, "
        "destino, cidade_uf, tempo_estimado, status_viagem, valor_frete) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            f.get("data"),
            caminhao["id"],
            motorista["id"],
            km_i,
            km_f,
            f.get("destino"),
            f.get("cidade_uf"),
            f.get("tempo_estimado") or None,
            f.get("status"),
            _to_float(f.get("valor_frete")),
        ),
    )
    viagem_id = cur.lastrowid
    db.executemany(
        "INSERT INTO viagem_cargas (viagem_id, nota_id, numero_nf, quantidade, "
        "peso_kg, cubagem_m3, valor_nf) VALUES (?,?,?,?,?,?,?)",
        [
            (viagem_id, c["nota_id"], c["numero_nf"], c["quantidade"],
             c["peso_kg"], c["cubagem_m3"], c["valor_nf"])
            for c in cargas
        ],
    )
    db.commit()
    flash(f"Viagem registrada com {len(cargas)} carga(s).", "ok")
    return redirect(url_for("viagens_page", dia=f.get("data")))


@app.route("/viagens", methods=["GET", "POST"])
@login_required
def viagens_page():
    db = get_db()

    if request.method == "POST":
        return _salvar_viagem(db)

    dia = request.args.get("dia") or date.today().isoformat()

    # Soma das cargas por viagem (subconsulta evita contar a viagem em dobro)
    cargas_por_viagem = (
        "SELECT viagem_id, SUM(peso_kg) AS peso_kg, SUM(valor_nf) AS valor_nf "
        "FROM viagem_cargas GROUP BY viagem_id"
    )

    resumo_row = db.execute(
        f"""
        SELECT COUNT(*) AS viagens,
               COALESCE(SUM(v.km_final - v.km_inicial), 0) AS km,
               COALESCE(SUM(vc.peso_kg), 0) AS peso_kg,
               COALESCE(SUM(v.valor_frete), 0) AS valor_frete
        FROM viagens v
        LEFT JOIN ({cargas_por_viagem}) vc ON vc.viagem_id = v.id
        WHERE v.data = ?
        """, (dia,)
    ).fetchone()
    resumo_dia = dict(resumo_row)

    ultimas = _dicts(db.execute(
        f"""
        SELECT v.id, v.data, v.km_final - v.km_inicial AS km,
               COALESCE(vc.peso_kg, 0) AS peso_kg,
               COALESCE(vc.valor_nf, 0) AS valor_nf,
               v.valor_frete, v.status_viagem, v.destino, v.cidade_uf,
               c.placa, m.nome AS motorista
        FROM viagens v
        LEFT JOIN ({cargas_por_viagem}) vc ON vc.viagem_id = v.id
        LEFT JOIN caminhoes c ON c.id = v.caminhao_id
        LEFT JOIN motoristas m ON m.id = v.motorista_id
        ORDER BY v.data DESC, v.id DESC
        LIMIT 30
        """
    ).fetchall())

    km_por_caminhao = db.execute(
        """
        SELECT c.placa, SUM(v.km_final - v.km_inicial) AS km
        FROM viagens v JOIN caminhoes c ON c.id = v.caminhao_id
        GROUP BY c.id ORDER BY km DESC
        """
    ).fetchall()
    peso_por_motorista = db.execute(
        f"""
        SELECT m.nome, COALESCE(SUM(vc.peso_kg), 0) AS peso
        FROM viagens v
        JOIN motoristas m ON m.id = v.motorista_id
        LEFT JOIN ({cargas_por_viagem}) vc ON vc.viagem_id = v.id
        GROUP BY m.id ORDER BY peso DESC
        """
    ).fetchall()

    grafico = {
        "caminhoes": {
            "labels": [filtro_placa(r["placa"]) for r in km_por_caminhao],
            "km": [_to_float(r["km"]) for r in km_por_caminhao],
        },
        "motoristas": {
            "labels": [r["nome"] for r in peso_por_motorista],
            "peso": [_to_float(r["peso"]) for r in peso_por_motorista],
        },
    }

    produtos = {
        str(n["id"]): {
            "peso_kg": _to_float(n["peso_total_kg"]),
            "cubagem_m3": _to_float(n["volume_total_m3"]),
            "valor_nf": _to_float(n["valor_total"]),
        }
        for n in _notas()
    }

    caminhoes_lista = _caminhoes()
    capacidades = {
        str(c["id"]): {
            "peso": _to_float(c.get("capacidade_kg"), 0),
            "cub": _to_float(c.get("cubagem_m3"), 0),
        }
        for c in caminhoes_lista
    }

    primeiro = caminhoes_lista[0] if caminhoes_lista else None
    capacidade_peso_fallback = _to_float(primeiro.get("capacidade_kg"), 0) if primeiro else 0
    capacidade_cub_fallback = _to_float(primeiro.get("cubagem_m3"), 0) if primeiro else 0

    return render_template(
        "resultados_viagens.html",
        caminhoes=caminhoes_lista,
        motoristas=_motoristas(),
        produtos=_notas(),
        produtos_json=produtos,
        capacidade_peso=capacidade_peso_fallback,
        capacidade_cub=capacidade_cub_fallback,
        capacidades_json=capacidades,
        dia=dia,
        hoje=date.today().isoformat(),
        resumo_dia=resumo_dia,
        ultimas=ultimas,
        grafico=grafico,
    )


# ---------------- Manutenção ----------------
@app.route("/manutencao", methods=["GET"])
@login_required
def manutencao_page():
    db = get_db()
    lancamentos = _dicts(db.execute(
        """
        SELECT mn.*, c.placa, m.nome AS motorista
        FROM manutencoes mn
        LEFT JOIN caminhoes c ON c.id = mn.caminhao_id
        LEFT JOIN motoristas m ON m.id = mn.motorista_id
        ORDER BY mn.data DESC, mn.id DESC
        """
    ).fetchall())

    total_gasto = sum(_to_float(l["custo"]) for l in lancamentos)
    pendentes = sum(1 for l in lancamentos if l["status"] == "Pendente")
    fornecedores = sorted({l["empresa"] for l in lancamentos if l["empresa"]})

    return render_template(
        "resultados_manutencao.html",
        caminhoes=_caminhoes(),
        motoristas=_motoristas(),
        pecas=["Pneu", "Pastilha de Freio", "Óleo", "Filtro", "Correia"],
        status_lista=["Concluído", "Pendente", "Em andamento"],
        hoje=date.today().isoformat(),
        lancamentos=lancamentos,
        total_gasto=total_gasto,
        pendentes=pendentes,
        fornecedores=fornecedores,
    )


@app.route("/manutencao/nova", methods=["POST"])
@login_required
def nova_manutencao():
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM caminhoes WHERE id = ?", (request.form.get("caminhao_id"),)
    ).fetchone():
        flash("Selecione um caminhão válido.", "erro")
        return redirect(url_for("manutencao_page"))
    db.execute(
        "INSERT INTO manutencoes (data, caminhao_id, motorista_id, peca, custo, "
        "status, numero_os, empresa) VALUES (?,?,?,?,?,?,?,?)",
        (
            request.form.get("data"),
            request.form.get("caminhao_id"),
            request.form.get("motorista_id") or None,
            request.form.get("peca"),
            request.form.get("custo"),
            request.form.get("status"),
            request.form.get("numero_os"),
            request.form.get("empresa"),
        ),
    )
    db.commit()
    flash("Manutenção registrada.", "ok")
    return redirect(url_for("manutencao_page"))


if __name__ == '__main__':
    print("\n  Sistema rodando! Abra no navegador:  http://127.0.0.1:5001")
    print("  Para parar o servidor: Ctrl + C\n")
    app.run(port=5001, debug=True)

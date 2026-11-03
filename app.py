"""Painel de Logística - Fase 1 (Arquitetura com Supabase)"""
import math
import os
import re
from datetime import date, datetime
from functools import wraps
from threading import Timer
import webbrowser

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave-padrao-insegura")

SUPABASE_URL = "https://cuvmgpcttdqhdtlycebn.supabase.co"
SUPABASE_KEY = "sb_publishable_alJE7NLcKgZJa_9jVsSDzQ_ZAcKHqBn"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


CATEGORIAS = ["VUC", "3/4", "Toco", "Truck", "Bitruck", "Carreta", "Bitrem", "Rodotrem"]
STATUS_MANUTENCAO = ["Trocado", "Revisado", "Reparado", "Pendente"]
PECAS_COMUNS = [
    "Pneu", "Pastilha de freio", "Lona de freio", "Óleo do motor", "Filtro de óleo",
    "Filtro de ar", "Filtro de combustível", "Correia", "Bateria", "Amortecedor", "Embreagem",
]

class ErroValidacao(Exception):
    pass

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

# ---------------------------------------------------------------------------
# Funções de validação e utilitários
# ---------------------------------------------------------------------------
def texto(valor, campo, max_len=80, obrigatorio=True):
    t = " ".join((valor or "").split())
    if obrigatorio and not t:
        raise ErroValidacao(f"Preencha o campo «{campo}».")
    if len(t) > max_len:
        raise ErroValidacao(f"«{campo}» aceita no máximo {max_len} caracteres.")
    return t

def numero(valor, campo, minimo=0.0, estrito=False):
    t = (valor or "").strip().replace(",", ".")
    if not t:
        raise ErroValidacao(f"Preencha o campo «{campo}».")
    try:
        n = float(t)
    except ValueError:
        raise ErroValidacao(f"«{campo}» precisa ser um número.")
    if not math.isfinite(n):
        raise ErroValidacao(f"«{campo}» tem valor inválido.")
    if estrito and n <= minimo:
        raise ErroValidacao(f"«{campo}» precisa ser maior que {minimo:g}.")
    if not estrito and n < minimo:
        raise ErroValidacao(f"«{campo}» não pode ser menor que {minimo:g}.")
    return n

def numero_opcional(valor, campo, padrao):
    if not (valor or "").strip():
        return padrao
    return numero(valor, campo)

def inteiro(valor, campo, minimo=1):
    n = numero(valor, campo, minimo)
    if n != int(n):
        raise ErroValidacao(f"«{campo}» precisa ser inteiro.")
    return int(n)

def normalizar_placa(valor):
    placa = re.sub(r"[\s\-]", "", (valor or "").upper())
    if not re.fullmatch(r"[A-Z]{3}\d[A-Z0-9]\d{2}", placa):
        raise ErroValidacao("Placa inválida. Use ABC-1234 ou ABC1D23.")
    return placa

def data_iso(valor, campo="Data"):
    try:
        return datetime.strptime((valor or "").strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ErroValidacao(f"«{campo}» inválida.")

def escolher_opcao(valor, opcoes, campo):
    if valor not in opcoes:
        raise ErroValidacao(f"Escolha opção válida em «{campo}».")
    return valor

def buscar_registro(tabela, valor, rotulo):
    try:
        registro_id = int(valor)
    except (TypeError, ValueError):
        raise ErroValidacao(f"Escolha {rotulo}.")
    res = supabase.table(tabela).select("*").eq("id", registro_id).execute()
    if not res.data:
        raise ErroValidacao(f"Não encontrei {rotulo}.")
    return res.data[0]

def fmt_num(valor, casas=0):
    s = f"{(valor or 0):,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

@app.template_filter("num")
def filtro_num(valor, casas=0):
    return fmt_num(valor, casas)

@app.template_filter("brl")
def filtro_brl(valor):
    return "R$ " + fmt_num(valor, 2)

@app.template_filter("placa")
def filtro_placa(valor):
    if valor and re.fullmatch(r"[A-Z]{3}\d{4}", valor):
        return f"{valor[:3]}-{valor[3:]}"
    return valor

@app.template_filter("data_br")
def filtro_data_br(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return valor

@app.template_filter("faixa")
def filtro_faixa(percentual):
    if percentual > 100:
        return "excesso"
    if percentual >= 90:
        return "alerta"
    return "ok"

def percentual(valor, capacidade):
    return (valor / capacidade * 100) if capacidade else 0.0

def voltar(rota_destino, ancora=""):
    url = url_for(rota_destino)
    if ancora:
        url += "#" + ancora
    return redirect(url)

# ---------------------------------------------------------------------------
# Funções de acesso ao Supabase
# ---------------------------------------------------------------------------
def buscar_caminhoes():
    return supabase.table("caminhoes").select("*").order("placa").execute().data or []

def buscar_motoristas():
    return supabase.table("motoristas").select("*").order("nome").execute().data or []

def buscar_notas():
    return supabase.table("notas_fiscais").select("*").order("numero_nf").execute().data or []

def buscar_produtos():
    return supabase.table("produtos").select("*").order("nome").execute().data or []

def buscar_viagens_view(limit=30):
    return supabase.table("vw_viagens").select("*").order("data", desc=True).limit(limit).execute().data or []

def buscar_manutencoes():
    return supabase.table("manutencoes").select("*").order("data", desc=True).order("id", desc=True).execute().data or []

# --- 1. ROTA DASHBOARD INICIAL ---
@app.get("/")
@login_required
def home():
    caminhoes = supabase.table("caminhoes").select("id").execute().data or []
    motoristas = supabase.table("motoristas").select("id").execute().data or []
    viagens = supabase.table("viagens").select("id").execute().data or []
    manutencoes = supabase.table("manutencoes").select("custo").execute().data or []

    totais = {
        "caminhoes": len(caminhoes),
        "motoristas": len(motoristas),
        "viagens": len(viagens),
        "custo_manutencao": sum(m.get("custo", 0) for m in manutencoes),
    }
    return render_template("index.html", totais=totais)

# --- 2. ROTA CADASTRAR/LISTAR ENTIDADES ---
@app.get("/cadastros")
@login_required
def cadastros():
    caminhoes = buscar_caminhoes()
    motoristas = buscar_motoristas()
    notas_fiscais = buscar_notas()
    return render_template(
        "cadastros.html",
        caminhoes=caminhoes,
        motoristas=motoristas,
        notas_fiscais=notas_fiscais,
        categorias=CATEGORIAS,
        status_manutencao=STATUS_MANUTENCAO,
        pecas_comuns=PECAS_COMUNS
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

        dados = {
            "placa": placa,
            "potencia_cv": potencia,
            "eixos": eixos,
            "categoria": categoria,
            "capacidade_kg": capacidade,
            "cubagem_m3": cubagem,
        }
        supabase.table("caminhoes").insert(dados).execute()
        flash(f"Caminhão {filtro_placa(placa)} cadastrado.", "ok")
    except Exception as erro:
        flash(str(erro), "erro")
    return voltar("cadastros", "caminhoes")

@app.post("/motoristas")
@login_required
def novo_motorista():
    f = request.form
    try:
        nome = texto(f.get("nome"), "Nome", 80)
        cnh = texto(f.get("cnh"), "CNH", 20, False)
        telefone = texto(f.get("telefone"), "Telefone", 20, False)

        dados = {
            "nome": nome,
            "cnh": cnh or None,
            "telefone": telefone or None,
        }
        supabase.table("motoristas").insert(dados).execute()
        flash(f"Motorista {nome} cadastrado.", "ok")
    except Exception as erro:
        flash(str(erro), "erro")
    return voltar("cadastros", "motoristas")

@app.post("/nova_nota")
@login_required
def nova_nota():
    f = request.form
    try:
        numero_nf = texto(f.get("numero_nf"), "Número da NF", 20)
        descricao = texto(f.get("descricao_carga"), "Descrição da carga", 120)
        peso = numero(f.get("peso_total_kg"), "Peso total", estrito=True)
        volume = numero(f.get("volume_total_m3"), "Volume total", estrito=True)
        valor = numero(f.get("valor_total"), "Valor total")

        dados = {
            "numero_nf": numero_nf,
            "descricao_carga": descricao,
            "peso_total_kg": peso,
            "volume_total_m3": volume,
            "valor_total": round(valor, 2),
        }
        supabase.table("notas_fiscais").insert(dados).execute()
        flash(f"Nota Fiscal {numero_nf} cadastrada com sucesso.", "ok")
    except Exception as erro:
        flash(str(erro), "erro")
    return voltar("cadastros", "notas")

# ---------------------------------------------------------------------------
# Rota de Viagens
# ---------------------------------------------------------------------------
@app.get("/viagens")
@login_required
def viagens_page():
    try:
        dia = data_iso(request.args.get("data"))
    except ErroValidacao:
        dia = date.today().isoformat()

    caminhoes = buscar_caminhoes()
    motoristas = buscar_motoristas()
    produtos = buscar_produtos()
    ultimas_view = buscar_viagens_view(limit=30)

    capacidade_peso = caminhoes[0]["capacidade_kg"] if caminhoes else 0
    capacidade_cub = caminhoes[0]["cubagem_m3"] if caminhoes else 0

    produtos_js = {
        str(p["id"]): {
            "peso_kg": float(p["peso_kg"]),
            "cubagem_m3": float(p["cubagem_m3"]),
            "valor_nf": float(p["valor_nf"]),
        }
        for p in produtos
    }

    dados_js = {
        "produtos": produtos_js,
        "capacidade_peso": float(capacidade_peso),
        "capacidade_cub": float(capacidade_cub),
    }

    resumo_dia_viagens = [v for v in ultimas_view if v.get("data") == dia]
    resumo_dia = {
        "viagens": len(resumo_dia_viagens),
        "km": sum(v.get("km", 0) for v in resumo_dia_viagens),
        "peso_kg": sum(v.get("peso_kg", 0) for v in resumo_dia_viagens),
        "valor_frete": sum(v.get("valor_frete", 0) for v in resumo_dia_viagens),
    }

    ultimas = []
    for v in ultimas_view:
        cap_peso = v.get("capacidade_kg") or 0
        pct_peso = percentual(v.get("peso_kg", 0), cap_peso) if cap_peso else 0
        ultimas.append({
            "id": v["id"],
            "data": v["data"],
            "placa": v["placa"],
            "motorista": v["motorista"],
            "km": v.get("km", 0),
            "peso_kg": v.get("peso_kg", 0),
            "pct_peso": pct_peso,
            "valor_nf": v.get("valor_nf", 0),
            "valor_frete": v.get("valor_frete", 0),
        })

    grafico = {
        "caminhoes": {"labels": [], "km": []},
        "motoristas": {"labels": [], "peso": []},
    }

    return render_template(
        "viagens_page.html",
        dia=dia,
        caminhoes=caminhoes,
        motoristas=motoristas,
        produtos=produtos,
        ultimas=ultimas,
        resumo_dia=resumo_dia,
        grafico=grafico,
        dados_js=dados_js,
        hoje=date.today().isoformat(),
    )

@app.post("/viagens")
@login_required
def nova_viagem():
    f = request.form
    try:
        data_v = data_iso(f.get("data"))
        caminhao = buscar_registro("caminhoes", f.get("caminhao_id"), "caminhão")
        motorista = buscar_registro("motoristas", f.get("motorista_id"), "motorista")
        km_inicial = numero(f.get("km_inicial"), "Km inicial")
        km_final = numero(f.get("km_final"), "Km final")
        if km_final < km_inicial:
            raise ErroValidacao("Km final menor que inicial.")

        dados_viagem = {
            "data": data_v,
            "caminhao_id": caminhao["id"],
            "motorista_id": motorista["id"],
            "km_inicial": km_inicial,
            "km_final": km_final,
            "destino_empresa": f.get("destino_empresa"),
            "destino_cidade": f.get("destino_cidade"),
            "tempo_estimado": numero_opcional(f.get("tempo_estimado"), "Tempo estimado", 0.0),
            "status_viagem": f.get("status_viagem") or "Concluída",
        }

        res = supabase.table("viagens").insert(dados_viagem).execute()
        viagem_id = res.data[0]["id"]

        produtos_ids = f.getlist("produto_id")
        notas = f.getlist("nota_fiscal")
        quantidades = f.getlist("quantidade")
        valores_nf = f.getlist("valor_nf")
        valores_frete = f.getlist("valor_frete")

        cargas = []
        for i in range(len(produtos_ids)):
            if not produtos_ids[i]:
                continue
            carga = {
                "viagem_id": viagem_id,
                "produto_id": int(produtos_ids[i]),
                "nota_fiscal": notas[i],
                "quantidade": float(quantidades[i] or 0),
                "valor_nf": float(valores_nf[i] or 0),
                "valor_frete": float(valores_frete[i] or 0),
            }
            cargas.append(carga)

        if not cargas:
            raise ErroValidacao("Informe pelo menos uma carga.")

        supabase.table("cargas").insert(cargas).execute()
        flash("Viagem salva com sucesso!", "ok")
    except Exception as erro:
        flash(str(erro), "erro")
    return voltar("viagens_page", "form-viagens")

# --- 4. ROTA MANUTENÇÕES ---
@app.get("/manutencao")
@login_required
def manutencao_page():
    lancamentos_raw = buscar_manutencoes()
    caminhoes = buscar_caminhoes()
    motoristas = buscar_motoristas()

    mapa_caminhao = {c["id"]: c for c in caminhoes}
    mapa_motorista = {m["id"]: m for m in motoristas}

    lancamentos = []
    for mn in lancamentos_raw:
        cam = mapa_caminhao.get(mn["caminhao_id"])
        mot = mapa_motorista.get(mn.get("motorista_id")) if mn.get("motorista_id") else None
        lancamentos.append({
            "id": mn["id"],
            "data": mn["data"],
            "placa": cam["placa"] if cam else "",
            "motorista": mot["nome"] if mot else None,
            "peca": mn["peca"],
            "custo": mn["custo"],
            "status": mn["status"],
        })

    por_caminhao = {}
    for mn in lancamentos:
        placa = mn["placa"]
        if placa not in por_caminhao:
            por_caminhao[placa] = {"placa": placa, "quantidade": 0, "custo": 0.0}
        por_caminhao[placa]["quantidade"] += 1
        por_caminhao[placa]["custo"] += mn["custo"]

    por_caminhao_lista = sorted(por_caminhao.values(), key=lambda x: x["custo"], reverse=True)

    grafico = {
        "labels": [filtro_placa(r["placa"]) for r in por_caminhao_lista],
        "custo": [r["custo"] for r in por_caminhao_lista],
        "quantidade": [r["quantidade"] for r in por_caminhao_lista],
    }

    total_gasto = sum(r["custo"] for r in lancamentos)
    pendentes = sum(1 for r in lancamentos if r["status"] == "Pendente")

    return render_template(
        "manutencao_page.html",
        lancamentos=lancamentos,
        por_caminhao=por_caminhao_lista,
        grafico=grafico,
        total_gasto=total_gasto,
        pendentes=pendentes,
        caminhoes=caminhoes,
        motoristas=motoristas,
        hoje=date.today().isoformat(),
        status_lista=STATUS_MANUTENCAO,
        pecas=PECAS_COMUNS,
    )

@app.post("/manutencoes")
@login_required
def nova_manutencao():
    f = request.form
    try:
        data_m = data_iso(f.get("data"))
        caminhao = buscar_registro("caminhoes", f.get("caminhao_id"), "caminhão")
        mot_id = buscar_registro("motoristas", f.get("motorista_id"), "motorista")["id"] if f.get("motorista_id") else None
        peca = texto(f.get("peca"), "Peça", 80)
        custo = numero(f.get("custo"), "Custo")
        status = escolher_opcao(f.get("status"), STATUS_MANUTENCAO, "Status")

        dados = {
            "data": data_m,
            "caminhao_id": caminhao["id"],
            "motorista_id": mot_id,
            "peca": peca,
            "custo": round(custo, 2),
            "status": status,
        }
        supabase.table("manutencoes").insert(dados).execute()
        flash(f"Preventiva registrada: {peca}.", "ok")
    except Exception as erro:
        flash(str(erro), "erro")
    return voltar("manutencao_page", "form-manutencao")

# --- 5. EXCLUSÃO ---
DESTINO_EXCLUSAO = {
    "caminhoes": "cadastros",
    "motoristas": "cadastros",
    "notas_fiscais": "cadastros",
    "viagens": "viagens_page",
    "manutencoes": "manutencao_page",
}

@app.post("/excluir/<tabela>/<int:registro_id>")
@login_required
def excluir(tabela, registro_id):
    if tabela not in DESTINO_EXCLUSAO:
        abort(404)
    try:
        supabase.table(tabela).delete().eq("id", registro_id).execute()
        flash("Registro excluído.", "ok")
    except Exception:
        flash("Não é possível excluir um item que já possui histórico no sistema.", "erro")
    return voltar(DESTINO_EXCLUSAO[tabela])

def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, abrir_navegador).start()
    app.run(debug=True, use_reloader=False, port=5000)

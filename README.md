# 🚚 Winxcar Logística: Sistema de Gestão de Frota

Sistema web de gestão de frota feito em **Flask + SQLite** para a **Fatec**. Ele cobre:

- Cadastro de caminhões, motoristas e notas fiscais
- Registro de viagens com **várias cargas (notas fiscais)** por viagem
- Controle de ocupação (peso e cubagem) em tempo real
- Manutenção preventiva com custos e fornecedores
- Dashboard com KPIs e metas ESG/ODS (ODS 3, 8, 9, 12 e 13)

---

## ▶️ Como rodar (passo a passo)

### Pré-requisito (uma única vez)

Ter o **Python 3.10 ou superior** instalado → https://www.python.org/downloads/
> Na instalação, marque a caixa **"Add python.exe to PATH"**.

### Opção A: Dois cliques (Windows, recomendado)

1. Baixe o projeto: no GitHub, clique em **Code → Download ZIP** e extraia o arquivo (ou use `git clone`).
2. Abra a pasta do projeto.
3. Dê **dois cliques em `iniciar.bat`**.
4. Aguarde. Na primeira vez ele instala o Flask (cerca de 1 minuto, precisa de internet) e **preenche o banco com dados fictícios**.
5. O navegador abre sozinho em **http://127.0.0.1:5001**.
6. Entre com a senha **`fatec2026`**.

> Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo**. O aviso aparece porque o arquivo veio da internet.

Para encerrar, feche a janela preta ou pressione `Ctrl + C` nela.

### Opção B: Pelo terminal (Windows / Linux / macOS)

Abra o terminal **dentro da pasta do projeto** e rode:

```bash
# 1. Criar o ambiente virtual (só na primeira vez)
python -m venv .venv

# 2. Ativar o ambiente
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

# 3. Instalar as dependências (só na primeira vez)
pip install -r requirements.txt

# 4. Preencher o banco com dados fictícios (só na primeira vez)
python popular_dados.py

# 5. Iniciar o sistema
python app.py
```

Nas próximas vezes, basta repetir os passos **2** e **5**.

Depois acesse **http://127.0.0.1:5001** e entre com a senha **`fatec2026`**.

> **Se o PowerShell bloquear o `activate`**, rode antes:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

---

## 🎲 Banco de dados e dados de demonstração

O banco é **local**: um arquivo SQLite chamado `logistica.db`, criado automaticamente na pasta do projeto. Ele **não** vem do GitHub, porque cada computador gera o seu.

Para testar com dados prontos, o projeto tem dados **fictícios**: 6 caminhões, 6 motoristas, 12 notas fiscais, 28 viagens e 10 manutenções. As datas são calculadas a partir do dia em que os dados são gerados, então sempre há viagens "de hoje" no Resumo do Dia.

| Quero… | Como fazer |
|---|---|
| **Ter os dados fictícios** | `iniciar.bat`: automático, sempre que o banco estiver vazio. Pelo terminal: `python popular_dados.py` |
| **Recarregar os dados fictícios do zero** | `python popular_dados.py --limpar` ⚠️ **apaga tudo** o que foi cadastrado e insere os dados fictícios de novo |
| **Começar com o sistema totalmente vazio** | Feche o sistema e apague o arquivo `logistica.db`. Pelo terminal, rode `python app.py` (cria um banco vazio). Pelo `iniciar.bat`, o banco vazio é preenchido de novo com os dados fictícios |

> Os comandos `python ...` devem ser rodados **dentro da pasta do projeto, com o ambiente virtual ativo** (passo 2 da Opção B).
> `popular_dados.py` sem `--limpar` **nunca apaga nada**: se o banco já tiver dados, ele não faz nada.

---

## 🧪 Roteiro rápido de teste

1. **Início** → veja os totais da frota e os cards ESG/ODS.
2. **Cadastros** → veja os caminhões, motoristas e notas fiscais, e cadastre um novo.
3. **Viagens** → registre uma viagem e adicione cargas (notas fiscais). A barra de ocupação muda de cor:
   - **laranja** acima de 85%
   - **vermelha** acima de 100%, e nesse caso o sistema **não deixa salvar**

   Dica: escolha o caminhão **VUC (RTA-7D88, 3.500 kg)** e adicione a NF de **aço (6.500 kg)** para ver o bloqueio.
4. Na mesma tela, veja o **Resumo do Dia** (filtre outras datas), os **gráficos** e o **histórico**.
5. **Manutenção** → lance uma preventiva e confira os indicadores.
6. Tente **excluir um caminhão que tem viagens**: o sistema impede, para proteger o histórico.

---

## 🔧 Problemas comuns

| Problema | Solução |
|---|---|
| `python` não é reconhecido | Reinstale o Python marcando **"Add python.exe to PATH"** |
| `No module named flask` | O ambiente virtual não está ativo: rode o passo 2 e depois o 3 |
| Erro na pasta `.venv` (`did not find executable`) | A `.venv` veio de outro computador. Apague a pasta `.venv` e repita os passos (o `iniciar.bat` faz isso sozinho) |
| Porta 5001 ocupada | Feche a outra janela do sistema que estiver aberta |
| Esqueci a senha | A padrão é `fatec2026`. Se existir um arquivo `.env`, vale a senha que está nele |
| Sistema abriu sem nenhum dado | Rode `python popular_dados.py` (veja a seção de banco de dados) |

---

## ✨ Funcionalidades

### 🔐 Autenticação
- Login com senha de administrador (padrão `fatec2026`; pode ser trocada no `.env`)
- Todas as telas exigem login; há logout com limpeza de sessão

### 📁 Cadastros Base
- **Caminhões**: placa, categoria, potência, eixos, capacidade (kg) e cubagem (m³)
- **Motoristas**: nome, CNH e telefone
- **Notas Fiscais**: número, descrição, peso, volume e valor
- Placa e número de NF não podem se repetir
- Não é possível excluir caminhão ou motorista que já tenha viagens ou manutenções

### 🛣️ Gestão de Viagens
- Data, caminhão, motorista, km inicial/final, destino, cidade/UF, tempo estimado, **valor do frete** e status
- **Várias cargas por viagem**: peso e cubagem = valores da NF × quantidade
- **Barra de ocupação em tempo real**, recalculada ao trocar de caminhão
- Validações na tela **e no servidor**: capacidade, km final ≥ km inicial e pelo menos uma carga
- Resumo diário (viagens, km, carga movida e frete), filtrável por data
- Gráficos (Chart.js) de km por caminhão e carga por motorista
- Histórico das últimas 30 viagens, com exclusão

### 🔧 Manutenção Preventiva
- Registro de serviços (peça, custo, status, nº da OS e empresa)
- KPIs: custo total, pendentes, total de serviços e número de fornecedores

### 📊 Dashboard
- KPIs gerais: caminhões, viagens, motoristas e custo de preventivas
- Cards ESG/ODS animados

---

## 🛠 Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.10+ / Flask 3.x |
| Banco | SQLite (biblioteca padrão do Python) |
| Templates | Jinja2 |
| Frontend | HTML5, CSS3, JavaScript puro |
| Gráficos | Chart.js 4 (CDN) |
| Ícones / Fonte | Font Awesome 6 / Inter (CDN) |

Únicas dependências: **Flask** e **python-dotenv**.

---

## 📂 Estrutura do Projeto

```text
logistica_1/
├── iniciar.bat            # Inicializador com dois cliques (Windows)
├── app.py                 # Backend Flask (rotas, banco, validações)
├── popular_dados.py       # Preenche o banco com dados fictícios
├── requirements.txt       # Dependências
├── .env.example           # Modelo do arquivo de configuração (senha)
├── logistica.db           # Banco SQLite (criado automaticamente, não vai para o GitHub)
├── static/
│   ├── style.css          # Estilo global
│   ├── viagem.js          # Cargas e cálculo de ocupação
│   ├── esg.js             # Animação dos cards ESG
│   └── logo.jpeg
└── templates/
    ├── base.html          # Layout base (menu e mensagens)
    ├── login.html
    ├── index.html         # Dashboard
    ├── cadastros.html
    ├── resultados_viagens.html
    └── resultados_manutencao.html
```

---

## 🗄️ Estrutura do Banco de Dados

SQLite puro, sem ORM. Para popular, recarregar ou zerar os dados, veja a seção [Banco de dados e dados de demonstração](#-banco-de-dados-e-dados-de-demonstração).

| Tabela | Conteúdo |
|---|---|
| `caminhoes` | Frota e capacidades |
| `motoristas` | Motoristas |
| `notas_fiscais` | Notas fiscais / produtos |
| `viagens` | Viagens (km, destino, frete, status) |
| `viagem_cargas` | Cargas de cada viagem (NF, quantidade, peso, cubagem, valor) |
| `manutencoes` | Manutenções preventivas |

---

## 🌱 Metas ESG / ODS

- **ODS 3 e 13**: rotas otimizadas e ocupação máxima de cubagem, para menos emissões por viagem
- **ODS 8, 9 e 12**: manutenção preventiva, segurança viária e maior vida útil de peças

---

## 📦 O que não vai para o GitHub (`.gitignore`)

| Arquivo / pasta | Por quê |
|---|---|
| `.venv/` | Só funciona no computador onde foi criada. Cada um cria a sua (o `iniciar.bat` faz isso) |
| `logistica.db` | Banco local. É recriado e populado automaticamente |
| `.env` | Configuração local (senha). Sem ele, vale a senha padrão `fatec2026`. Há um modelo em `.env.example` |

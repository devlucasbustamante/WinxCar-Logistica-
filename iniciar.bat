@echo off
REM ============================================================
REM  Winxcar Logistica - inicializador automatico (Windows)
REM  Basta dar dois cliques neste arquivo.
REM  1a vez: cria o ambiente virtual e instala o Flask (precisa de internet).
REM ============================================================
cd /d "%~dp0"
title Winxcar Logistica

python --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo  [ERRO] Python nao encontrado.
    echo  Instale o Python 3.10 ou superior em https://www.python.org/downloads/
    echo  e marque a opcao "Add python.exe to PATH" na instalacao.
    echo.
    pause
    exit /b 1
)

REM Se a pasta .venv veio de outro computador, ela nao funciona: recria.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo  Ambiente virtual invalido - recriando...
        rmdir /s /q .venv
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo  Criando ambiente virtual - so na primeira vez...
    python -m venv .venv
    if errorlevel 1 goto erro
)

echo  Verificando dependencias...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto erro

REM Se o banco estiver vazio (ex.: projeto recem-baixado do GitHub),
REM preenche com os dados ficticios de demonstracao.
".venv\Scripts\python.exe" popular_dados.py --se-vazio

REM Abre o navegador 3 segundos depois, quando o servidor ja subiu
start "" /b cmd /c "timeout /t 3 >nul & start http://127.0.0.1:5001"

".venv\Scripts\python.exe" app.py
pause
exit /b 0

:erro
echo.
echo  [ERRO] Falha ao preparar o ambiente. Verifique a conexao com a internet
echo  e tente novamente.
echo.
pause
exit /b 1

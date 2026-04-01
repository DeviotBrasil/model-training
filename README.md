# Treinamento de Modelos

Aplicativo desktop com interface gráfica (PyQt6) para treinamento de modelos de visão computacional.

## Requisitos

- Python 3.12.2
- Qt6 (necessário no Linux)

## Instalação

### Linux

Instale as dependências do Qt6:

```bash
sudo apt update
sudo apt install qt6-base-dev qt6-tools-dev-tools
```

Crie e ative o ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instale as dependências Python:

```bash
pip install -r requirements.txt
```

### Windows

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

> **Atenção:** No Windows, execute sempre pelo **Git Bash** a partir do diretório do projeto. O CMD e o PowerShell não suportam caminhos UNC (`\\wsl.localhost\...`).

## Execução

```bash
python main.py
```

## Editor de Interface

Para editar a interface gráfica (`interface.ui`) no Qt Designer:

```bash
/usr/lib/qt6/bin/designer
```

## Dependências

| Pacote | Versão |
|---|---|
| numpy | 2.4.4 |
| opencv-python | 4.13.0.92 |
| PyQt6 | 6.11.0 |

# Captura de Imagens — SciCam

Aplicativo desktop com interface gráfica (PyQt6) para captura e visualização de imagens de câmeras industriais via SDK SciCam. Suporta câmeras GigE e USB3, com controles de exposição, ganho e gama em tempo real.

## Funcionalidades

- Busca e conexão automática de câmeras GigE e USB3
- Visualização de frames ao vivo com escalonamento automático
- Controle de exposição (manual e automática), ganho e gama via sliders
- Registro de logs com rotação automática em `logs/app.log`
- Degradação graciosa quando o SDK não está disponível (modo simulação)

## Requisitos

- Python 3.12.2
- Qt6 (necessário no Linux)
- SDK SciCam (`libSciCamSDK.so` ou equivalente Windows) — veja [Configuração do SDK](#configuração-do-sdk)

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

> **Atenção:** Execute sempre pelo **Git Bash** a partir do diretório do projeto. O CMD e o PowerShell não suportam caminhos UNC (`\\wsl.localhost\...`).

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

## Configuração do SDK

O SDK SciCam é carregado automaticamente a partir da pasta `opt_samples/`. Copie os arquivos do SDK para esse diretório:

```
opt_samples/
├── SciCam_class.py
├── SciCamPayload_header.py
├── SciCamInfo_header.py
└── libSciCamSDK.so   # (Linux) ou SciCamSDK.dll (Windows)
```

Se o SDK não for encontrado, o aplicativo inicia em **modo simulação**: os controles de câmera são desabilitados e uma mensagem de aviso é exibida na tela principal.

As bibliotecas nativas de suporte (GigE, USB3, etc.) ficam em `libs/` e são carregadas automaticamente na inicialização.

## Execução

```bash
python main.py
```

## Estrutura do Projeto

```
.
├── main.py              # Ponto de entrada e lógica principal da UI
├── interface.ui         # Layout da janela principal (Qt Designer)
├── requirements.txt     # Dependências Python
├── libs/                # Bibliotecas nativas do SDK (CTI, SO/DLL)
├── opt_samples/         # Módulos Python do SDK SciCam e demos
├── logs/                # Logs da aplicação (gerados em tempo de execução)
├── System/Config/       # Configurações do driver (OptDriverSet.ini)
└── SystemLog/           # Logs gerados pelo driver da câmera
```

## Editor de Interface

Para editar o layout da janela (`interface.ui`) no Qt Designer:

```bash
# Linux
/usr/lib/qt6/bin/designer

# Via Python (qualquer plataforma)
pyqt6-tools designer
```

## Logs

O arquivo `logs/app.log` é criado automaticamente com rotação a cada 5 MB (até 5 arquivos de backup). Para acompanhar em tempo real:

```bash
tail -f logs/app.log
```

## Dependências

| Pacote | Versão |
|---|---|
| numpy | 2.4.4 |
| opencv-python | 4.13.0.92 |
| PyQt6 | 6.11.0 |
| PyQt6-Qt6 | 6.11.0 |
| PyQt6_sip | 13.11.1 |
| psutil | latest |

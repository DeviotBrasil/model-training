# Captura de Imagens — SciCam

Aplicativo desktop com interface gráfica (PyQt6) para captura e visualização de imagens de câmeras industriais via SDK SciCam. Suporta câmeras GigE e USB3, com controles de exposição, ganho e gama em tempo real.

## Funcionalidades

- Busca e conexão automática de câmeras GigE e USB3
- Visualização de frames ao vivo com escalonamento automático
- Controle de exposição (manual e automática), ganho e gama via sliders
- Registro de logs com rotação automática em `logs/app.log`
- Degradação graciosa quando o SDK não está disponível (modo simulação)

---

## Requisitos

- Python 3.12+
- SDK SciCam instalado (bibliotecas nativas em `libs/`)

---

## Instalação

### Linux

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# 2. Instale as dependências Python
pip install -r requirements.txt
```

### Windows

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
source venv/bin/activate

# 2. Instale as dependências Python
pip install -r requirements.txt
```

---

## Execução

```bash
python main.py
```

> Caso o SDK SciCam não esteja disponível, a aplicação inicializa em **modo simulação** — útil para desenvolvimento e testes da interface.

---

## Editor de Interface

Para editar o layout `interface.ui` visualmente no Qt Designer:

**Linux**
```bash
./.venv/bin/pyside6-designer
```

**Windows**
```bash
./.venv/Lib/site-packages/PySide6/designer.exe
```

---

## Arquitetura

### Camadas da Aplicação

```mermaid
graph TB
    subgraph Presentation["Apresentação (PyQt6)"]
        direction TB
        MW["MainWindow\n(main_window.py)"]
        CT["CameraThread\n(camera_thread.py)"]
    end

    subgraph Domain["Domínio"]
        direction TB
        CS["CameraService\n(camera_service.py)"]
        FP["FrameProcessor\n(frame_processor.py)"]
        ICD["&lt;&lt;interface&gt;&gt;\nICameraDevice\n(camera_interface.py)"]
    end

    subgraph Infrastructure["Infraestrutura"]
        direction TB
        SC["SciCamera\n(sci_camera.py)"]
        LS["LogSetup\n(log_setup.py)"]
    end

    subgraph External["SDK / Hardware"]
        direction TB
        SDK["SciCam SDK\n(libs nativas .dll/.so)"]
        CAM["Câmera\nGigE / USB3"]
    end

    MW -->|"usa"| CS
    MW -->|"cria/controla"| CT
    CT -->|"usa"| FP
    CT -->|"chama via"| ICD
    CS -->|"chama via"| ICD
    ICD <-.->|"implementa"| SC
    MW -->|"configura"| LS
    SC -->|"carrega"| SDK
    SDK <-->|"protocolo GigE/USB3"| CAM
```

### Fluxo de Captura de Imagens

```mermaid
sequenceDiagram
    actor User as Usuário
    participant UI as MainWindow
    participant SVC as CameraService
    participant THR as CameraThread
    participant FP as FrameProcessor
    participant CAM as SciCamera (SDK)

    User->>UI: clica "Buscar"
    UI->>SVC: discover(dev_infos, tl_type)
    SVC->>CAM: SciCam_DiscoveryDevices()
    CAM-->>SVC: lista de dispositivos
    SVC-->>UI: contagem + rótulos
    UI->>UI: popula comboBox

    User->>UI: seleciona câmera e clica "Conectar"
    UI->>SVC: connect(dev_info)
    SVC->>CAM: SciCam_CreateDevice()
    SVC->>CAM: SciCam_OpenDevice()
    SVC->>CAM: configurar parâmetros (exposição, ganho, gama)
    SVC-->>UI: CameraParams (valores iniciais)
    UI->>UI: inicializa sliders

    User->>UI: clica "Iniciar Captura"
    UI->>SVC: start_grab()
    SVC->>CAM: SciCam_StartGrab()
    UI->>THR: start()

    loop Captura contínua (QThread)
        THR->>CAM: SciCam_Grab()
        CAM-->>THR: payload bruto
        THR->>FP: convert(payload_attribute, payload)
        FP-->>THR: QImage
        THR-->>UI: frame_ready(QImage, w, h, frameID)
        UI->>UI: atualiza lblImage (scaled)
    end

    User->>UI: clica "Parar Captura"
    UI->>THR: stop() + wait()
    UI->>SVC: stop_grab()
    SVC->>CAM: SciCam_StopGrab()

    User->>UI: clica "Desconectar"
    UI->>SVC: disconnect()
    SVC->>CAM: SciCam_DeleteDevice()
```

### Ciclo de Vida da Câmera

```mermaid
stateDiagram-v2
    [*] --> Desconectada : inicialização

    Desconectada --> Descobrindo : Buscar
    Descobrindo --> Desconectada : nenhuma câmera encontrada
    Descobrindo --> Pronta : câmera(s) encontrada(s)

    Pronta --> Conectando : Conectar
    Conectando --> Conectada : SciCam_OpenDevice OK
    Conectando --> Pronta : erro de conexão

    Conectada --> Capturando : Iniciar Captura\n(SciCam_StartGrab)
    Capturando --> Conectada : Parar Captura\n(SciCam_StopGrab)

    Conectada --> Desconectada : Desconectar\n(SciCam_DeleteDevice)
    Capturando --> Desconectada : closeEvent\n(stop + delete)

    Capturando --> Capturando : frame_ready → atualiza UI
```

---

## Estrutura do Projeto

```
.
├── main.py                         # Ponto de entrada: libs nativas, logging e QApplication
├── requirements.txt                # Dependências Python
├── app/
│   ├── domain/
│   │   ├── frame_processor.py      # Converte payload bruto em QImage (Strategy)
│   │   ├── interfaces/
│   │   │   └── camera_interface.py # Contrato abstrato ICameraDevice
│   │   └── services/
│   │       └── camera_service.py   # Orquestra o ciclo de vida da câmera
│   ├── infrastructure/
│   │   ├── camera/
│   │   │   ├── sci_camera.py       # Implementação concreta via SDK SciCam
│   │   │   ├── sci_cam_errors.py   # Constantes de erro do SDK
│   │   │   ├── sci_cam_info.py     # Estruturas de informação de dispositivo
│   │   │   └── sci_cam_payload.py  # Estruturas e funções de payload/imagem
│   │   └── logging/
│   │       └── log_setup.py        # Configuração de logging com rotação
│   └── presentation/
│       ├── camera_thread.py        # QThread para captura em segundo plano
│       ├── main_window.py          # Janela principal (conecta UI ↔ domínio)
│       └── main_window.ui          # Layout Qt Designer
├── libs/                           # Bibliotecas nativas do SDK (CTI, SO/DLL)
├── samples/                        # Demos e módulos Python do SDK SciCam
├── logs/                           # Logs da aplicação (gerados em tempo de execução)
├── System/Config/                  # Configurações do driver (OptDriverSet.ini)
└── SystemLog/                      # Logs gerados pelo driver da câmera
```

---

## Dependências Python

| Pacote | Versão |
|---|---|
| numpy | 2.4.4 |
| opencv-python | 4.13.0.92 |
| PyQt6 | 6.11.0 |
| PyQt6-Qt6 | 6.11.0 |
| PyQt6_sip | 13.11.1 |
| psutil | latest |

"""Janela principal da aplicação de visualização de câmera SciCam.

Carrega o layout definido em interface.ui (PyQt6/Designer) e conecta os
widgets ao CameraService e à CameraThread. Se o SDK não estiver disponível
(libraría nativa ausente), os controles são desabilitados e uma mensagem
orientativa é exibida no lugar da imagem.
"""
import logging
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from app.domain.services.camera_service import CameraParams

_UI_FILE = str(Path(__file__).parent / 'main_window.ui')
Form, Window = uic.loadUiType(_UI_FILE)  # Gera as classes base a partir do arquivo .ui

log = logging.getLogger('scicam.ui')

# Flag global que indica se as bibliotecas nativas do SDK foram carregadas com sucesso
SDK_AVAILABLE = False
SDK_ERROR = ""

try:
    from app.infrastructure.camera.sci_camera import SciCamera
    from app.infrastructure.camera.sci_cam_info import SCI_DEVICE_INFO_LIST
    from app.domain.services.camera_service import CameraService
    from app.domain.frame_processor import FrameProcessor
    from app.presentation.camera_thread import CameraThread
    SDK_AVAILABLE = True
except (OSError, ImportError) as e:
    SDK_ERROR = str(e)
    log.warning('SDK SciCam indisponível: %s', e)


class MainWindow(Window, Form):
    """Janela principal que reúne todos os controles de câmera e exibição de imagem."""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)  # Inicializa os widgets gerados a partir do arquivo .ui

        # Atributos de estado controlados pela janela
        self._service: CameraService | None = None
        self._devInfos = None                        # Lista de dispositivos descobertos
        self._camera_thread: CameraThread | None = None
        self._processor: FrameProcessor | None = None

        # Conecta os sinais dos widgets aos métodos de controle
        self.btnSearch.clicked.connect(self._on_search)
        self.btnConnect.clicked.connect(self._on_connect)
        self.btnDisconnect.clicked.connect(self._on_disconnect)
        self.btnStartGrab.clicked.connect(self._on_start_grab)
        self.btnStopGrab.clicked.connect(self._on_stop_grab)
        self.chkAutoExposure.stateChanged.connect(self._on_auto_exposure_changed)
        self.sliderExposure.valueChanged.connect(self._on_exposure_changed)
        self.sliderGain.valueChanged.connect(self._on_gain_changed)
        self.sliderGamma.valueChanged.connect(self._on_gamma_changed)

        if not SDK_AVAILABLE:
            log.warning('SDK indisponível — controles desabilitados: %s', SDK_ERROR)
            self._disable_sdk_controls()
            return

        # Instancia as dependências principais somente quando o SDK está disponível
        self._service = CameraService(SciCamera())
        self._devInfos = SCI_DEVICE_INFO_LIST()
        self._processor = FrameProcessor()
        log.info('MainWindow inicializada')

    # --- SDK indisponível ---

    def _disable_sdk_controls(self) -> None:
        """Desabilita todos os controles de câmera e exibe mensagem de SDK ausente."""
        self.btnSearch.setEnabled(False)
        self.btnConnect.setEnabled(False)
        self.btnDisconnect.setEnabled(False)
        self.btnStartGrab.setEnabled(False)
        self.btnStopGrab.setEnabled(False)
        self.lblStatus.setText("SDK não encontrado")
        self.lblStatus.setStyleSheet("color: orange; font-weight: bold;")
        self.lblImage.setText(
            "SDK da câmera não está disponível.\n\n"
            "Coloque o arquivo  libSciCamSDK.so  dentro da pasta  libs/\n\n"
            f"Detalhe: {SDK_ERROR}"
        )
        self.lblImage.setStyleSheet(
            "background-color: #1a1a1a; color: #cc8800; font-size: 13px; padding: 20px;"
        )
        self.statusbar.showMessage(f"SDK não carregado: {SDK_ERROR}")

    # --- Busca e conexão ---

    def _on_search(self) -> None:
        """Dispara a busca de câmeras e preenche o combo com os dispositivos encontrados."""
        from app.infrastructure.camera.sci_cam_info import SciCamTLType

        self.cameraCombo.clear()
        self.btnConnect.setEnabled(False)
        log.info('Iniciando busca de câmeras')

        nRet = self._service.discover(self._devInfos, SciCamTLType.SciCam_TLType_Unkown)
        if nRet != 0:
            self.statusbar.showMessage(f"Erro ao buscar câmeras: código {nRet}")
            return

        if self._devInfos.count == 0:
            log.info('Nenhuma câmera encontrada')
            self.statusbar.showMessage("Nenhuma câmera encontrada")
            return

        log.info('%d câmera(s) encontrada(s)', self._devInfos.count)
        for i in range(self._devInfos.count):
            label = self._service.device_label(self._devInfos.pDevInfo[i], i)
            log.debug('  Câmera %d: %s', i, label)
            self.cameraCombo.addItem(label)

        self.btnConnect.setEnabled(True)
        self.statusbar.showMessage(f"{self._devInfos.count} câmera(s) encontrada(s)")

    def _on_connect(self) -> None:
        """Conecta à câmera selecionada no combo e carrega seus parâmetros iniciais."""
        idx = self.cameraCombo.currentIndex()
        if idx < 0 or idx >= self._devInfos.count:
            return
        ok, msg = self._service.connect(self._devInfos.pDevInfo[idx])
        if not ok:
            log.error(msg)
            self.statusbar.showMessage(msg)
            return

        params = self._service.read_params()
        if params:
            self._apply_params(params)

        self.groupBoxImage.setEnabled(True)
        self.lblStatus.setText("Conectado")
        self.lblStatus.setStyleSheet("color: green; font-weight: bold;")
        self.btnConnect.setEnabled(False)
        self.btnDisconnect.setEnabled(True)
        self.btnStartGrab.setEnabled(True)
        self.statusbar.showMessage(msg)
        log.info(msg)

    def _on_disconnect(self) -> None:
        """Para a captura (se ativa), desconecta a câmera e restaura o estado da UI."""
        log.info('Desconectando câmera')
        self._stop_camera_thread()
        self._service.disconnect()

        self.lblStatus.setText("Desconectado")
        self.lblStatus.setStyleSheet("color: red; font-weight: bold;")
        self.btnConnect.setEnabled(True)
        self.btnDisconnect.setEnabled(False)
        self.btnStartGrab.setEnabled(False)
        self.btnStopGrab.setEnabled(False)
        self.lblImage.clear()
        self.lblImage.setText("Sem imagem")
        self.lblFrameInfo.setText("")
        self.groupBoxImage.setEnabled(False)
        self.statusbar.showMessage("Câmera desconectada")

    # --- Captura de frames ---

    def _on_start_grab(self) -> None:
        """Inicia a captura contínua e sobe a CameraThread para processar frames."""
        log.info('Iniciando captura de imagens')
        ok, msg = self._service.start_grabbing()
        if not ok:
            self.statusbar.showMessage(msg)
            return

        self._camera_thread = CameraThread(self._service._camera, self._processor)
        self._camera_thread.frame_ready.connect(self._on_frame_ready)
        self._camera_thread.error_occurred.connect(self._on_thread_error)
        self._camera_thread.start()

        self.btnStartGrab.setEnabled(False)
        self.btnStopGrab.setEnabled(True)
        self.statusbar.showMessage(msg)
        log.info(msg)

    def _on_stop_grab(self) -> None:
        """Para a CameraThread e solicita ao SDK que interrompa o fluxo de frames."""
        log.info('Parando captura de imagens')
        self._stop_camera_thread()
        self._service.stop_grabbing()

        self.btnStartGrab.setEnabled(True)
        self.btnStopGrab.setEnabled(False)
        self.statusbar.showMessage("Captura parada")

    def _stop_camera_thread(self) -> None:
        """Interrompe a thread de captura de forma segura, se ela estiver em execução."""
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.stop()
            self._camera_thread = None

    def _on_thread_error(self, msg: str) -> None:
        """Exibe na barra de status erros emitidos pela CameraThread."""
        log.error('Erro na thread de captura: %s', msg)
        self.statusbar.showMessage(f"Erro: {msg}")

    # --- Parâmetros de imagem ---

    def _apply_params(self, params: CameraParams) -> None:
        """Aplica os parâmetros lidos da câmera nos sliders e labels da UI.

        Bloqueia os sinais dos widgets durante a atualização para evitar
        chamadas de retorno ao SDK enquanto os controles são inicializados.
        """
        self.chkAutoExposure.blockSignals(True)
        self.chkAutoExposure.setChecked(params.auto_exposure)
        self.chkAutoExposure.blockSignals(False)
        self.sliderExposure.setEnabled(not params.auto_exposure)

        self.sliderExposure.setMinimum(params.exposure_min)
        self.sliderExposure.setMaximum(params.exposure_max)
        self.sliderExposure.blockSignals(True)
        self.sliderExposure.setValue(params.exposure_val)
        self.sliderExposure.blockSignals(False)
        self.lblExposureVal.setText(f'{params.exposure_val} µs')

        self.sliderGain.setMaximum(params.gain_slider_max)
        self.sliderGain.blockSignals(True)
        self.sliderGain.setValue(int(params.gain_db * 10))
        self.sliderGain.blockSignals(False)
        self.lblGainVal.setText(f'{params.gain_db:.1f} dB')

        gamma_slider_val = int(max(10, min(300, params.gamma * 100)))
        self.sliderGamma.blockSignals(True)
        self.sliderGamma.setValue(gamma_slider_val)
        self.sliderGamma.blockSignals(False)
        self.lblGammaVal.setText(f'{params.gamma:.2f}')

    def _on_auto_exposure_changed(self, state: int) -> None:
        """Ativa/desativa a exposição automática e ajusta o estado do slider."""
        self._service.set_auto_exposure(bool(state))
        self.sliderExposure.setEnabled(not bool(state))

    def _on_exposure_changed(self, value: int) -> None:
        """Atualiza o label e envia o novo tempo de exposição (µs) para a câmera."""
        self.lblExposureVal.setText(f'{value} µs')
        self._service.set_exposure(float(value))

    def _on_gain_changed(self, value: int) -> None:
        """Converte o valor do slider (inteiro *10) em dB e envia para a câmera."""
        gain_db = value / 10.0
        self.lblGainVal.setText(f'{gain_db:.1f} dB')
        self._service.set_gain(gain_db)

    def _on_gamma_changed(self, value: int) -> None:
        """Converte o valor do slider (inteiro *100) em gamma e envia para a câmera."""
        gamma = value / 100.0
        self.lblGammaVal.setText(f'{gamma:.2f}')
        self._service.set_gamma(gamma)

    # --- Renderização de frames ---

    def _on_frame_ready(self, qimage: QImage, width: int, height: int, frameID: int) -> None:
        """Recebe um frame da CameraThread, escala-o para o widget e atualiza o contador.

        O escalonamento usa KeepAspectRatio com FastTransformation para minimizar
        o impacto de performance no loop de captura em alta frequência.
        """
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.lblImage.width(),
            self.lblImage.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.lblImage.setPixmap(scaled)
        self.lblFrameInfo.setText(f"Frame: {frameID} | {width}×{height} px")

    # --- Encerramento ---

    def closeEvent(self, event) -> None:
        """Garante que a câmera e a thread sejam liberadas antes de fechar a janela."""
        log.info('Encerrando aplicação')
        self._stop_camera_thread()
        if self._service:
            self._service.close_if_open()
        event.accept()

import logging
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from app.domain.services.camera_service import CameraParams

_UI_FILE = str(Path(__file__).parent / 'interface.ui')
Form, Window = uic.loadUiType(_UI_FILE)

log = logging.getLogger('scicam.ui')

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
    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)

        self._service: CameraService | None = None
        self._devInfos = None
        self._camera_thread: CameraThread | None = None
        self._processor: FrameProcessor | None = None

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

        self._service = CameraService(SciCamera())
        self._devInfos = SCI_DEVICE_INFO_LIST()
        self._processor = FrameProcessor()
        log.info('MainWindow inicializada')

    # --- SDK indisponível ---

    def _disable_sdk_controls(self) -> None:
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

    # --- Captura ---

    def _on_start_grab(self) -> None:
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
        log.info('Parando captura de imagens')
        self._stop_camera_thread()
        self._service.stop_grabbing()

        self.btnStartGrab.setEnabled(True)
        self.btnStopGrab.setEnabled(False)
        self.statusbar.showMessage("Captura parada")

    def _stop_camera_thread(self) -> None:
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.stop()
            self._camera_thread = None

    def _on_thread_error(self, msg: str) -> None:
        log.error('Erro na thread de captura: %s', msg)
        self.statusbar.showMessage(f"Erro: {msg}")

    # --- Parâmetros de imagem ---

    def _apply_params(self, params: CameraParams) -> None:
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
        self._service.set_auto_exposure(bool(state))
        self.sliderExposure.setEnabled(not bool(state))

    def _on_exposure_changed(self, value: int) -> None:
        self.lblExposureVal.setText(f'{value} µs')
        self._service.set_exposure(float(value))

    def _on_gain_changed(self, value: int) -> None:
        gain_db = value / 10.0
        self.lblGainVal.setText(f'{gain_db:.1f} dB')
        self._service.set_gain(gain_db)

    def _on_gamma_changed(self, value: int) -> None:
        gamma = value / 100.0
        self.lblGammaVal.setText(f'{gamma:.2f}')
        self._service.set_gamma(gamma)

    # --- Frame rendering ---

    def _on_frame_ready(self, qimage: QImage, width: int, height: int, frameID: int) -> None:
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
        log.info('Encerrando aplicação')
        self._stop_camera_thread()
        if self._service:
            self._service.close_if_open()
        event.accept()

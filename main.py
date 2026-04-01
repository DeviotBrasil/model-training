import sys
import os
import ctypes
import socket
import struct
import logging
from logging.handlers import RotatingFileHandler

import numpy as np

_libs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs')
if os.path.isdir(_libs_dir):
    if sys.platform == 'win32':
        # Windows: registra o diretório para busca de DLLs (Python >= 3.8)
        os.add_dll_directory(_libs_dir)
    elif _libs_dir not in os.environ.get('LD_LIBRARY_PATH', '').split(':'):
        # Linux: LD_LIBRARY_PATH só tem efeito antes do processo iniciar → re-exec
        os.environ['LD_LIBRARY_PATH'] = _libs_dir + ':' + os.environ.get('LD_LIBRARY_PATH', '')
        os.execv(sys.executable, [sys.executable] + sys.argv)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'opt_samples'))

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(_log_dir, exist_ok=True)

_formatter = logging.Formatter(
    fmt='%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

_file_handler = RotatingFileHandler(
    os.path.join(_log_dir, 'app.log'),
    maxBytes=5 * 1024 * 1024,  # 5 MB por arquivo
    backupCount=5,
    encoding='utf-8',
)
_file_handler.setFormatter(_formatter)
_file_handler.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)
_console_handler.setLevel(logging.INFO)

logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(_file_handler)
logging.root.addHandler(_console_handler)

log = logging.getLogger('scicam')
# ---------------------------------------------------------------------------

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

SDK_AVAILABLE = False
SDK_ERROR = ""

try:
    from SciCam_class import (
        SciCamera, SciCamTLType, SCI_DEVICE_INFO_LIST, SCI_CAM_PAYLOAD_ATTRIBUTE,
        SciCamDeviceXmlType, SCI_CAMERA_OK, SCI_NODE_VAL_FLOAT,
    )
    from SciCamPayload_header import (
        SciCamPayloadMode, SciCamPixelType,
        SciCam_Payload_GetAttribute, SciCam_Payload_GetImage,
        SciCam_Payload_ConvertImageEx,
    )
    SDK_AVAILABLE = True
    log.info('SDK SciCam carregado com sucesso')
except (OSError, ImportError) as e:
    SDK_ERROR = str(e)
    log.warning('SDK SciCam indisponível: %s', e)


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage, int, int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera):
        super().__init__()
        self._camera = camera
        self._running = False

    def run(self):
        _tlog = logging.getLogger('scicam.thread')
        _tlog.info('CameraThread iniciada')
        self._running = True
        _grab_errors = 0
        while self._running:
            ppayload = ctypes.c_void_p()
            nRet = self._camera.SciCam_Grab(ppayload)
            if nRet != SCI_CAMERA_OK:
                _grab_errors += 1
                if _grab_errors <= 5 or _grab_errors % 50 == 0:
                    _tlog.warning('SciCam_Grab falhou (código %d, ocorrência %d)', nRet, _grab_errors)
                if ppayload.value is not None:
                    self._camera.SciCam_FreePayload(ppayload)
                continue
            _grab_errors = 0

            payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
            nRet = SciCam_Payload_GetAttribute(ppayload, payloadAttribute)
            if nRet != SCI_CAMERA_OK or not payloadAttribute.isComplete:
                _tlog.debug('Payload descartado: GetAttribute=%d isComplete=%s', nRet, payloadAttribute.isComplete)
                self._camera.SciCam_FreePayload(ppayload)
                continue

            if payloadAttribute.payloadMode != SciCamPayloadMode.SciCam_PayloadMode_2D:
                self._camera.SciCam_FreePayload(ppayload)
                continue

            width = payloadAttribute.imgAttr.width
            height = payloadAttribute.imgAttr.height
            frameID = payloadAttribute.frameID

            imgdata = ctypes.c_void_p()
            nRet = SciCam_Payload_GetImage(ppayload, imgdata)
            if nRet != SCI_CAMERA_OK or not imgdata.value:
                self._camera.SciCam_FreePayload(ppayload)
                continue

            try:
                qimage = self._convert_to_qimage(payloadAttribute, imgdata, width, height)
                if qimage is not None:
                    _tlog.debug('Frame %d emitido: %dx%d', frameID, width, height)
                    self.frame_ready.emit(qimage, width, height, frameID)
                else:
                    _tlog.warning('Frame %d: conversão retornou None (pixelType=%s)', frameID, payloadAttribute.imgAttr.pixelType)
            except Exception as e:
                _tlog.exception('Exceção ao processar frame %d', frameID)
                self.error_occurred.emit(str(e))
            finally:
                self._camera.SciCam_FreePayload(ppayload)

    def _convert_to_qimage(self, payloadAttribute, imgdata, width, height):
        ptype = payloadAttribute.imgAttr.pixelType

        if ptype == SciCamPixelType.Mono8:
            data_size = width * height
            raw = ctypes.string_at(imgdata.value, data_size)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width))
            qimg = QImage(arr.data, width, height, width, QImage.Format.Format_Grayscale8)
            return qimg.copy()

        if ptype == SciCamPixelType.RGB8:
            data_size = width * height * 3
            raw = ctypes.string_at(imgdata.value, data_size)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            qimg = QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888)
            return qimg.copy()

        if ptype == SciCamPixelType.BGR8:
            data_size = width * height * 3
            raw = ctypes.string_at(imgdata.value, data_size)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            arr = arr[:, :, ::-1].copy()
            qimg = QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888)
            return qimg.copy()

        _color_types = {
            SciCamPixelType.BayerBG8, SciCamPixelType.BayerGR8,
            SciCamPixelType.BayerRG8, SciCamPixelType.BayerGB8,
            SciCamPixelType.YUV422_8, SciCamPixelType.YUV422_8_UYVY,
            SciCamPixelType.YUV8_UYV,
        }
        dst_type = SciCamPixelType.RGB8 if ptype in _color_types else SciCamPixelType.Mono8

        dstImgSize = ctypes.c_uint64(0)
        nRet = SciCam_Payload_ConvertImageEx(
            payloadAttribute.imgAttr, imgdata, dst_type, None, dstImgSize, True, 0
        )
        if nRet != SCI_CAMERA_OK or dstImgSize.value == 0:
            return None

        pDstData = (ctypes.c_ubyte * dstImgSize.value)()
        nRet = SciCam_Payload_ConvertImageEx(
            payloadAttribute.imgAttr, imgdata, dst_type, pDstData, dstImgSize, True, 0
        )
        if nRet != SCI_CAMERA_OK:
            return None

        if dst_type == SciCamPixelType.RGB8:
            arr = np.frombuffer(pDstData, dtype=np.uint8).reshape((height, width, 3))
            qimg = QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888)
        else:
            arr = np.frombuffer(pDstData, dtype=np.uint8).reshape((height, width))
            qimg = QImage(arr.data, width, height, width, QImage.Format.Format_Grayscale8)

        return qimg.copy()

    def stop(self):
        logging.getLogger('scicam.thread').info('CameraThread parando')
        self._running = False
        self.wait(2000)


Form, Window = uic.loadUiType("interface.ui")


class MainWindow(Window, Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self._camera = None
        self._devInfos = None
        self._camera_thread = None

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

        self._camera = SciCamera()
        self._devInfos = SCI_DEVICE_INFO_LIST()
        self._device_created = False
        log.info('MainWindow inicializada')

    def _disable_sdk_controls(self):
        self.btnSearch.setEnabled(False)
        self.btnConnect.setEnabled(False)
        self.btnDisconnect.setEnabled(False)
        self.btnStartGrab.setEnabled(False)
        self.btnStopGrab.setEnabled(False)
        self.lblStatus.setText("SDK não encontrado")
        self.lblStatus.setStyleSheet("color: orange; font-weight: bold;")
        self.lblImage.setText(
            "SDK da câmera não está disponível.\n\n"
            "Coloque o arquivo  libSciCamSDK.so  dentro da pasta  opt_samples/\n\n"
            f"Detalhe: {SDK_ERROR}"
        )
        self.lblImage.setStyleSheet(
            "background-color: #1a1a1a; color: #cc8800; font-size: 13px; padding: 20px;"
        )
        self.statusbar.showMessage(f"SDK não carregado: {SDK_ERROR}")

    def _on_search(self):
        if not SDK_AVAILABLE:
            return
        self.cameraCombo.clear()
        self.btnConnect.setEnabled(False)

        log.info('Iniciando busca de câmeras')
        nRet = SciCamera.SciCam_DiscoveryDevices(self._devInfos, SciCamTLType.SciCam_TLType_Unkown)
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_DiscoveryDevices falhou: código %d', nRet)
            self.statusbar.showMessage(f"Erro ao buscar câmeras: código {nRet}")
            return

        if self._devInfos.count == 0:
            log.info('Nenhuma câmera encontrada')
            self.statusbar.showMessage("Nenhuma câmera encontrada")
            return

        log.info('%d câmera(s) encontrada(s)', self._devInfos.count)
        for i in range(self._devInfos.count):
            label = self._device_label(self._devInfos.pDevInfo[i], i)
            log.debug('  Câmera %d: %s', i, label)
            self.cameraCombo.addItem(label)
        self.btnConnect.setEnabled(True)
        self.statusbar.showMessage(f"{self._devInfos.count} câmera(s) encontrada(s)")

    def _device_label(self, dev, index):
        try:
            if dev.tlType == SciCamTLType.SciCam_TLType_Gige:
                model = bytes(b for b in dev.info.gigeInfo.modelName if b != 0).decode('ascii', errors='replace')
                ip = dev.info.gigeInfo.ip
                # SDK armazena IP como uint32 little-endian; htonl converte para network order
                ip_str = socket.inet_ntoa(struct.pack('>I', socket.htonl(ip)))
                return f"[{index}] GigE  {model}  ({ip_str})"
            if dev.tlType == SciCamTLType.SciCam_TLType_Usb3:
                name = bytes(b for b in dev.info.usb3Info.name if b != 0).decode('ascii', errors='replace')
                return f"[{index}] USB3  {name}"
        except Exception:
            pass
        return f"[{index}] Câmera"

    # ------------------------------------------------------------------
    # Ajustes de imagem
    # ------------------------------------------------------------------
    def _read_camera_params(self):
        nv = SCI_NODE_VAL_FLOAT()
        xml = SciCamDeviceXmlType.SciCam_DeviceXml_Camera

        # ExposureAuto
        try:
            from SciCamInfo_header import SCI_NODE_VAL_ENUM
            nv_enum = SCI_NODE_VAL_ENUM()
            if self._camera.SciCam_GetEnumValueEx(xml, 'ExposureAuto', nv_enum) == SCI_CAMERA_OK:
                enum_str = bytes(nv_enum.chCurVal).split(b'\x00')[0].decode('ascii', errors='replace')
                is_auto = enum_str not in ('Off', '')
                self.chkAutoExposure.blockSignals(True)
                self.chkAutoExposure.setChecked(is_auto)
                self.chkAutoExposure.blockSignals(False)
                self.sliderExposure.setEnabled(not is_auto)
        except Exception:
            pass

        # ExposureTime
        if self._camera.SciCam_GetFloatValueEx(xml, 'ExposureTime', nv) == SCI_CAMERA_OK:
            val = int(max(nv.dMin, min(nv.dMax, nv.dVal)))
            slider_max = int(min(nv.dMax, 100000))
            slider_min = int(max(nv.dMin, 100))
            self.sliderExposure.setMinimum(slider_min)
            self.sliderExposure.setMaximum(slider_max)
            self.sliderExposure.blockSignals(True)
            self.sliderExposure.setValue(val)
            self.sliderExposure.blockSignals(False)
            self.lblExposureVal.setText(f'{val} µs')
            log.debug('ExposureTime: val=%d min=%d max=%d', val, slider_min, slider_max)

        # Gain
        if self._camera.SciCam_GetFloatValueEx(xml, 'Gain', nv) == SCI_CAMERA_OK:
            val_db = nv.dVal
            slider_max = int(min(nv.dMax, 24.0) * 10)
            slider_val = int(max(0, min(slider_max, val_db * 10)))
            self.sliderGain.setMaximum(slider_max)
            self.sliderGain.blockSignals(True)
            self.sliderGain.setValue(slider_val)
            self.sliderGain.blockSignals(False)
            self.lblGainVal.setText(f'{val_db:.1f} dB')
            log.debug('Gain: val=%.1f dB min=%.1f max=%.1f', val_db, nv.dMin, nv.dMax)

        # Gamma
        if self._camera.SciCam_GetFloatValueEx(xml, 'Gamma', nv) == SCI_CAMERA_OK:
            gamma = nv.dVal
            slider_val = int(max(10, min(300, gamma * 100)))
            self.sliderGamma.blockSignals(True)
            self.sliderGamma.setValue(slider_val)
            self.sliderGamma.blockSignals(False)
            self.lblGammaVal.setText(f'{gamma:.2f}')
            log.debug('Gamma: val=%.2f', gamma)

    def _on_auto_exposure_changed(self, state):
        xml = SciCamDeviceXmlType.SciCam_DeviceXml_Camera
        if state:
            self._camera.SciCam_SetEnumValueByStringEx(xml, 'ExposureAuto', 'Continuous')
            self.sliderExposure.setEnabled(False)
            log.info('ExposureAuto=Continuous')
        else:
            self._camera.SciCam_SetEnumValueByStringEx(xml, 'ExposureAuto', 'Off')
            self.sliderExposure.setEnabled(True)
            log.info('ExposureAuto=Off')

    def _on_exposure_changed(self, value):
        self.lblExposureVal.setText(f'{value} µs')
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'ExposureTime', float(value)
        )

    def _on_gain_changed(self, value):
        gain_db = value / 10.0
        self.lblGainVal.setText(f'{gain_db:.1f} dB')
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'Gain', gain_db
        )

    def _on_gamma_changed(self, value):
        gamma = value / 100.0
        self.lblGammaVal.setText(f'{gamma:.2f}')
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'Gamma', gamma
        )

    def _on_connect(self):
        idx = self.cameraCombo.currentIndex()
        if idx < 0 or idx >= self._devInfos.count:
            return
        self._connect_device(self._devInfos.pDevInfo[idx])

    def _connect_device(self, dev):
        log.debug('_connect_device: tlType=%d devType=%d', dev.tlType, dev.devType)
        # Só deleta se havia um dispositivo criado anteriormente
        if self._device_created:
            log.debug('Deletando dispositivo anterior')
            self._camera.SciCam_DeleteDevice()
            self._device_created = False
        nRet = self._camera.SciCam_CreateDevice(dev)
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_CreateDevice falhou: código %d', nRet)
            self.statusbar.showMessage(f"Erro ao criar dispositivo: código {nRet}")
            return
        self._device_created = True
        log.info('SciCam_CreateDevice OK')

        nRet = self._camera.SciCam_OpenDevice()
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_OpenDevice falhou: código %d', nRet)
            self._camera.SciCam_DeleteDevice()
            self._device_created = False
            self.statusbar.showMessage(f"Erro ao abrir dispositivo: código {nRet}")
            return
        log.info('SciCam_OpenDevice OK')

        self._camera.SciCam_SetEnumValueByStringEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, "TriggerMode", "Off"
        )
        # Packet size seguro para evitar frames incompletos; 1450 garante no-fragmentation
        # em qualquer caminho de rede sem depender de jumbo frames
        self._camera.SciCam_SetIntValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, "GevSCPSPacketSize", 1450
        )
        log.info('GevSCPSPacketSize=1450')
        self._read_camera_params()
        self.groupBoxImage.setEnabled(True)

        self.lblStatus.setText("Conectado")
        self.lblStatus.setStyleSheet("color: green; font-weight: bold;")
        self.btnConnect.setEnabled(False)
        self.btnDisconnect.setEnabled(True)
        self.btnStartGrab.setEnabled(True)
        self.statusbar.showMessage("Câmera conectada com sucesso")
        log.info('Câmera conectada com sucesso')

    def _on_disconnect(self):
        log.info('Desconectando câmera')
        self._stop_camera_thread()
        self._camera.SciCam_StopGrabbing()
        self._camera.SciCam_CloseDevice()
        self._camera.SciCam_DeleteDevice()
        self._device_created = False

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
        log.info('Câmera desconectada')

    def _on_start_grab(self):
        log.info('Iniciando captura de imagens')
        nRet = self._camera.SciCam_StartGrabbing()
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_StartGrabbing falhou: código %d', nRet)
            self.statusbar.showMessage(f"Erro ao iniciar captura: código {nRet}")
            return

        self._camera_thread = CameraThread(self._camera)
        self._camera_thread.frame_ready.connect(self._on_frame_ready)
        self._camera_thread.error_occurred.connect(
            lambda msg: (log.error('Erro na thread de captura: %s', msg),
                         self.statusbar.showMessage(f"Erro: {msg}"))
        )
        self._camera_thread.start()

        self.btnStartGrab.setEnabled(False)
        self.btnStopGrab.setEnabled(True)
        self.statusbar.showMessage("Captura iniciada")
        log.info('Captura iniciada')

    def _on_stop_grab(self):
        log.info('Parando captura de imagens')
        self._stop_camera_thread()
        self._camera.SciCam_StopGrabbing()

        self.btnStartGrab.setEnabled(True)
        self.btnStopGrab.setEnabled(False)
        self.statusbar.showMessage("Captura parada")
        log.info('Captura parada')

    def _stop_camera_thread(self):
        if self._camera_thread and self._camera_thread.isRunning():
            self._camera_thread.stop()
            self._camera_thread = None

    def _on_frame_ready(self, qimage: QImage, width: int, height: int, frameID: int):
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.lblImage.width(),
            self.lblImage.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.lblImage.setPixmap(scaled)
        self.lblFrameInfo.setText(f"Frame: {frameID} | {width}×{height} px")

    def closeEvent(self, event):
        log.info('Encerrando aplicação')
        self._stop_camera_thread()
        try:
            if self._camera and self._camera.SciCam_IsDeviceOpen():
                self._camera.SciCam_StopGrabbing()
                self._camera.SciCam_CloseDevice()
                self._camera.SciCam_DeleteDevice()
                self._device_created = False
                log.info('Dispositivo fechado ao encerrar')
        except Exception as e:
            log.warning('Erro ao fechar dispositivo no closeEvent: %s', e)
        event.accept()


if __name__ == "__main__":
    log.info('=== Iniciando aplicação ===')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    log.info('=== Aplicação encerrada (código %d) ===', exit_code)
    sys.exit(exit_code)

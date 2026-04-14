import ctypes
import logging

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from app.domain.frame_processor import FrameProcessor
from app.domain.interfaces.camera_interface import ICameraDevice

log = logging.getLogger('scicam.thread')


class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage, int, int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera: ICameraDevice, processor: FrameProcessor) -> None:
        super().__init__()
        self._camera = camera
        self._processor = processor
        self._running = False

    def run(self) -> None:
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK
        from app.infrastructure.camera.sci_cam_payload import (
            SciCamPayloadMode, SciCam_Payload_GetAttribute, SciCam_Payload_GetImage,
            SCI_CAM_PAYLOAD_ATTRIBUTE,
        )

        log.info('CameraThread iniciada')
        self._running = True
        _grab_errors = 0

        while self._running:
            ppayload = ctypes.c_void_p()
            nRet = self._camera.SciCam_Grab(ppayload)

            if nRet != SCI_CAMERA_OK:
                _grab_errors += 1
                if _grab_errors <= 5 or _grab_errors % 50 == 0:
                    log.warning('SciCam_Grab falhou (código %d, ocorrência %d)', nRet, _grab_errors)
                if ppayload.value is not None:
                    self._camera.SciCam_FreePayload(ppayload)
                continue

            _grab_errors = 0
            payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
            nRet = SciCam_Payload_GetAttribute(ppayload, payloadAttribute)

            if nRet != SCI_CAMERA_OK or not payloadAttribute.isComplete:
                log.debug(
                    'Payload descartado: GetAttribute=%d isComplete=%s',
                    nRet, payloadAttribute.isComplete,
                )
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
                qimage = self._processor.convert(payloadAttribute, imgdata, width, height)
                if qimage is not None:
                    log.debug('Frame %d emitido: %dx%d', frameID, width, height)
                    self.frame_ready.emit(qimage, width, height, frameID)
                else:
                    log.warning(
                        'Frame %d: conversão retornou None (pixelType=%s)',
                        frameID, payloadAttribute.imgAttr.pixelType,
                    )
            except Exception:
                log.exception('Exceção ao processar frame %d', frameID)
                self.error_occurred.emit(f"Erro ao processar frame {frameID}")
            finally:
                self._camera.SciCam_FreePayload(ppayload)

    def stop(self) -> None:
        log.info('CameraThread parando')
        self._running = False
        self.wait(2000)

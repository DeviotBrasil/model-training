import socket
import struct
import logging
from dataclasses import dataclass

from app.domain.interfaces.camera_interface import ICameraDevice

log = logging.getLogger('scicam.service')

PACKET_SIZE_SAFE = 1450
EXPOSURE_MIN = 100
EXPOSURE_MAX = 100_000
GAIN_MAX_DB = 24.0


@dataclass
class CameraParams:
    exposure_val: int
    exposure_min: int
    exposure_max: int
    gain_db: float
    gain_slider_max: int
    gamma: float
    auto_exposure: bool


class CameraService:
    def __init__(self, camera: ICameraDevice) -> None:
        self._camera = camera
        self._device_created = False

    # --- Discovery ---

    def discover(self, dev_infos, tl_type) -> int:
        nRet = type(self._camera).SciCam_DiscoveryDevices(dev_infos, tl_type)
        count = dev_infos.count if nRet == 0 else 0
        log.info('Discovery: código=%d câmeras=%d', nRet, count)
        return nRet

    def device_label(self, dev, index: int) -> str:
        from app.infrastructure.camera.sci_cam_info import SciCamTLType
        try:
            if dev.tlType == SciCamTLType.SciCam_TLType_Gige:
                model = bytes(b for b in dev.info.gigeInfo.modelName if b != 0).decode('ascii', errors='replace')
                ip = dev.info.gigeInfo.ip
                ip_str = socket.inet_ntoa(struct.pack('>I', socket.htonl(ip)))
                return f"[{index}] GigE  {model}  ({ip_str})"
            if dev.tlType == SciCamTLType.SciCam_TLType_Usb3:
                name = bytes(b for b in dev.info.usb3Info.name if b != 0).decode('ascii', errors='replace')
                return f"[{index}] USB3  {name}"
        except Exception:
            pass
        return f"[{index}] Câmera"

    # --- Lifecycle ---

    def connect(self, dev) -> tuple[bool, str]:
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType

        if self._device_created:
            log.debug('Deletando dispositivo anterior')
            self._camera.SciCam_DeleteDevice()
            self._device_created = False

        nRet = self._camera.SciCam_CreateDevice(dev)
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_CreateDevice falhou: código %d', nRet)
            return False, f"Erro ao criar dispositivo: código {nRet}"
        self._device_created = True
        log.info('SciCam_CreateDevice OK')

        nRet = self._camera.SciCam_OpenDevice()
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_OpenDevice falhou: código %d', nRet)
            self._camera.SciCam_DeleteDevice()
            self._device_created = False
            return False, f"Erro ao abrir dispositivo: código {nRet}"
        log.info('SciCam_OpenDevice OK')

        xml = SciCamDeviceXmlType.SciCam_DeviceXml_Camera
        self._camera.SciCam_SetEnumValueByStringEx(xml, "TriggerMode", "Off")
        self._camera.SciCam_SetIntValueEx(xml, "GevSCPSPacketSize", PACKET_SIZE_SAFE)
        log.info('TriggerMode=Off GevSCPSPacketSize=%d', PACKET_SIZE_SAFE)
        return True, "Câmera conectada com sucesso"

    def disconnect(self) -> None:
        self._camera.SciCam_StopGrabbing()
        self._camera.SciCam_CloseDevice()
        self._camera.SciCam_DeleteDevice()
        self._device_created = False
        log.info('Câmera desconectada')

    def close_if_open(self) -> None:
        try:
            if self._camera.SciCam_IsDeviceOpen():
                self._camera.SciCam_StopGrabbing()
                self._camera.SciCam_CloseDevice()
                self._camera.SciCam_DeleteDevice()
                self._device_created = False
                log.info('Dispositivo fechado ao encerrar')
        except Exception as e:
            log.warning('Erro ao fechar dispositivo: %s', e)

    # --- Grabbing ---

    def start_grabbing(self) -> tuple[bool, str]:
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK
        nRet = self._camera.SciCam_StartGrabbing()
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_StartGrabbing falhou: código %d', nRet)
            return False, f"Erro ao iniciar captura: código {nRet}"
        return True, "Captura iniciada"

    def stop_grabbing(self) -> None:
        self._camera.SciCam_StopGrabbing()

    # --- Parâmetros ---

    def read_params(self) -> CameraParams | None:
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK
        from app.infrastructure.camera.sci_cam_info import (
            SciCamDeviceXmlType, SCI_NODE_VAL_FLOAT, SCI_NODE_VAL_ENUM,
        )

        xml = SciCamDeviceXmlType.SciCam_DeviceXml_Camera
        nv = SCI_NODE_VAL_FLOAT()

        auto_exposure = False
        try:
            nv_enum = SCI_NODE_VAL_ENUM()
            if self._camera.SciCam_GetEnumValueEx(xml, 'ExposureAuto', nv_enum) == SCI_CAMERA_OK:
                enum_str = bytes(nv_enum.chCurVal).split(b'\x00')[0].decode('ascii', errors='replace')
                auto_exposure = enum_str not in ('Off', '')
        except Exception:
            pass

        exposure_val, exposure_min, exposure_max = 1000, EXPOSURE_MIN, EXPOSURE_MAX
        if self._camera.SciCam_GetFloatValueEx(xml, 'ExposureTime', nv) == SCI_CAMERA_OK:
            exposure_val = int(max(nv.dMin, min(nv.dMax, nv.dVal)))
            exposure_min = int(max(nv.dMin, EXPOSURE_MIN))
            exposure_max = int(min(nv.dMax, EXPOSURE_MAX))
            log.debug('ExposureTime: val=%d min=%d max=%d', exposure_val, exposure_min, exposure_max)

        gain_db, gain_slider_max = 0.0, int(GAIN_MAX_DB * 10)
        if self._camera.SciCam_GetFloatValueEx(xml, 'Gain', nv) == SCI_CAMERA_OK:
            gain_db = nv.dVal
            gain_slider_max = int(min(nv.dMax, GAIN_MAX_DB) * 10)
            log.debug('Gain: val=%.1f dB min=%.1f max=%.1f', gain_db, nv.dMin, nv.dMax)

        gamma = 1.0
        if self._camera.SciCam_GetFloatValueEx(xml, 'Gamma', nv) == SCI_CAMERA_OK:
            gamma = nv.dVal
            log.debug('Gamma: val=%.2f', gamma)

        return CameraParams(
            exposure_val=exposure_val,
            exposure_min=exposure_min,
            exposure_max=exposure_max,
            gain_db=gain_db,
            gain_slider_max=gain_slider_max,
            gamma=gamma,
            auto_exposure=auto_exposure,
        )

    def set_auto_exposure(self, enabled: bool) -> None:
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        xml = SciCamDeviceXmlType.SciCam_DeviceXml_Camera
        value = 'Continuous' if enabled else 'Off'
        self._camera.SciCam_SetEnumValueByStringEx(xml, 'ExposureAuto', value)
        log.info('ExposureAuto=%s', value)

    def set_exposure(self, value: float) -> None:
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'ExposureTime', value
        )

    def set_gain(self, value_db: float) -> None:
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'Gain', value_db
        )

    def set_gamma(self, value: float) -> None:
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'Gamma', value
        )

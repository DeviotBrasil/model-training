"""Serviço de alto nível para gerenciamento completo do ciclo de vida da câmera.

Mediaia a comunicação entre a interface gráfica (camada de apresentação) e o SDK
SciCam (camada de infraestrutura), traduzindo operações de usuário em chamadas
do SDK e tratando códigos de erro de forma centralizada.
"""
import socket
import struct
import logging
from dataclasses import dataclass

from app.domain.interfaces.camera_interface import ICameraDevice

log = logging.getLogger('scicam.service')

# Tamanho máximo seguro para pacotes GigE (bytes) — evita fragmentação de rede
PACKET_SIZE_SAFE = 1450

# Inter-packet delay padrão (nanosegundos) — espaça pacotes UDP para aliviar a NIC
# Ajuste para cima (ex: 5000) se ainda ocorrer SCI_ERR_CAMERA_IMAGE_NOT_COMPLETE
INTER_PACKET_DELAY_NS = 2000

# Limites de exposição aplicados pela UI (em microssegundos)
EXPOSURE_MIN = 100
EXPOSURE_MAX = 100_000

# Limite superior de ganho exposto na UI (em dB)
GAIN_MAX_DB = 24.0


@dataclass
class CameraParams:
    """Parâmetros de imagem lidos da câmera após a conexão.

    Usados para inicializar os controles deslizantes e checkboxes da UI com
    os valores reais da câmera, respeitando os limites reportados pelo SDK.
    """

    exposure_val: int         # Valor atual de exposição em microssegundos
    exposure_min: int         # Mínimo de exposição suportado (limitado por EXPOSURE_MIN)
    exposure_max: int         # Máximo de exposição suportado (limitado por EXPOSURE_MAX)
    gain_db: float            # Valor atual de ganho em dB
    gain_slider_max: int      # Máximo do slider de ganho (valor * 10, para 1 casa decimal)
    gamma: float              # Valor atual de gamma
    auto_exposure: bool       # True se a exposição automática estiver ativa


class CameraService:
    """Orquestra as operações da câmera SciCam para a camada de apresentação.

    Encapsula toda a lógica de descoberta, conexão, captura e configuração de
    parâmetros, devolvendo resultados tipados em vez de códigos de erro brutos.
    """

    def __init__(self, camera: ICameraDevice) -> None:
        """Recebe a implementação concreta do dispositivo via injeção de dependência."""
        self._camera = camera
        self._device_created = False  # Rastreia se SciCam_CreateDevice foi chamado com sucesso

    # --- Descoberta de dispositivos ---

    def discover(self, dev_infos, tl_type) -> int:
        """Busca dispositivos de câmera na rede/USB.

        Preenche dev_infos.pDevInfo com os dispositivos encontrados.
        Retorna o código de status do SDK (0 = sucesso).
        """
        nRet = type(self._camera).SciCam_DiscoveryDevices(dev_infos, tl_type)
        count = dev_infos.count if nRet == 0 else 0
        log.info('Discovery: código=%d câmeras=%d', nRet, count)
        return nRet

    def device_label(self, dev, index: int) -> str:
        """Gera o rótulo legível do dispositivo para exibição no combo da UI.

        Para GigE inclui o modelo e o endereço IP; para USB3 inclui apenas o nome.
        """
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

    # --- Ciclo de vida do dispositivo ---

    def connect(self, dev) -> tuple[bool, str]:
        """Cria, abre e configura a câmera selecionada.

        Seqüência: SciCam_CreateDevice → SciCam_OpenDevice → configurações iniciais
        (TriggerMode=Off, tamanho de pacote GigE).

        Returns:
            (True, mensagem_ok) em caso de sucesso, (False, mensagem_erro) em falha.
        """
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
        # Inter-packet delay (ns): reduz rajadas UDP e evita SCI_ERR_CAMERA_IMAGE_NOT_COMPLETE
        self._camera.SciCam_SetIntValueEx(xml, "GevSCPD", INTER_PACKET_DELAY_NS)
        log.info(
            'TriggerMode=Off GevSCPSPacketSize=%d GevSCPD=%d',
            PACKET_SIZE_SAFE, INTER_PACKET_DELAY_NS,
        )
        return True, "Câmera conectada com sucesso"

    def disconnect(self) -> None:
        """Para a captura, fecha e destrói o handle do dispositivo."""
        self._camera.SciCam_StopGrabbing()
        self._camera.SciCam_CloseDevice()
        self._camera.SciCam_DeleteDevice()
        self._device_created = False
        log.info('Câmera desconectada')

    def close_if_open(self) -> None:
        """Fecha o dispositivo com segurança se ele ainda estiver aberto.

        Usado no evento closeEvent da janela principal para garantir que a
        câmera seja liberada antes do encerramento da aplicação.
        """
        try:
            if self._camera.SciCam_IsDeviceOpen():
                self._camera.SciCam_StopGrabbing()
                self._camera.SciCam_CloseDevice()
                self._camera.SciCam_DeleteDevice()
                self._device_created = False
                log.info('Dispositivo fechado ao encerrar')
        except Exception as e:
            log.warning('Erro ao fechar dispositivo: %s', e)

    # --- Captura de imagens ---

    def start_grabbing(self) -> tuple[bool, str]:
        """Inicia o fluxo contínuo de captura de frames.

        Returns:
            (True, mensagem_ok) em sucesso, (False, mensagem_erro) em falha.
        """
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK

        GRAB_TIMEOUT_MS = 3000
        self._camera.SciCam_SetGrabTimeout(GRAB_TIMEOUT_MS)
        log.info('GrabTimeout definido para %d ms', GRAB_TIMEOUT_MS)

        nRet = self._camera.SciCam_StartGrabbing()
        if nRet != SCI_CAMERA_OK:
            log.error('SciCam_StartGrabbing falhou: código %d', nRet)
            return False, f"Erro ao iniciar captura: código {nRet}"
        return True, "Captura iniciada"

    def stop_grabbing(self) -> None:
        """Para o fluxo de captura de frames sem fechar o dispositivo."""
        self._camera.SciCam_StopGrabbing()

    # --- Parâmetros de imagem ---

    def read_params(self) -> CameraParams | None:
        """Lê os parâmetros atuais da câmera (exposição, ganho, gamma).

        Retorna um CameraParams preenchido com os valores/limites reportados pela
        câmera, ou None se a leitura falhar completamente. Valores parcialmente
        lidos usam os valores padrão definidos pelas constantes do módulo.
        """
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
        """Ativa ou desativa a exposição automática contínua na câmera."""
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        xml = SciCamDeviceXmlType.SciCam_DeviceXml_Camera
        value = 'Continuous' if enabled else 'Off'
        self._camera.SciCam_SetEnumValueByStringEx(xml, 'ExposureAuto', value)
        log.info('ExposureAuto=%s', value)

    def set_exposure(self, value: float) -> None:
        """Define o tempo de exposição da câmera em microssegundos."""
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType

    def set_gain(self, value_db: float) -> None:
        """Define o ganho da câmera em dB."""
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'Gain', value_db
        )

    def set_gamma(self, value: float) -> None:
        """Define o valor de gamma da câmera (afeta o brilho percebido na imagem)."""
        from app.infrastructure.camera.sci_cam_info import SciCamDeviceXmlType
        self._camera.SciCam_SetFloatValueEx(
            SciCamDeviceXmlType.SciCam_DeviceXml_Camera, 'Gamma', value
        )

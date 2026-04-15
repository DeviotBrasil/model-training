"""Contrato abstrato que define as operações suportadas por qualquer câmera SciCam.

Isola o restante da aplicação dos detalhes de implementação do SDK, permitindo
a substituição ou simulação da câmera física em testes unitários.
"""
from abc import ABC, abstractmethod
from typing import Any


class ICameraDevice(ABC):
    """Interface abstrata para dispositivos de câmera compatíveis com o SDK SciCam.

    Todos os métodos retornam um código de status inteiro:
      0 (SCI_CAMERA_OK) indica sucesso; valores diferentes indicam erro.
    """

    # --- Descoberta de dispositivos ---

    @staticmethod
    @abstractmethod
    def SciCam_DiscoveryDevices(devInfos: Any, tlType: int) -> int:
        """Busca câmeras disponíveis na rede/USB e preenche a lista devInfos.

        Args:
            devInfos: Estrutura SCI_DEVICE_INFO_LIST que receberá os dispositivos encontrados.
            tlType:   Tipo de transporte (GigE, USB3 ou 0 para todos).
        """
        ...

    # --- Ciclo de vida do dispositivo ---

    @abstractmethod
    def SciCam_CreateDevice(self, devInfo: Any) -> int:
        """Cria um handle interno para o dispositivo selecionado."""
        ...

    @abstractmethod
    def SciCam_DeleteDevice(self) -> int:
        """Destrói o handle e libera recursos alocados para o dispositivo."""
        ...

    @abstractmethod
    def SciCam_OpenDevice(self) -> int:
        """Abre a conexão com o dispositivo (GigE/USB3)."""
        ...

    @abstractmethod
    def SciCam_CloseDevice(self) -> int:
        """Fecha a conexão com o dispositivo e libera a linha de comunicação."""
        ...

    @abstractmethod
    def SciCam_IsDeviceOpen(self) -> bool:
        """Informa se o dispositivo está atualmente conectado e aberto."""
        ...

    # --- Captura de imagens ---

    @abstractmethod
    def SciCam_StartGrabbing(self) -> int:
        """Inicia o fluxo contínuo de captura de frames."""
        ...

    @abstractmethod
    def SciCam_StopGrabbing(self) -> int:
        """Interrompe o fluxo de captura de frames."""
        ...

    @abstractmethod
    def SciCam_Grab(self, ppayload: Any) -> int:
        """Aguarda e retorna o próximo payload (frame) capturado.

        Args:
            ppayload: Ponteiro ctypes que receberá o endereço do payload.
        """
        ...

    @abstractmethod
    def SciCam_FreePayload(self, ppayload: Any) -> int:
        """Libera a memória do payload após o processamento do frame."""
        ...

    # --- Leitura e escrita de parâmetros ---

    @abstractmethod
    def SciCam_GetFloatValueEx(self, xmlType: Any, nodeName: str, nodeVal: Any) -> int:
        """Lê um parâmetro de ponto flutuante da câmera (ex.: ExposureTime, Gain)."""
        ...

    @abstractmethod
    def SciCam_SetFloatValueEx(self, xmlType: Any, nodeName: str, value: float) -> int:
        """Escreve um parâmetro de ponto flutuante na câmera (ex.: ExposureTime, Gain)."""
        ...

    @abstractmethod
    def SciCam_SetIntValueEx(self, xmlType: Any, nodeName: str, value: int) -> int:
        """Escreve um parâmetro inteiro na câmera (ex.: GevSCPSPacketSize)."""
        ...

    @abstractmethod
    def SciCam_GetEnumValueEx(self, xmlType: Any, nodeName: str, nodeVal: Any) -> int:
        """Lê um parâmetro enumerado da câmera (ex.: ExposureAuto)."""
        ...

    @abstractmethod
    def SciCam_SetEnumValueByStringEx(self, xmlType: Any, nodeName: str, value: str) -> int:
        """Escreve um parâmetro enumerado na câmera usando seu valor textual (ex.: 'Off', 'Continuous')."""
        ...

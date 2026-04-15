"""Módulo responsável pela conversão de payloads brutos da câmera em QImage.

O FrameProcessor recebe os dados de pixel entregues pelo SDK da SciCam e os
transforma em objetos QImage prontos para exibição na interface gráfica. A
conversão é feita de forma diferenciada conforme o tipo de pixel:
  - Formatos nativos (Mono8, RGB8, BGR8): cópia direta via NumPy, sem chamada ao SDK.
  - Demais formatos (Bayer, YUV, etc.): conversão delegada à função SciCam_Payload_ConvertImageEx.
"""
import ctypes
import logging
from typing import Callable

import numpy as np
from PyQt6.QtGui import QImage

log = logging.getLogger('scicam.frame')


class FrameProcessor:
    """Converte payloads de câmera SciCam em objetos QImage para exibição na UI.

    Usa o padrão Strategy: formatos simples são convertidos diretamente via
    NumPy (sem custo de chamada ao SDK), enquanto formatos complexos passam pela
    função SciCam_Payload_ConvertImageEx.
    """

    def __init__(self) -> None:
        """Inicializa o processador importando os tipos e funções do SDK sob demanda.

        A importação tardia garante que o módulo pode ser instanciado mesmo antes
        das bibliotecas nativas serem registradas no LD_LIBRARY_PATH.
        """
        from app.infrastructure.camera.sci_cam_payload import (
            SciCamPixelType,
            SciCam_Payload_ConvertImageEx,
        )
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK

        self._SciCamPixelType = SciCamPixelType
        self._convert_ex = SciCam_Payload_ConvertImageEx
        self._SCI_CAMERA_OK = SCI_CAMERA_OK

        # Mapa de tipo de pixel → método de conversão direta (sem SDK)
        self._direct_strategies: dict[int, Callable] = {
            int(SciCamPixelType.Mono8): self._mono8,
            int(SciCamPixelType.RGB8): self._rgb8,
            int(SciCamPixelType.BGR8): self._bgr8,
        }

        # Tipos coloridos que o SDK deve converter para RGB8 antes de exibir
        self._color_types = {
            SciCamPixelType.BayerBG8, SciCamPixelType.BayerGR8,
            SciCamPixelType.BayerRG8, SciCamPixelType.BayerGB8,
            SciCamPixelType.YUV422_8, SciCamPixelType.YUV422_8_UYVY,
            SciCamPixelType.YUV8_UYV,
        }

    def convert(
        self,
        payload_attribute,
        imgdata,
        width: int,
        height: int,
    ) -> QImage | None:
        """Converte um payload de câmera em QImage.

        Seleciona automaticamente a estratégia de conversão pelo tipo de pixel.
        Retorna None se a conversão falhar ou o tipo não for suportado.

        Args:
            payload_attribute: Atributo do payload retornado por SciCam_Payload_GetAttribute.
            imgdata: Ponteiro ctypes para o buffer de imagem bruta.
            width: Largura da imagem em pixels.
            height: Altura da imagem em pixels.

        Returns:
            QImage pronto para exibição, ou None em caso de falha.
        """
        ptype = payload_attribute.imgAttr.pixelType
        strategy = self._direct_strategies.get(int(ptype))
        if strategy:
            return strategy(imgdata, width, height)
        return self._convert_via_sdk(payload_attribute, imgdata, width, height, ptype)

    # --- estratégias diretas (sem chamada ao SDK) ---

    def _mono8(self, imgdata, width: int, height: int) -> QImage:
        """Converte buffer Mono8 (8 bits por pixel, escala de cinza) para QImage."""
        raw = ctypes.string_at(imgdata.value, width * height)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width))
        return QImage(arr.data, width, height, width, QImage.Format.Format_Grayscale8).copy()

    def _rgb8(self, imgdata, width: int, height: int) -> QImage:
        """Converte buffer RGB8 (3 bytes por pixel, ordem R-G-B) para QImage."""
        raw = ctypes.string_at(imgdata.value, width * height * 3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        return QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()

    def _bgr8(self, imgdata, width: int, height: int) -> QImage:
        """Converte buffer BGR8 (3 bytes por pixel, ordem B-G-R) invertendo canais para RGB."""
        raw = ctypes.string_at(imgdata.value, width * height * 3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        arr = arr[:, :, ::-1].copy()  # inverte a ordem dos canais: BGR → RGB
        return QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()

    # --- conversão via SDK (Bayer, YUV e outros formatos não nativos) ---

    def _convert_via_sdk(
        self,
        payload_attribute,
        imgdata,
        width: int,
        height: int,
        ptype,
    ) -> QImage | None:
        """Converte formatos não suportados diretamente usando SciCam_Payload_ConvertImageEx.

        A função do SDK é chamada duas vezes: primeiro para calcular o tamanho
        do buffer de destino (passando None como buffer), depois para realizar a
        conversão de fato alocando o buffer com o tamanho obtido.

        Formatos coloridos (Bayer, YUV) são convertidos para RGB8.
        Demais formatos são convertidos para Mono8 (escala de cinza).
        """
        # Seleciona o formato de destino conforme o tipo de pixel de origem
        dst_type = (
            self._SciCamPixelType.RGB8
            if ptype in self._color_types
            else self._SciCamPixelType.Mono8
        )

        # 1ª chamada: obtém o tamanho necessário do buffer de destino
        dstImgSize = ctypes.c_uint64(0)
        nRet = self._convert_ex(
            payload_attribute.imgAttr, imgdata, dst_type, None, dstImgSize, True, 0
        )
        if nRet != self._SCI_CAMERA_OK or dstImgSize.value == 0:
            return None

        # 2ª chamada: realiza a conversão no buffer alocado
        pDstData = (ctypes.c_ubyte * dstImgSize.value)()
        nRet = self._convert_ex(
            payload_attribute.imgAttr, imgdata, dst_type, pDstData, dstImgSize, True, 0
        )
        if nRet != self._SCI_CAMERA_OK:
            return None

        if dst_type == self._SciCamPixelType.RGB8:
            arr = np.frombuffer(pDstData, dtype=np.uint8).reshape((height, width, 3))
            qimg = QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888)
        else:
            arr = np.frombuffer(pDstData, dtype=np.uint8).reshape((height, width))
            qimg = QImage(arr.data, width, height, width, QImage.Format.Format_Grayscale8)

        return qimg.copy()

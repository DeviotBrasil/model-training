import ctypes
import logging
from typing import Callable

import numpy as np
from PyQt6.QtGui import QImage

log = logging.getLogger('scicam.frame')


class FrameProcessor:
    def __init__(self) -> None:
        from app.infrastructure.camera.sci_cam_payload import (
            SciCamPixelType,
            SciCam_Payload_ConvertImageEx,
        )
        from app.infrastructure.camera.sci_cam_errors import SCI_CAMERA_OK

        self._SciCamPixelType = SciCamPixelType
        self._convert_ex = SciCam_Payload_ConvertImageEx
        self._SCI_CAMERA_OK = SCI_CAMERA_OK

        self._direct_strategies: dict[int, Callable] = {
            int(SciCamPixelType.Mono8): self._mono8,
            int(SciCamPixelType.RGB8): self._rgb8,
            int(SciCamPixelType.BGR8): self._bgr8,
        }

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
        ptype = payload_attribute.imgAttr.pixelType
        strategy = self._direct_strategies.get(int(ptype))
        if strategy:
            return strategy(imgdata, width, height)
        return self._convert_via_sdk(payload_attribute, imgdata, width, height, ptype)

    # --- estratégias diretas ---

    def _mono8(self, imgdata, width: int, height: int) -> QImage:
        raw = ctypes.string_at(imgdata.value, width * height)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width))
        return QImage(arr.data, width, height, width, QImage.Format.Format_Grayscale8).copy()

    def _rgb8(self, imgdata, width: int, height: int) -> QImage:
        raw = ctypes.string_at(imgdata.value, width * height * 3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        return QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()

    def _bgr8(self, imgdata, width: int, height: int) -> QImage:
        raw = ctypes.string_at(imgdata.value, width * height * 3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        arr = arr[:, :, ::-1].copy()
        return QImage(arr.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()

    # --- conversão via SDK (demais pixel types) ---

    def _convert_via_sdk(
        self,
        payload_attribute,
        imgdata,
        width: int,
        height: int,
        ptype,
    ) -> QImage | None:
        dst_type = (
            self._SciCamPixelType.RGB8
            if ptype in self._color_types
            else self._SciCamPixelType.Mono8
        )

        dstImgSize = ctypes.c_uint64(0)
        nRet = self._convert_ex(
            payload_attribute.imgAttr, imgdata, dst_type, None, dstImgSize, True, 0
        )
        if nRet != self._SCI_CAMERA_OK or dstImgSize.value == 0:
            return None

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

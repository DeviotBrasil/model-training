from abc import ABC, abstractmethod
from typing import Any


class ICameraDevice(ABC):
    # --- Discovery ---

    @staticmethod
    @abstractmethod
    def SciCam_DiscoveryDevices(devInfos: Any, tlType: int) -> int: ...

    # --- Lifecycle ---

    @abstractmethod
    def SciCam_CreateDevice(self, devInfo: Any) -> int: ...

    @abstractmethod
    def SciCam_DeleteDevice(self) -> int: ...

    @abstractmethod
    def SciCam_OpenDevice(self) -> int: ...

    @abstractmethod
    def SciCam_CloseDevice(self) -> int: ...

    @abstractmethod
    def SciCam_IsDeviceOpen(self) -> bool: ...

    # --- Grabbing ---

    @abstractmethod
    def SciCam_StartGrabbing(self) -> int: ...

    @abstractmethod
    def SciCam_StopGrabbing(self) -> int: ...

    @abstractmethod
    def SciCam_Grab(self, ppayload: Any) -> int: ...

    @abstractmethod
    def SciCam_FreePayload(self, ppayload: Any) -> int: ...

    # --- Configuration ---

    @abstractmethod
    def SciCam_GetFloatValueEx(self, xmlType: Any, nodeName: str, nodeVal: Any) -> int: ...

    @abstractmethod
    def SciCam_SetFloatValueEx(self, xmlType: Any, nodeName: str, value: float) -> int: ...

    @abstractmethod
    def SciCam_SetIntValueEx(self, xmlType: Any, nodeName: str, value: int) -> int: ...

    @abstractmethod
    def SciCam_GetEnumValueEx(self, xmlType: Any, nodeName: str, nodeVal: Any) -> int: ...

    @abstractmethod
    def SciCam_SetEnumValueByStringEx(self, xmlType: Any, nodeName: str, value: str) -> int: ...

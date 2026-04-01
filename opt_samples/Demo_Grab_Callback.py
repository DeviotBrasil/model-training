# -- coding: utf-8 --

import sys
import ctypes

from SciCam_class import *
m_currentCam =  SciCamera()

#ch:打印相机信息 | en:Print Camera Info
def PrintDeviceInfo(info:SCI_DEVICE_INFO):

     nIp1 = (info.info.gigeInfo.ip & 0x000000ff); #ch: 第一位 | en:the first number
     nIp2 = ((info.info.gigeInfo.ip & 0x0000ff00) >> 8); #ch: 第二位 | en:the second number
     nIp3 = ((info.info.gigeInfo.ip & 0x00ff0000) >> 16); #ch: 第三位 | en:the third number
     nIp4 = ((info.info.gigeInfo.ip & 0xff000000) >> 24); #ch: 第四位 | en:the fourth number
     manufactureName = ''
     for per in info.info.gigeInfo.manufactureName:
          if per == 0:
               break
          manufactureName = manufactureName + chr(per)
     serialNumber = ''
     for per in info.info.gigeInfo.serialNumber:
          if per == 0:
               break
          serialNumber = serialNumber + chr(per)
     modelname = ''
     for per in info.info.gigeInfo.modelName:
          if per == 0:
               break
          modelname = modelname + chr(per)
     #ch: 打印当前相机ip, 制造商,序列号和型号 | en: print current ip, ManufactureName, SN,ModelName
     print("CurrentIp: {}.{}.{}.{}".format(nIp1, nIp2, nIp3, nIp4))
     print("ManufactureName: %s"  %(manufactureName))
     print("Serial Number: %s"  %(serialNumber))
     print("ModelName: %s" % (modelname))

#ch:采集回调接口 | en:Grab Callback interface
def ImageCallBack(payload):
     if(payload == None):
          return

     payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
     nRet = SciCam_Payload_GetAttribute(payload,payloadAttribute)
     if nRet == SCI_CAMERA_OK and payloadAttribute.isComplete:
          print("Get One Frame: width[%d], height[%d], frameID[%d]"
                % (payloadAttribute.imgAttr.width, payloadAttribute.imgAttr.height, payloadAttribute.frameID))
     else:
          print("Failed to get image attributes or frame is incomplete.")



PayloadInfoCallBack = CFUNCTYPE(None, c_void_p)
CALL_BACK_FUN = PayloadInfoCallBack(ImageCallBack)


if __name__ == "__main__":
     devInfos = SCI_DEVICE_INFO_LIST()


     while True:
          #ch:枚举设备 | en:Enum device
          nRet = SciCamera.SciCam_DiscoveryDevices(devInfos, SciCamTLType.SciCam_TLType_Gige)
          if nRet != SCI_CAMERA_OK:
               print("Enum Devices fail! nRet [%d]" % (nRet))
               break;

          if devInfos.count == 0:
               print("Find No Devices!")
               break;

          for ii in range(0, devInfos.count):
               print(' Device[%d]: ' % (ii))
               PrintDeviceInfo(devInfos.pDevInfo[ii])

          index = int(input("Please Input camera index(0-%d):" % (devInfos.count - 1)))
          if index >devInfos.count - 1:
               print("Input error!")
          #ch:选择设备并创建对象 | en:Select device and create Object
          nRet = m_currentCam.SciCam_CreateDevice(devInfos.pDevInfo[index])
          if nRet != SCI_CAMERA_OK:
               print("Create Handle fail! nRet [%d]" % (nRet))
               break

          #ch:打开设备 | en:Open device
          nRet = m_currentCam.SciCam_OpenDevice();
          if nRet != SCI_CAMERA_OK:
               print("Open Device fail! nRet [%d]" % (nRet))
               break

          #ch:注册抓图回调 | en:Register image callback
          nRet = m_currentCam.SciCam_RegisterPayloadCallBack(CALL_BACK_FUN,None,True)
          if nRet != SCI_CAMERA_OK:
               print("Register Image CallBack fail! nRet [%d]" % (nRet))
               break

          #ch:设置触发模式为off | en:Set trigger mode as off
          nRet = m_currentCam.SciCam_SetEnumValueByStringEx(SciCamDeviceXmlType.SciCam_DeviceXml_Camera,"TriggerMode" , "Off")
          if nRet != SCI_CAMERA_OK:
               print("Set Trigger Mode fail! nRet [%d]" % (nRet))
               break


          #ch:开始取流 | en:Start grab image
          nRet = m_currentCam.SciCam_StartGrabbing();
          if nRet != SCI_CAMERA_OK:
               print("Start Grabbing fail! nRet [%d]" % (nRet))
               break

          input("Press AnyKey to Stop...\n")
          #ch:停止取流 | en:Stop grab image
          nRet = m_currentCam.SciCam_StopGrabbing()
          if nRet != SCI_CAMERA_OK:
               print("Stop Grab fail! nRet [%d]" % (nRet))
               break

          #ch:关闭设备 | en:Close device
          nRet = m_currentCam.SciCam_CloseDevice()
          if nRet != SCI_CAMERA_OK:
               print("Close Device fail! nRet [%d]" % (nRet))
               break

          #ch:销毁句柄 | en:Destroy handle
          nRet = m_currentCam.SciCam_DeleteDevice()
          if nRet != SCI_CAMERA_OK:
               print("Delete Device fail! nRet [%d]" % (nRet))
               break
          break

     if m_currentCam:
          m_currentCam.SciCam_DeleteDevice()

     input("Press AnyKey to Exit...")

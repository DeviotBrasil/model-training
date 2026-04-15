# -- coding: utf-8 --

import sys
import ctypes

from SciCam_class import *

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
     print("ManufactureName: %s"  %(manufactureName));
     print("Serial Number: %s"  %(serialNumber));
     print("ModelName: %s" % (modelname));

#ch:检查是否为彩色 | en:Check if the camera is RGB
def IsColor(enType:SciCamPixelType):
     if enType in {
          SciCamPixelType.BayerBG8,SciCamPixelType.BGR8,
          SciCamPixelType.YUV422_8, SciCamPixelType.YUV422_8_UYVY,
          SciCamPixelType.BayerGB8, SciCamPixelType.BayerGB10,
          SciCamPixelType.BayerGB10Packed, SciCamPixelType.BayerGB12,
          SciCamPixelType.BayerGB12Packed
     }:
          return True
     else:
          return False

#ch:检查是否为黑白 | en:Check if the camera is Mono
def IsMono(enType:SciCamPixelType):
     if enType in {
          SciCamPixelType.Mono10,SciCamPixelType.Mono12,
          SciCamPixelType.Mono10p, SciCamPixelType.Mono12p,
          SciCamPixelType.Mono10Packed, SciCamPixelType.Mono12Packed
     }:
          return True
     else:
          return False


if __name__ == "__main__":
     devInfos = SCI_DEVICE_INFO_LIST()
     m_currentCam =  SciCamera()

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
               break
          #ch:选择设备并创建对象 | en:Select device and create Object
          nRet = m_currentCam.SciCam_CreateDevice(devInfos.pDevInfo[index])
          if nRet != SCI_CAMERA_OK:
               print("Create Handle fail! nRet [%d]" % (nRet))
               break

          #ch:打开设备 | en:Open device
          nRet = m_currentCam.SciCam_OpenDevice()
          if nRet != SCI_CAMERA_OK:
               print("Open Device fail! nRet [%d]" % (nRet))
               break

          #ch:设置触发模式为off | en:Set trigger mode as off
          nRet = m_currentCam.SciCam_SetEnumValueByStringEx(SciCamDeviceXmlType.SciCam_DeviceXml_Camera,"TriggerMode" , "Off")
          if nRet != SCI_CAMERA_OK:
               print("Set Trigger Mode fail! nRet [%d]" % (nRet))
               break

          #ch:开始取流 | en:Start grab image
          nRet = m_currentCam.SciCam_StartGrabbing()
          if nRet != SCI_CAMERA_OK:
               print("Start Grabbing fail! nRet [%d]" % (nRet))
               break

          #ch:采集一帧图像 | en:Grab One Image
          ppayload = ctypes.c_void_p()
          nRet = m_currentCam.SciCam_Grab(ppayload)
          if nRet != SCI_CAMERA_OK:
               print("Get payload fail! nRet [%d]" % (nRet))
               break

          #ch:获取payload属性 | en:Get PayloadAttribute
          payloadAttribute = SCI_CAM_PAYLOAD_ATTRIBUTE()
          nRet = SciCam_Payload_GetAttribute(ppayload, payloadAttribute)
          if nRet == SCI_CAMERA_OK:
               print("Get One Frame: width[%d], height[%d], frameID[%d]"
                     %(payloadAttribute.imgAttr.width, payloadAttribute.imgAttr.height, payloadAttribute.frameID))

               #ch:判断是否为2D相机以及帧完整性 | en:Determine if it is a 2D camera and isComplete
               if (payloadAttribute.payloadMode != SciCamPayloadMode.SciCam_PayloadMode_2D or not payloadAttribute.isComplete):
                    print("The Camera payloadMode is not 2D or The frame is not complete")
                    break

               imgdata = ctypes.c_void_p()
               #ch:获取图像数据 | en:Get image data
               nRet = SciCam_Payload_GetImage(ppayload,imgdata)

               ptype =SciCamPixelType.PixelTypeUnknown
               #ch:判断图像格式 | en:Determine whether chunkdata is included
               if IsColor(payloadAttribute.imgAttr.pixelType):
                    ptype = SciCamPixelType.RGB8
                    chFileName = "AfterConvertRGB8.raw"
               elif IsMono(payloadAttribute.imgAttr.pixelType):
                    ptype = SciCamPixelType.Mono8
                    chFileName = "AfterConvertMono8.raw"
               else:
                    print("Don't need to convert!")

               if ptype != SciCamPixelType.PixelTypeUnknown:
                    dstImgSize = ctypes.c_uint64(0)
                    #ch:获取目标图像数据大小 | en:Get the target image data size
                    nRet = SciCam_Payload_ConvertImageEx(payloadAttribute.imgAttr, imgdata, ptype, None, dstImgSize, True,0)
                    if nRet != SCI_CAMERA_OK:
                         print("Convert Pixel Type fail! nRet [%d]" %(nRet));
                         break;
                    pDstData = (ctypes.c_byte*dstImgSize.value)()
                    nRet = SciCam_Payload_ConvertImageEx(payloadAttribute.imgAttr, imgdata, ptype, pDstData, dstImgSize, True,0)
                    fp = open(chFileName ,"wb")
                    if fp==None:
                         print("Open file failed")
                         break
                    fp.write(pDstData)
                    fp.close()
                    print("Convert pixeltype succeed")
          else:
               print("Get Image fail! nRet [%d]" %(nRet))

          #ch:释放帧数据 | en:Free Payload
          nRet = m_currentCam.SciCam_FreePayload(ppayload)

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

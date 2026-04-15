import sys
import os
import socket
import struct
import platform
import ctypes
from ctypes.wintypes import UINT
from ctypes import CFUNCTYPE, c_void_p
from typing import Reversible
from SciCam_class import *

def GetEnumName(enumCls, value):
	for name, member in enumCls.__members__.items():
		if member == value:
			return name
	return None

def uint32_to_ipv4(ip_uint32):
	network_order_ip = socket.htonl(ip_uint32)
	packed_ip = struct.pack("!I", network_order_ip)
	ipv4_address = socket.inet_ntoa(packed_ip)
	return ipv4_address

def ShowDeviceInfo(dev):
	# print device type
	devType = GetEnumName(SciCamDeviceType, dev.devType)
	print('| Device type: ', devType)
	# print device transfer type
	devTlType = GetEnumName(SciCamTLType, dev.tlType)
	print('| Device transfer type: ', devTlType)

	if dev.tlType == SciCamTLType.SciCam_TLType_Gige:

		print('| Camera status: %c' %dev.info.gigeInfo.status)

		camName = ''
		for per in dev.info.gigeInfo.name:
			if per == 0:
				break
			camName = camName + chr(per)
		print('| Camera name: %s' %camName)

		camManufactureName = ''
		for per in dev.info.gigeInfo.manufactureName:
			if per == 0:
				break
			camManufactureName = camManufactureName + chr(per)
		print('| Camera manufactureName: %s' %camManufactureName)

		camModelName = ''
		for per in dev.info.gigeInfo.modelName:
			if per == 0:
				break
			camModelName = camModelName + chr(per)
		print('| Camera modelName: %s' %camModelName)

		camVersion = ''
		for per in dev.info.gigeInfo.version:
			if per == 0:
				break
			camVersion = camVersion + chr(per)
		print('| Camera version: %s' %camVersion)

		camUserDefineName = ''
		for per in dev.info.gigeInfo.userDefineName:
			if per == 0:
				break
			camUserDefineName = camUserDefineName + chr(per)
		print('| Camera userDefineName: %s' %camUserDefineName)

		camSerialNumber = ''
		for per in dev.info.gigeInfo.serialNumber:
			if per == 0:
				break
			camSerialNumber = camSerialNumber + chr(per)
		print('| Camera serialNumber: %s' %camSerialNumber)

		print('| Camera mac: %.2x:%.2x:%.2x:%.2x:%.2x:%.2x' %(dev.info.gigeInfo.mac[0], dev.info.gigeInfo.mac[1], dev.info.gigeInfo.mac[2], dev.info.gigeInfo.mac[3], dev.info.gigeInfo.mac[4], dev.info.gigeInfo.mac[5]))
		camIp = uint32_to_ipv4(dev.info.gigeInfo.ip)
		camMask = uint32_to_ipv4(dev.info.gigeInfo.mask)
		camGateway = uint32_to_ipv4(dev.info.gigeInfo.gateway)
		adapterIp = uint32_to_ipv4(dev.info.gigeInfo.adapterIp)
		adapterMask = uint32_to_ipv4(dev.info.gigeInfo.adapterMask)
		print('| Camera ip: {}'.format(camIp))
		print('| Camera mask: {}'.format(camMask))
		print('| Camera gateway {}'.format(camGateway))
		print('| Camera adapterIp {}'.format(adapterIp))
		print('| Camera adapterMask {}'.format(adapterMask))
		
		camAdapterName = ''
		for per in dev.info.gigeInfo.adapterName:
			if per == 0:
				break
			camAdapterName = camAdapterName + chr(per)
		print('| Camera adapterName: %s' %camAdapterName)

	elif dev.tlType == SciCamTLType.SciCam_TLType_Usb3:

		print('| Camera status: %c' %dev.info.gigeInfo.status)

		camName = ''
		for per in dev.info.usb3Info.name:
			if per == 0:
				break
			camName = camName + chr(per)
		print('| Camera name: {}'.format(camName))

		camManufactureName = ''
		for per in dev.info.usb3Info.manufactureName:
			if per == 0:
				break
			camManufactureName = camManufactureName + chr(per)
		print('| Camera manufactureName: {}'.format(camManufactureName))
		
		camModelName = ''
		for per in dev.info.usb3Info.modelName:
			if per == 0:
				break
			camModelName = camModelName + chr(per)
		print('| Camera modelName: {}'.format(camModelName))
		
		camVersion = ''
		for per in dev.info.usb3Info.version:
			if per == 0:
				break
			camVersion = camVersion + chr(per)
		print('| Camera version: {}'.format(camVersion))
		
		camUserDefineName = ''
		for per in dev.info.usb3Info.userDefineName:
			if per == 0:
				break
			camUserDefineName = camUserDefineName + chr(per)
		print('| Camera userDefineName: {}'.format(camUserDefineName))
		
		camSerialNumber = ''
		for per in dev.info.usb3Info.serialNumber:
			if per == 0:
				break
			camSerialNumber = camSerialNumber + chr(per)
		print('| Camera serialNumber: {}'.format(camSerialNumber))
		
		camGuid = ''
		for per in dev.info.usb3Info.guid:
			if per == 0:
				break
			camGuid = camGuid + chr(per)
		print('| Camera guid: {}'.format(camGuid))

		camU3VVersion = ''
		for per in dev.info.usb3Info.U3VVersion:
			if per == 0:
				break
			camU3VVersion = camU3VVersion + chr(per)
		print('| Camera U3VVersion: {}'.format(camU3VVersion))
		
		camGenCPVersion = ''
		for per in dev.info.usb3Info.GenCPVersion:
			if per == 0:
				break
			camGenCPVersion = camGenCPVersion + chr(per)
		print('| Camera GenCPVersion: {}'.format(camGenCPVersion))
		
	elif dev.tlType == SciCamTLType.SciCam_TLType_CL:
		print('| Card status: %c' %dev.info.clInfo.cardStatus)
		
		cardName = ''
		for per in dev.info.clInfo.cardName:
			if per == 0:
				break
			cardName = cardName + chr(per)
		print('| Card name: {}'.format(cardName))
		
		cardManufacture = ''
		for per in dev.info.clInfo.cardManufacture:
			if per == 0:
				break
			cardManufacture = cardManufacture + chr(per)
		print('| Card manufacture: {}'.format(cardManufacture))
		
		cardModel = ''
		for per in dev.info.clInfo.cardModel:
			if per == 0:
				break
			cardModel = cardModel + chr(per)
		print('| Card model: {}'.format(cardModel))
		
		cardVersion = ''
		for per in dev.info.clInfo.cardVersion:
			if per == 0:
				break
			cardVersion = cardVersion + chr(per)
		print('| Card version: {}'.format(cardVersion))
		
		cardUserDefineName = ''
		for per in dev.info.clInfo.cardUserDefineName:
			if per == 0:
				break
			cardUserDefineName = cardUserDefineName + chr(per)
		print('| Card user define name: {}'.format(cardUserDefineName))
		
		cardSerialNumber = ''
		for per in dev.info.clInfo.cardSerialNumber:
			if per == 0:
				break
			cardSerialNumber = cardSerialNumber + chr(per)
		print('| Card serial number: {}'.format(cardSerialNumber))

		print('| Camera status: %c' %dev.info.clInfo.cameraStatus)
		
		print('| Camera type: {}'.format(dev.info.clInfo.cameraType))
		
		print('| Camera baud: {}'.format(dev.info.clInfo.cameraBaud))
		
		cameraModel = ''
		for per in dev.info.clInfo.cameraModel:
			if per == 0:
				break
			cameraModel = cameraModel + chr(per)
		print('| Camera model: {}'.format(cameraModel))
		
		cameraManufacture = ''
		for per in dev.info.clInfo.cameraManufacture:
			if per == 0:
				break
			cameraManufacture = cameraManufacture + chr(per)
		print('| Camera manufacture: {}'.format(cameraManufacture))
		
		cameraFamily = ''
		for per in dev.info.clInfo.cameraFamily:
			if per == 0:
				break
			cameraFamily = cameraFamily + chr(per)
		print('| Camera family: {}'.format(cameraFamily))
		
		cameraModel = ''
		for per in dev.info.clInfo.cameraModel:
			if per == 0:
				break
			cameraModel = cameraModel + chr(per)
		print('| Camera model: {}'.format(cameraModel))
		
		cameraVersion = ''
		for per in dev.info.clInfo.cameraVersion:
			if per == 0:
				break
			cameraVersion = cameraVersion + chr(per)
		print('| Camera version: {}'.format(cameraVersion))
		
		cameraSerialNumber = ''
		for per in dev.info.clInfo.cameraSerialNumber:
			if per == 0:
				break
			cameraSerialNumber = cameraSerialNumber + chr(per)
		print('| Camera serial number: {}'.format(cameraSerialNumber))
		
		cameraSerialPort = ''
		for per in dev.info.clInfo.cameraSerialPort:
			if per == 0:
				break
			cameraSerialPort = cameraSerialPort + chr(per)
		print('| Camera serial port: {}'.format(cameraSerialPort))
		
		cameraProtocol = ''
		for per in dev.info.clInfo.cameraProtocol:
			if per == 0:
				break
			cameraProtocol = cameraProtocol + chr(per)
		print('| Camera protocol: {}'.format(cameraProtocol))

# Callback function
if platform.system() == "Windows":
	from ctypes import WINFUNCTYPE
	winfun_ctype = WINFUNCTYPE
else:
	winfun_ctype = CFUNCTYPE
PayloadInfoCallBack = winfun_ctype(None, c_void_p, c_void_p)

def payloadCallbackFunc(ppayload, tag):
	payloadMeta = SCI_CAM_LP3D_META()
	reVal = SciCam_Payload_LP3D_GetMeta(ppayload, payloadMeta)
	if reVal != SCI_CAMERA_OK:
		print('Get payload meta failed, return error number: %d' %reVal)
		return
	print('FrameID: %d, Index: %d, IsFinish: %s' %(payloadMeta.frameId, payloadMeta.index, "true" if payloadMeta.finished else "false"))
	# 原则上此处是需要先调用SciCam_Payload_LP3D_GetPointCounts，获取批轮廓点数，根据点数分配内存空间，
	# 接着调用SciCam_Payload_LP3D_GetContour进行一批轮廓的内存拷贝；

	invalid_value = ctypes.c_void_p(0)
	buffer = ctypes.create_string_buffer(m_buffer_size)
	reVal = SciCam_Payload_LP3D_GetContour(ppayload, m_DataType, buffer, invalid_value)
	if reVal != SCI_CAMERA_OK:
		print('Get contour failed, return error number: %d' %reVal)
		
	offset = payloadMeta.index * m_buffer_size
	ctypes.memmove(ctypes.addressof(m_rangeImageData) + offset, buffer, m_buffer_size)
	
	if payloadMeta.finished:
		# 此时能得到完整的轮廓数据，可以直接把m_rangeImageData拷贝进行使用
		pass
	

CALL_BACK_FUN = PayloadInfoCallBack(payloadCallbackFunc)

def discoveryDevices():
	global m_currentDeviceInfo
	print('Please wait ...')

	devInfos = SCI_DEVICE_INFO_LIST()
	reVal = SciCamera.SciCam_DiscoveryDevices(devInfos, SciCamTLType.SciCam_TLType_Unkown)
	if reVal != SCI_CAMERA_OK:
		print('Discovery devices failed, return error number: %d' %reVal)
		return reVal

	print('The number of discovered devices is: ', devInfos.count)
	for index in range(0, devInfos.count):
		print('-------------------------------------------')
		print('| ---- Index: ', index)
		ShowDeviceInfo(devInfos.pDevInfo[index])

	if devInfos.count != 0:
		print('-------------------------------------------')
		m_currentDeviceInfo = devInfos.pDevInfo[int(0)]
	else:
		return -1
	
	return SCI_CAMERA_OK
	
def openDevice():
	reVal = m_currentCam.SciCam_CreateDevice(m_currentDeviceInfo)
	if reVal != SCI_CAMERA_OK:
		print('Create device failed, return error number: %u' %reVal)
		return reVal

	reVal = m_currentCam.SciCam_OpenDevice()
	if reVal != SCI_CAMERA_OK:
		print('Open device failed, return error number: %u' %reVal)
		return reVal
	print('Open device success!')
	return reVal

def closeDevice():
	reVal = m_currentCam.SciCam_CloseDevice();
	if reVal != SCI_CAMERA_OK:
		print('Close device failed, return error number: %u' %reVal)
	else:
		m_currentCam.SciCam_DeleteDevice()
		print('Close device success!')
	return reVal

def registPayloadCallback():
	reVal = m_currentCam.SciCam_RegisterPayloadCallBack(CALL_BACK_FUN, None, True)
	if reVal != SCI_CAMERA_OK:
		print('Register payload callback function failed, return error number: %u' %reVal)
	else:
		print('Register payload callback function success.')
	return reVal

def getDeviceNodes():
	global m_ZMin
	m_ZMin = SCI_NODE_VAL_FLOAT()
	global m_ZMax
	m_ZMax = SCI_NODE_VAL_FLOAT()
	global m_XSizeInfo
	m_XSizeInfo = SCI_NODE_VAL_FLOAT()
	global m_Scaler
	m_Scaler = SCI_NODE_VAL_INT()

	nodeName = 'ZUpSizeInfo'
	reVal = m_currentCam.SciCam_GetFloatValue(nodeName, m_ZMin)
	if reVal != SCI_CAMERA_OK:
		print('Get node value: %s failed, return error number: %u' %(nodeName, reVal))
		return reVal
	nodeName = 'ZDownSizeInfo'
	reVal = m_currentCam.SciCam_GetFloatValue(nodeName, m_ZMax)
	if reVal != SCI_CAMERA_OK:
		print('Get node value: %s failed, return error number: %u' %(nodeName, reVal))
		return reVal
	nodeName = 'XSizeInfo'
	reVal = m_currentCam.SciCam_GetFloatValue(nodeName, m_XSizeInfo)
	if reVal != SCI_CAMERA_OK:
		print('Get node value: %s failed, return error number: %u' %(nodeName, reVal))
		return reVal
	nodeName = 'Scaler'
	reVal = m_currentCam.SciCam_GetIntValue(nodeName, m_Scaler)
	if reVal != SCI_CAMERA_OK:
		print('Get node value: %s failed, return error number: %u' %(nodeName, reVal))
		return reVal
	
	
	print('Get node value success.')
	return reVal

def setParameter():
	global m_DataType
	# 设置采集模式为批量轮廓
	reVal = m_currentCam.SciCam_LP3D_SetGrabType(SciCamLp3dGrabMode.SciCam_GrabMode_LP3D_BatchContour)
	if reVal != SCI_CAMERA_OK:
		print('Set grab type failed, return error number: %u' %reVal)
		return reVal
	else:
		print('Set grab type success.')
	# 设置采集超时
	reVal = m_currentCam.SciCam_SetGrabTimeout(m_Timeout)
	if reVal != SCI_CAMERA_OK:
		print('Set grab timeout failed, return error number: %u' %reVal)
		return reVal
	else:
		print('Set grab timeout success.')
	# 设置批处理量
	reVal = m_currentCam.SciCam_SetIntValue('BatchNumber', m_BatchNumber)
	if reVal != SCI_CAMERA_OK:
		print('Set batch number failed, return error number: %u' %reVal)
		return reVal
	else:
		print('Set batch number success.')
	# 设置总采集行数
	reVal = m_currentCam.SciCam_SetIntValue('AcquisitionLineCount', m_LineCount)
	if reVal != SCI_CAMERA_OK:
		print('Set acquisition line count failed, return error number: %u' %reVal)
		return reVal
	else:
		print('Set acquisition line count success.')
	# 设置采集的轮廓数据位数，如设置失败则代表该激光设备不支持该数据类型设置
	if m_DataType == SciCamPayloadDataType.SciCam_Payload_DataType_USHORT:
		reVal = m_currentCam.SciCam_SetEnumValueByString('DepthDataType', 'Uint16_t')
	elif m_DataType == SciCamPayloadDataType.SciCam_Payload_DataType_INT:
		reVal = m_currentCam.SciCam_SetEnumValueByString('DepthDataType', 'Uint32_t')
		
	if reVal != SCI_CAMERA_OK:
		m_DataType = SciCamPayloadDataType.SciCam_Payload_DataType_INT
		
	return reVal

def startGrab():
	reVal = m_currentCam.SciCam_StartGrabbing()
	if reVal != SCI_CAMERA_OK:
		print('Start grabbing failed, return error number: %u' %reVal)
	else:
		print('Start grabbing success!')
	return reVal
	
def stopGrab():
	reVal = m_currentCam.SciCam_StopGrabbing()
	if reVal != SCI_CAMERA_OK:
		print('Stop grabbing failed, return error number: %u' %reVal)
	else:
		print('Stop grabbing success!')
	return reVal

def main():
	global m_LineCount
	global m_BatchNumber
	global m_Timeout
	global m_DataType
	global m_invalidValue
	global m_rangeImageData
	global m_currentCam
	global m_buffer_size
	
	# ---------------------------------------------------------------------------------------

	m_LineCount = 1000      # 总采集行数
	m_BatchNumber = 100     # 批处理量
	m_Timeout = 5000        # 采集超时

	m_DataType = SciCamPayloadDataType.SciCam_Payload_DataType_INT
	m_invalidValue = float('-inf')
	m_rangeImageData = ctypes.create_string_buffer(3200 * m_LineCount * ctypes.sizeof(ctypes.c_int))
	m_buffer_size = 3200 * m_BatchNumber * ctypes.sizeof(ctypes.c_int)

	# m_DataType = SciCamPayloadDataType.SciCam_Payload_DataType_USHORT
	# m_invalidValue = 0;
	# m_rangeImageData = ctypes.create_string_buffer(3200 * m_LineCount * ctypes.sizeof(ctypes.c_ushort))
	# m_buffer_size = 3200 * m_BatchNumber * ctypes.sizeof(ctypes.c_ushort)

	# ---------------------------------------------------------------------------------------

	m_currentCam = SciCamera()

	reVal = discoveryDevices()
	if reVal != SCI_CAMERA_OK :
		return
	reVal = openDevice()
	if reVal != SCI_CAMERA_OK :
		return
	reVal = registPayloadCallback()
	if reVal != SCI_CAMERA_OK :
		return
	reVal = getDeviceNodes()
	if reVal != SCI_CAMERA_OK :
		return
	reVal = setParameter()
	if reVal != SCI_CAMERA_OK:
		return
	reVal = startGrab()
	if reVal != SCI_CAMERA_OK:
		return
	
	input()

	stopGrab()
	closeDevice()


	
if __name__ == "__main__":
	main()
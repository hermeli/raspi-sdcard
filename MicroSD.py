#!/usr/bin/python
"""
************************************************************************
* MicroSD.py 
* 
* Controller class for MicroSD cards on SPI bus (CS=0)
*
* 04/2014, stefan.wyss@kaba.com
************************************************************************
"""

import spidev
import time
import RPi.GPIO as GPIO

# Command definitions for MMC/SDC
CMD0 = 		0x40+0		# GO_IDLE_STATE 
CMD1 = 		0x40+1		# SEND_OP_COND (MMC)
ACMD41 = 	0xC0+41		# SEND_OP_COND (SDC) 
CMD8 = 		0x40+8		# SEND_IF_COND
CMD9 = 		0x40+9		# SEND_CSD
CMD10 =		0x40+10		# SEND_CID 
CMD12 = 	0x40+12		# STOP_TRANSMISSION
ACMD13 =	0xC0+13		# SD_STATUS (SDC)
CMD16 =		0x40+16		# SET_BLOCKLEN
CMD17 = 	0x40+17		# READ_SINGLE_BLOCK
CMD18 = 	0x40+18		# READ_MULTIPLE_BLOCK
CMD23 = 	0x40+23		# SET_BLOCK_COUNT (MMC)
ACMD23 = 	0xC0+23		# SET_WR_BLK_ERASE_COUNT (SDC)
CMD24 = 	0x40+24		# WRITE_BLOCK
CMD25 = 	0x40+25		# WRITE_MULTIPLE_BLOCK
CMD55 = 	0x40+55		# APP_CMD
CMD58 =		0x40+58		# READ_OCR

class MicroSD:
	""" Controller class for SD/MMC cards """
	def __init__(self):
		self._verbose = False
		self._CRC7Table = [0]*256
		# generate CRC7 table
		self._GenerateCRC7Table()
		self._spi = spidev.SpiDev()
		self._cardType = ""
		self._ocr = [0]*4
		self._nextcmd = 0

	def Init(self):
		GPIO.setmode(GPIO.BCM) 	# set BCM numbering scheme

		# setup SPI port CS1. This is the wrong CS, but assures that
		# CS0 is inactive during the first 80 clock pulses with MISO high.
		self._spi.open(0,1)
		spidev.speed = 100000
		self._spi.mode = 0 		# SD spec. requires mode 0

		# send 80 CLKs with CS* and MOSI high, freq. range 100kHz to 400kHz
		for i in range(10):
			self._spi.xfer2([0xFF])		

		self._spi.open(0,0)		# open SPI port CS0
	
		# send GO_IDLE_STATE (reset CMD)
		answer = self.SendCmd([CMD0,0,0,0,0,0])	
		if answer != 0x01:
			print "Error: SD answer to CMD0 [FAIL]"
			return False
			
		# send CMD8 (interface condition CMD), mandatory for 2.0 spec cards
		answer = self.SendCmd([CMD8,0,0,0x01,0xAA,0])	
		if answer == 0x01:
			# SDHC card type
			for i in range(4): self._ocr[i]=self._spi.xfer2([0xFF])[0]
			if self._verbose:
				print "Found SDHC card with OCR = "+self._BytesToHex(self._ocr);
			
			if (self._ocr[2] == 0x01) and (self._ocr[3] == 0xAA):
				# wait for leaving idle state (ACMD41 with HCS bit)
				# send ACMD41 (CMD55 included!)
				loop = 10
				while loop:
					loop -= 1
					ans = self.SendCmd([ACMD41,0x40,0,0,0,0]) # HCS (high capacity) support bit=1
					if ans == 0x00: break	
					time.sleep(0.01)

				if loop == 0: 
					print "SD answer to ACMD41 timeout [FAIL]"
					return False
						
				if self.SendCmd([CMD58,0,0,0,0,0]) == 0:
					for i in range(4): self._ocr[i]=self._spi.xfer2([0xFF])[0]
					if self._verbose:
						print "Info: OCR = "+self._BytesToHex(self._ocr);
						
					if self._ocr[0] & 0x40:
						self._cardType = "SD2 BLOCK"
					else:
						self._cardType = "SD2"
			
			else:
				print "SD initialization error - unknown state"
				return False
		
		else:
			# SDSC or MMC type
			if self.SendCmd([ACMD41,0,0,0,0,0]) <= 1:
				self._cardType = "SD1"
				self._nextcmd = ACMD41		# SDSC 
			else:
				self._cardType = "MMC"
				self._nextcmd = CMD1		# MMC
			
			loop = 10
			while (loop!=0) and self.SendCmd([self._nextcmd,0,0,0,0,0]):	loop -= 1		# Wait for leaving idle state 
			if (loop == 0) or self._SendCmd([CMD16, 0,0,0,1,0]) != 0:			# Set R/W block length to 512 
				self._cardType = ""
				
		print "SD initialization passed [OK]. Card type is "+self._cardType
		return True
	
	def GetCSD(self):
		""" Receive CSD as a data block (16 bytes) """
		if self.SendCmd([CMD9,0,0,0,0,0]) != 0: return []			# READ_CSD
		data = []
		if self._ReceiveDataBlock(data, 16):
			return data
		else:
			return []
	
	def GetCID(self):
		""" Receive CID as a data block (16 bytes) """
		if self.SendCmd([CMD10,0,0,0,0,0]) != 0: return []			# READ_CID
		data = []
		if self._ReceiveDataBlock(data, 16):
			return data
		else:
			return []
	
	def _ReceiveDataBlock(self, data, count): 
		loop = 10;	# 10 * 10ms timeout
		while loop > 0:
			loop -= 1
			answer = self._spi.xfer2([0xFF])
			if answer[0] != 0xFF: break
		
		if self._verbose:
			print "<" + self._BytesToHex(answer),
			
		if answer[0] != 0xFE: return False
		
		while count > 0:
			data.append(self._spi.xfer2([0xFF])[0])
			data.append(self._spi.xfer2([0xFF])[0])
			data.append(self._spi.xfer2([0xFF])[0])
			data.append(self._spi.xfer2([0xFF])[0])
			count -= 4
		
		self._spi.xfer2([0xFF,0xFF])	# discard CRC16
		if self._verbose:
			print self._BytesToHex(data)
		return True
	
	def SendCmd(self,cmd):
		""" SendCmd is the primary communication function for the SD card. If an advanced
			command is given (type ACMD), the function issues a CMD55 first. """
		if cmd[0] & 0x80:
			cmd[0] &= 0x7F
			answer = self.SendCmd([CMD55,0,0,0,0,0])
			if answer > 1: return answer
		
		cmd[len(cmd)-1] = self._getCRC(cmd)
		if self._verbose:
			print '>'+self._BytesToHex(cmd),
			print ''
		self._spi.xfer2(cmd)	
		retries = 10
		while retries:
			retries -= 1
			answer = self._spi.xfer2([0xFF])	
			if answer[0] & 0x80 == 0: break
		
		if self._verbose:
			print '<'+self._BytesToHex(answer),
			print ''
		return answer[0]
			
	def _GenerateCRC7Table(self):
		""" SPI communication does not need CRC7 except for the first 
			initialization commands. """
		CRCPoly = 0x89
		for i in xrange(0,255):
			if i & 0x80:
				self._CRC7Table[i] = i ^ CRCPoly
			else:
				self._CRC7Table[i] = i
			for j in range(1,8):
				self._CRC7Table[i] <<= 1
				if (self._CRC7Table[i] & 0x80):
					self._CRC7Table[i] ^= CRCPoly
				
	def _getCRC(self,message):
		""" CRC7 is pasted into the last byte of the message """
		CRC = 0
		for i in xrange(0,len(message)-1):
			CRC = self._CRC7Table[(CRC << 1) ^ message[i]]		
		return (CRC<<1)|0x01		
		
	def _BytesToHex(self,Bytes):
		return ''.join(["0x%02X " % x for x in Bytes]).strip()

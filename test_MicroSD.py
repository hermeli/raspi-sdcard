#!/usr/bin/python
"""
************************************************************************
* test_MicroSD.py 
* 
* Test progrm for MicroSD class
*
* 04/2014, stefan.wyss@kaba.com
************************************************************************
"""
from MicroSD import MicroSD

def BytesToHex(Bytes):
		return ''.join(["0x%02X " % x for x in Bytes]).strip()

sd = MicroSD()
sd._verbose = False
if ~sd.Init(): exit
print "CSD: " + BytesToHex(sd.GetCSD()) 
CID = sd.GetCID()
print "CID: " + BytesToHex(CID) 
print "-> Product Name (PNM): "+chr(CID[3])+chr(CID[4])+chr(CID[5])+chr(CID[6])+chr(CID[7])
print "-> Serial Number (PSN): "+BytesToHex([CID[9],CID[10],CID[11],CID[12]]) 

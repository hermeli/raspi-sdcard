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
import spidev
import time
import RPi.GPIO as GPIO
from MicroSD import MicroSD

sd = MicroSD()
sd._verbose = False
sd.Init()

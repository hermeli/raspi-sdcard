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

sd = MicroSD()
sd._verbose = False
sd.Init()

#!/usr/bin/env python -u

"""
2018-10-27
Tentacle T3 for Raspberry Pi to MODBUS TCP example

Requirements:
    git clone https://github.com/ljean/modbus-tk.git
    cd modbus-tk
    sudo python3 setup.py install
    cd ~

    wget https://raw.githubusercontent.com/AtlasScientific/Raspberry-Pi-sample-code/master/i2c.py
    mv i2c.py AtlasI2C.py

    touch __init__.py

Usage:
    sudo python3 main.py
"""

""" 
modbus-tk
https://github.com/ljean/modbus-tk
"""

import sys
import time
from math import pi
import struct

import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp

from AtlasI2C import *

def mb_set_float(addr, val):
    """ Write a float to a pair of MODBUS registers """
    j = struct.unpack('<HH',struct.pack('<f', val))
    slave_1.set_values('ro', addr, j)
    return val

def mb_get_float(addr):
    """ Read a float from a pair of MODBUS registers """
    i2, i1 = slave_1.get_values('ro', addr, 2)
    return struct.unpack('>f',struct.pack('>HH',i1,i2))[0]

""" 
Atlas Scientific
https://raw.githubusercontent.com/AtlasScientific/Raspberry-Pi-sample-code/master/i2c.py
https://github.com/whitebox-labs/tentacle-raspi-oshw

The example code is good so extend the base class. 

Rename i2c.py to AtlasI2C.py to avoid name conflicts and add a file named __init__.py to 
the working directory.
"""

class AtlasEZO(AtlasI2C):
    address_ph = 99
    address_ec = 100
    address_rtd = 102

    def read_rtd(self):
        """ Read temperature """
        self.set_i2c_address(self.address_rtd)
        return float((self.query("R").split(" ")[2]).rstrip('\0'))
    
    def read_ec(self):
        """ Read electrical conductivity """
        self.set_i2c_address(self.address_ec)
        return float((self.query("R").split(" ")[2]).rstrip('\0'))

    def read_ph(self):
        """ Read pH """
        self.set_i2c_address(self.address_ph)
        return float((self.query("R").split(" ")[2]).rstrip('\0'))

    def temperature_compensation(self, t):
        """ Temperature compensate electrical conductivity and pH """
        cmd = "T,%f" % t
        self.set_i2c_address(self.address_ec)
        self.query(cmd)
        print(self.query("T,?"))
        self.set_i2c_address(self.address_ph)
        self.query(cmd)
        print(self.query("T,?"))

if __name__ == "__main__":
    try:
        """ Initialize the MODBUS TCP slave """        
        mb_start = 40001
        mb_len = 10
        server = modbus_tcp.TcpServer(address='0.0.0.0')
        server.start()
        slave_1 = server.add_slave(1)
        slave_1.add_block('ro', cst.HOLDING_REGISTERS, mb_start, mb_len)
        print("Ready")

        ezo = AtlasEZO()

        tc_count = 0
        while True:
            """ 40001   Quality Control (3.14159265359) """
            mb_set_float(40001, pi)
            print("40001  QC: %f" % mb_get_float(40001))
            
            """ 40003   RTD (C) """
            rtd = ezo.read_rtd()
            mb_set_float(40003, rtd)
            print("40003 RTD: %f (C)" % mb_get_float(40003))

            """ 40005   TDS (ppm) """
            mb_set_float(40005, ezo.read_ec())
            print("40005  EC: %f (ppm)" % mb_get_float(40005))

            """ 40007   PH """
            mb_set_float(40007, ezo.read_ph())
            print("40007  PH: %f" % mb_get_float(40007))

            print()

            """
            Apply temperature compensation at about one minute intervals
            """
            tc_count += 1
            if tc_count > 14:
                tc_count = 0
                print("Updating temperature compensation")
                ezo.temperature_compensation(rtd)
                print()
            
            time.sleep(1)

            """ 
            modpoll -0 -1 -m tcp -t 4:float -r 40001 -c 1 -o 3 192.168.x.x

            -0          First reference is 0 (PDU addressing) instead 1
            -1          Poll only once, otherwise poll every second
            -m tcp      MODBUS/TCP protocol
            -t 4:float  32-bit float data type in output (holding) register table
            -c 4        Number of values to poll (1-100, 1 is default)
            -o 3        Time-out in seconds (0.01 - 10.0, 1.0 s is default)
            """

    finally:
        server.stop()
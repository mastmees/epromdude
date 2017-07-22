# The MIT License (MIT)
#
# Copyright (c) 2017 Madis Kaal <mast@nomad.ee>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import time
import sys
import binascii
from hardware import eprom

device=eprom()

def cleanup():
  global device
  device.power_off()
  device.power_on()
  device.set_type(0)
  device.set_led(0)
  device.power_off()

cleanup()

def initialize():
  device.power_off()
  device.power_on()
  device.reset()
  device.set_led(1)
  device.set_type(1)
  
devices = {
  "2764":   { "size": 64/8*1024, "type":1 },
  "27128":  { "size": 128/8*1024,"type":2 },
  "27256":  { "size": 256/8*1024,"type":3 },
  "27512":  { "size": 512/8*1024,"type":4 }
}

voltages = {
  "5v":  {"type":0},
  "12v": {"type":1},
  "21v": {"type":2}
}

initialize()

def menu():
  print ""
  print "5 - set VPP to 5V"
  print "1 - set VPP to 12V"
  print "2 - set VPP to 21V"
  
  print "p - connect VPP to pin 1"
  print "P - connect VPP to pin 22"
  print "L - led on"
  print "l - led off"
  print "r - read data bits"
  
  print "c - address bits to 0000"
  print "a - address bits to 5555"
  print "A - address bits to AAAA"
  
  print "q - quit"
  
  print ">",
  
menu()
while 1:
  c=sys.stdin.read(1)
  if c=='\n':
    continue
  elif c=='c':
    device.seek(0)
  elif c=='a':
    device.seek(0x5555)
  elif c=='A':
    device.seek(0xaaaa)
  elif c=='5':
    device.set_vpp(0)
  elif c=='1':
    device.set_vpp(1)
  elif c=='2':  
    device.set_vpp(2)
  elif c=='p':
    device.set_type(1)
  elif c=='P':
    device.set_type(4)
  elif c=='q':
    break
  elif c=='L':
    device.set_led(1)
  elif c=='l':
    device.set_led(0)
  elif c=='r':
    print "%2x"%device.read()
  menu()
  
cleanup()

    

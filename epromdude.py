# The MIT License (MIT)
#
# Copyright (c) 2016,2017 Madis Kaal <mast@nomad.ee>
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

# You need PyUSB (https://github.com/walac/pyusb/blob/master/docs/tutorial.rst)
#
import time
import sys
import binascii
from hardware import eprom


class FormatException(Exception):
  def __init__(self, value):
     self.value = value
  def __str__(self):
     return str(self.value)

format=''
filename=None
devicename=None
operation=''
address=0
readcount=0
verify=False
voltage=None
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
  global device,devicename,voltage
  device.power_off()
  device.power_on()
  device.reset()
  device.set_led(1)
  device.set_type(devices[devicename]["type"])
  if voltage!=None:
    device.set_vpp(voltages[voltage]["type"])

def printhelp():
  print "use: python epromdude.py --write --device devicename --vpp voltage"
  print "              [--adr epromadr --count bytecount] [--hex|--bin] filename"
  print "     python epromdude.py --read --device devicename [--adr epromadr --count bytecount] filename"
  print ""
  print " For write adr and count arguments only apply to binary files"
  print " count and adr can be decimal, or hex with 0x prefix"
  print ""
  print "supported devices:\n    ",
  for d in devices:
    print d,
  print ""
  print "supported voltages:\n    ",
  for d in voltages:
    print d,
  print ""
  exit(0)

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

args=sys.argv[1:]

while len(args):
  arg=args.pop(0)
  if arg=='--hex':
    format='hex'
  elif arg=='--bin':
    format='bin'
  elif arg=='--verify':
    verify=True
  elif arg=='--read':
    operation='read'
  elif arg=='--write':
    operation='write'
  elif arg=='--adr':
    address=int(args.pop(0),0)
    continue
  elif arg=='--count':
    readcount=int(args.pop(0),0)
    continue
  elif arg=='--device':
    devicename=args.pop(0).lower()
    if devicename not in devices:
      print "unsupported device %s"%devicename
      exit(1)
  elif arg=='--vpp':
    voltage=args.pop(0).lower()
    if voltage not in voltage:
      print "unsupported voltage %s"%voltage
      exit(1)
  elif arg in ('-h','--h','--help'):
    printhelp()
  else:
    filename=arg

if devicename==None:
  printhelp()

if filename==None:
  printhelp()

if voltage==None and operation=='write':
  printhelp()
  
def program_hex():
  global address,device,devicename
  initialize()
  memsize=devices[devicename]["size"]
  baseadr=0
  for l in open(filename):
    if l[0]!=":":
      raise FormatException("%s does not begin with ':'"%l)
    b=binascii.unhexlify(l[1:].strip())
    bytecount=ord(b[0])
    adr=(ord(b[1])<<8)|ord(b[2])
    type=ord(b[3])
    data=[]
    for c in b[4:bytecount+4]:
      data.append(ord(c))
    chksum=ord(b[bytecount+4])
    sum=0
    for c in b[0:bytecount+4]:
      sum=sum+ord(c)
    sum=(~sum)&0xff
    sum=(sum+1)&0xff
    if sum!=chksum:
      raise FormatException("Invalid checksum %02x!=%02x"%(chksum,sum))
    if type==0: #data
      beginadr=baseadr+adr
      if beginadr+len(data)>memsize:
        raise FormatException("Data exceeds memory size") 
      print "\r%08x"%(beginadr),
      sys.stdout.flush()
      device.seek(beginadr)
      for c in data:
        device.write_inca(c)
        if device.is_error():
          raise FormatException("Programming failed")
    elif type==1:
      break
    elif type==2:
      if bytecount!=2:
        raise FormatException("Extended segment address not 2 bytes")
      a=(ord(data[0])<<8)|ord(data[1])
      baseadr=a*16
    elif type==3:
      continue    #CS:IP register content, just ignore it
    elif type==4:
      if bytecount!=2:
        raise FormatException("Extended linear address not 2 bytes")
      a=(ord(data[0])<<8)|ord(data[1])
      baseadr=a<<16
    elif type==5:
      continue    #EIP register content, also ignored
  print ""
  cleanup()

def program_binary():
  global address,device,devicename,readcount
  initialize()
  memsize=devices[devicename]["size"]
  if readcount==0:
    readcount=devices[devicename]["size"]-address
  f=open(filename,"rb")
  s=f.read(readcount)
  f.close()
  if address+len(s)>memsize:
      raise FormatException("Data exceeds memory size")
  device.seek(address)
  for c in s:
    if address&15==0:
      print "%08x\r"%(address),
      sys.stdout.flush()
    device.write_inca(ord(c))
    if device.is_error():
      raise FormatException("Programming failed")
    address+=1
    readcount-=1
    if readcount<=0:
      break
  print "%08x\r"%(address-1),
  cleanup()
  print ""
  return


if operation=='write':
  if format=='':
    if '.hex' in filename:
      format='hex'
    else:
      format='.bin'
  print "programming device"
  try:
    if format=='hex':
      program_hex()
    else:
      program_binary()
  except FormatException as e:
    print ""
    print e
    cleanup()
    exit(1)
  except IOError as e:
    print ""
    print e
    cleanup()
    exit(1)
  except KeyboardInterrupt:
    cleanup()
    exit(1)
  exit(0)
  
if operation=='read':
  if readcount==0:
    readcount=devices[devicename]["size"]-address
  print "reading %d bytes from %08x into %s"%(readcount,address,filename)
  initialize()
  device.seek(address);
  try:
    s=""
    while readcount:
      if address&15==0:
        print "\r%08x"%address,
      sys.stdout.flush()
      ch=device.read_inca()
      s=s+chr(ch)
      readcount-=1
      address+=1
    print "\r%08x"%(address-1),
    f=open(filename,"wb")
    f.write(s)
    f.close()
  except IOError as e:
    print e
  except KeyboardInterrupt:
    cleanup()
    exit(1)
  print ""
  cleanup()
  exit(0)
  
printhelp()


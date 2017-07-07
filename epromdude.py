# The MIT License (MIT)
#
# Copyright (c) 2016 Madis Kaal <mast@nomad.ee>
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
import usb.core
import usb.util
import time
import sys
import binascii

class usbtiny:

  def __init__(self):
    self.USBTINY_ECHO = 0          #echo test
    self.USBTINY_READ = 1          #read port B pins
    self.USBTINY_WRITE = 2         #write byte to port B
    self.USBTINY_CLR = 3           #clear PORTB bit, value=bit number (0..7)
    self.USBTINY_SET = 4           #set PORTB bit, value=bit number (0..7)
    self.USBTINY_POWERUP = 5       #apply power and enable buffers, value=sck-period, index=RESET
    self.USBTINY_POWERDOWN = 6     #remove power from chip, disable buffers
    self.USBTINY_SPI = 7           #spi command, value=c1c0, index=c3c2
    self.USBTINY_POLL_BYTES = 8    #set poll bytes for write, value=p1p2
    self.USBTINY_FLASH_READ = 9    #read flash, index=address, USB_IN reads data
    self.USBTINY_FLASH_WRITE = 10  #write flash, index=address,value=timeout, USB_OUT writes data
    self.USBTINY_EEPROM_READ = 11  #read eeprom, index=address, USB_IN reads data
    self.USBTINY_EEPROM_WRITE = 12 #write eeprom, index=address,value=timeout, USB_OUT writes data
    self.USBTINY_DDRWRITE = 13     #set port direction, value=DDRB register value
    self.USBTINY_SPI1 = 14         #single byte SPI command, value=command
    # these values came from avrdude (http://www.nongnu.org/avrdude/)
    self.USBTINY_RESET_LOW = 0     #for POWERUP command
    self.USBTINY_RESET_HIGH = 1    #for POWERUP command
    self.USBTINY_SCK_MIN = 1       #min sck-period for POWERUP
    self.USBTINY_SCK_MAX = 250     #max sck-period for POWERUP
    self.USBTINY_SCK_DEFAULT = 10  #default sck-period to use for POWERUP
    self.USBTINY_CHUNK_SIZE = 128
    self.USBTINY_USB_TIMEOUT = 500 #timeout value for writes
    # search for usbtiny
    self.dev=usb.core.find(idVendor=0x1781,idProduct=0x0c9f)
    if self.dev==None:
      print "USBtiny programmer not connected"
      exit(1)
    self.dev.set_configuration()
    return

  def _usb_control(self,req,val,index,retlen=0):
    return self.dev.ctrl_transfer(usb.util.CTRL_IN|usb.util.CTRL_RECIPIENT_DEVICE|usb.util.CTRL_TYPE_VENDOR,req,val,index,retlen)
    
  def power_on(self):
    self._usb_control(self.USBTINY_POWERUP, 20, self.USBTINY_RESET_LOW ) # slow SPI CLK to 20usec

  def power_off(self):
    self._usb_control(self.USBTINY_POWERDOWN,0,0)

  def write(self,portbbits):
    self._usb_control(self.USBTINY_WRITE,portbbits,0)
    
  def read(self):
    return self._usb_control(self.USBTINY_READ,0,0,1)
  
  def spi1(self,b):
    return self._usb_control(self.USBTINY_SPI1,b,0,1)
  
  def spi4(self,d1d0,d3d2):
    return self._usb_control(self.USBTINY_SPI,d1d0,d3d2,4)
    
  def clr(self,bit):
    self._usb_control(self.USBTINY_CLR,bit,0)

  def set(self,bit):
    self._usb_control(self.USBTINY_SET,bit,0)

class eprom:

  def __init__(self):
    self.dev=usbtiny()
  
  def power_on(self):
    self.dev.power_on()
  
  def power_off(self):
    self.dev.power_off()
    
  def command(self,cmd,address,data):
    d=self.dev.spi4((address&0xff00)|cmd,(data<<8)|(address&0xff))
    return d

  def reset(self):
    self.command(0,0,0)
  
  def is_busy(self):
    r=self.command(1,0,0)
    return r[2]&1!=0
  
  def is_error(self):
    r=self.command(1,0,0)
    return r[2]&2!=0
    
  def ready_wait(self):
    while self.is_busy():
      pass
    
  def seek(self,address):
    self.command(2,address,0)
    self.ready_wait()
   
  def set_type(self,type):
    self.command(3,0,type)
    self.ready_wait()
    
  def set_vpp(self,vpp):
    self.command(4,0,vpp)
    self.ready_wait()
  
  def set_led(self,led):
    self.command(9,0,led)
    self.ready_wait()
    
  def write(self,d):
    self.command(5,0,d)
    self.ready_wait()
  
  def read(self):
    r=self.command(6,0,0)
    return r[3]
    
  def write_inca(self,d):
    self.command(7,0,d)
    self.ready_wait()
    
  def read_inca(self):
    r=self.command(8,0,0)
    return r[3]

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


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

# You need PyUSB (https://github.com/walac/pyusb/blob/master/docs/tutorial.rst)
#
import usb.core
import usb.util

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
    self.d=self.dev.spi4((address&0xff00)|cmd,(data<<8)|(address&0xff))
    return self.d

  def reset(self):
    self.command(0,0,0)
  
  def is_busy(self):
    self.r=self.command(1,0,0)
    return self.r[2]&1!=0
  
  def is_error(self):
    self.r=self.command(1,0,0)
    return self.r[2]&2!=0
    
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
    self.r=self.command(6,0,0)
    return self.r[3]
    
  def write_inca(self,d):
    self.command(7,0,d)
    self.ready_wait()
    
  def read_inca(self):
    self.r=self.command(8,0,0)
    return self.r[3]


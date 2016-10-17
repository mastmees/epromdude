/* The MIT License (MIT)
 
  Copyright (c) 2016 Madis Kaal <mast@nomad.ee>
 
  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:
 
  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.
 
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
*/
#ifndef __eprom_hpp__
#define __eprom_hpp__
#include <avr/io.h>
#include <util/delay.h>

#ifndef COUNTOF
#define COUNTOF(a) (sizeof(a)/sizeof(a[0]))
#endif

class EPROM
{
public:
  enum DEVICE { _UNKNOWN=0, _2764=1, _27128=2, _27256=3, _27512=4 };
  enum VPP { _5V=0, _12V=1, _21V=2 };
  EPROM();
  void set_vpp(VPP voltage);
  void set_type(DEVICE type);
  void reset();
  uint8_t read();
  uint8_t write(uint8_t b);
  void address_reset(uint16_t adr=0);
  void address_next();
  void address_seek(uint16_t a);

private:
  DEVICE type;
  VPP voltage;
  uint16_t adr;
  void writepulse_on();
  void writepulse_off();
  uint8_t verify_read();

};

#endif

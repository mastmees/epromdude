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
#include "eprom.hpp"

// for 'VPP on' indicator led
#define led_on() PORTD&=~(_BV(PORTD2))
#define led_off() PORTD|=_BV(PORTD2)
// these are for manipulating eprom control signals
#define ce_low()   PORTD&=~(_BV(PORTD4))
#define ce_high()  PORTD|=_BV(PORTD4)
#define pgm_low()  PORTA&=~(_BV(PORTA2))
#define pgm_high() PORTA|=_BV(PORTA2)
#define oe_low()   PORTD&=~(_BV(PORTD5))
#define oe_high()  PORTD|=_BV(PORTD5)

EPROM::EPROM() : type(_UNKNOWN), voltage(_5V), adr(0)
{
}

// reset CD4040 and set 4 high address bits. for nonzero
// address caller needs to clock the lower 12 address bits
void EPROM::address_reset(uint16_t address)
{
  adr=address;
  uint8_t ao;
  PORTA |= _BV(PORTA5);  // CD4040 reset high
  // some address pins have other functions for
  // smaller size eproms, set these appropriately
  switch (type) {
    case _27512: // all address pins in use
      ao=0;
      break;
    case _27256:
      ao=0x8; // VPP high for 256
      break;
    default:
      ao=0xc; // /PGM and VPP high for 64,128      
      break;
  }
  PORTA &= (~_BV(PORTA5)); // CD4040 reset low, 12 lower address bits are 0 now
  PORTA = (PORTA&0xf0)|((adr>>12)&0x0f)|ao; // set top 4 address bits
}
  
void EPROM::address_next()
{
  adr++;                // keep track of address counter for higher bits
  uint8_t ao;
  PORTA |= _BV(PORTA4); // CD4040 clock high
  switch (type) {
    case _27512:
      ao=0;
      break;
    case _27256:
      ao=0x8; // VPP high for 256
      break;
    default:
      ao=0xc; // /PGM and VPP high for 64,128      
      break;
  }
  PORTA &= (~_BV(PORTA4)); // CD4040 clock low, 12 lower address bits are now +1
  PORTA = (PORTA&0xf0)|((adr>>12)&0x0f)|ao; // set higher address bits
}

void EPROM::address_seek(uint16_t a)
{
  address_reset(a);
  a&=0xfff;  // for low 12 addresses we need to clock the CD4040
  while (a) {
    PORTA |= _BV(PORTA4); // CD4040 clock high
    a--;
    PORTA &= (~_BV(PORTA4)); // CD4040 clock low, 12 lower address bits are now +1
  }
}


void EPROM::set_vpp(VPP voltage)
{
  this->voltage=voltage;
  PORTD&=~(_BV(PORTD6)|_BV(PORTD7)); // turn both voltage control fets off
  switch (voltage) {
    default:
    case _5V:
      led_off();
      break;
    case _12V:
      PORTD|=_BV(PORTD6);
      led_on();
      break;
    case _21V:
      PORTD|=_BV(PORTD7);
      led_on();
      break;
  }
  _delay_ms(50);  // allow a little time for voltage to stabilize
}

// setting the type of eprom device forces VPP to 5V
// in other words, always set the device type first
void EPROM::set_type(DEVICE type)
{
  set_vpp(_5V); // first switch the VPP off
  _delay_ms(250); // and allow excess voltage to drain
  this->type=type;
  if (type==_27512) {
    PORTD|=_BV(PORTD3); // reconfigure for 27512 by pulling relay
  }
  else {
    PORTD&=~(_BV(PORTD3));
  }
  _delay_ms(100); // allow time for relay to act
}

void EPROM::reset()
{
  set_vpp(_5V); // drop VPP, but keep the type set
  address_reset();
}

uint8_t EPROM::read()
{
  uint8_t d;
  DDRC=0x00;    // make port C all input
  PORTC=0xff;   // pull-ups on
  PORTD&=0xcf;  // CE, OE low
  _delay_us(5); // the transistor switch is slow, signal fall time is ~2.5us 
  d=PINC;
  PORTD|=0x30;  // CE, OE high
  _delay_us(2); // just to be on safe side, allow for slow rise time too
  return d;
}

//  2764 write: VPP vpp, CE low, PGM(A14) low
//      verify: VPP vpp, CE low, PGM(A14) high, OE low
// 27128 write: VPP vpp, CE low, PGM(A14) low
//      verify: VPP vpp, CE low, PGM(A14) high, OE low
// 27256 write: VPP vpp, OE high, CE low
//      verify: VPP vpp, OE low, CE low/high
// 27512 write: OE/VPP vpp, CE low
//      verify: OE/VPP low, CE low
//

// start programming pulse
void EPROM::writepulse_on()
{
  switch (type) {
    case _2764:
    case _27128:
      pgm_high();
      oe_high();
      ce_low();
      pgm_low();
      break;
    case _27256:
    case _27512:
      oe_high();
      ce_low();
      break;
    default:
      break;
  }
}

// end programming pulse, leave eprom
// prepared for verify mode, but outputs
// still high-z, so that MCU port direction can be
// changed
void EPROM::writepulse_off()
{
  switch (type) {
    case _2764:
    case _27128:
      pgm_high();
      break;
    case _27256:
    case _27512:
      ce_high();
      break;
    default:
      break;
  }
}

// read the byte out for verification
// during programming (see above table)
uint8_t EPROM::verify_read()
{
  uint8_t d;
  DDRC=0x00;   // make port C all input
  PORTC=0xff;  // pull-ups on
  switch (type) {
    case _2764:
    case _27128:
      oe_low();
      _delay_us(5);
      d=PINC;
      oe_high();
      _delay_us(2);
      break;
    case _27256:
    case _27512:
      oe_low();
      ce_low();
      _delay_us(5);
      d=PINC;
      ce_high();
      oe_high();
      _delay_us(2);
      break;
    default:
      d=0;
      break;
  }
  return d;
}

// write a byte at current address with Intel intelligent programming
// algorithm, assumes VPP is already set up
uint8_t EPROM::write(uint8_t b)
{
  uint8_t d,pulselen=1;
  d=read();
  if (d==b)    // no need to write if already correct value
    return d;
  while (pulselen<16) {
    DDRC=0xff; // data bus to outputs
    PORTC=b;   // put data byte on EPROM data signal
    writepulse_on();
    _delay_ms(1); // one 1ms programming pulse
    writepulse_off();
    d=verify_read(); // see if we got the bits programmed
    if (d==b)
      break;
    pulselen++;   // if not, try again and keep count
  }
  if (pulselen>=16)
    return d; // faulty eprom, return value that we were able to write
  // the value is now in eprom, 'fix it' by issuing a longer programming
  // pulse (4 times the milliseconds that it took to change the bits)
  DDRC=0xff;
  PORTC=b;
  writepulse_on();
  pulselen*=4;
  while (pulselen--)
    _delay_ms(1); // this function only takes constant as argument
  writepulse_off();
  DDRC=0x00;     // make port C all input
  PORTC=0xff;    // pull-ups on
  _delay_us(2);  // just a small safety margin
  return d;
}

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
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include <string.h>

#include "eprom.hpp"

EPROM eprom;

enum PRGCOMMANDS { RESET,READ_STATUS,SEEK,SET_TYPE,SET_VPP,WRITE,READ,WRITE_INCA,READ_INCA };
typedef uint32_t COMMAND;

struct SPISLAVE 
{
uint8_t state;
COMMAND command;
COMMAND queue[4];
uint8_t head,tail,count,rdata,error,sdata;
 
  // return number of queued commands waiting to be processed
  uint8_t command_ready()
  {
    return count;
  } 
  
  // take next command from queue and process it
  void process_command()
  {
    if (!count)
      return;
    COMMAND c=queue[tail++]; // take command out of queue but do not
    tail=tail%COUNTOF(queue); // decrease the count until processing completed
    uint8_t cmd=c>>24;    // extract the values for less cycles later
    uint8_t data=c&0xff;
    uint16_t adr=c>>8;
    // any command that changes EPROM address should also read out
    // the EPROM data at that address so that it can be sent in SPI
    // responses
    // some of the commands take significant time to process, and
    // the host machine should read and check the status before issuing
    // next command
    // write errors are only cleared with RESET, and next WRITE
    switch (cmd) {
      case RESET:
        eprom.reset();
        rdata=eprom.read();
        error=0;
        break;
      case SEEK:
        eprom.address_seek(adr);
        rdata=eprom.read();
        break;
      case SET_TYPE:
        //enum DEVICE { _UNKNOWN, _2764, _27128, _27256, _27512 };
        eprom.set_type((EPROM::DEVICE)data);
        break;
      case SET_VPP:
        // enum VPP { _5V, _12V, _21V };
        eprom.set_vpp((EPROM::VPP)data);
        break;
      case WRITE:
        // write commands set the data that we were actually
        // able to store to EPROM. if it is not what is wanted
        // the error flag will also be set
        error=0;
        rdata=eprom.write(data);
        if (rdata!=data)
          error=0x02;
        break;
      case WRITE_INCA:
        // this misbehaves and does not read a new byte after changing address
        // this is for making the failed write result available until next address
        // change. should not be a problem, because you do not want to mix in
        // regular reads with writing anyway
        error=0;
        rdata=eprom.write(data);
        if (rdata!=data)
          error=0x02;
        eprom.address_next();
        break;
      case READ_INCA:
        // because of the way the protcol works, this works in an odd way
        // read READ has actually already happened, so all we need to do
        // is to move to next address, and cache the byte for next read
        eprom.address_next();
        rdata=eprom.read();
        break;
      case READ:
        // this will not have much use, but you can use it to read the actual
        // value of the new EPROM location after WRITE_INCA
        rdata=eprom.read();
        break;
    }
    count--;
  }
  
  void init()
  {
    uint8_t t;
    DDRB|=_BV(PORTB6);
    cli();
    PCMSK1=0x10; // PCINT12 enable
    PCICR=2;     // enable PCINT1 to cause interrupts on /SS pin change
    SPCR = (1<<SPE)|(1<<SPIE); // enable SPI module and SPI interrupts
    SPDR=0;
    state=0;
    sdata=0;
    t=SPSR;
    t=SPDR;
    error=head=tail=count=0;
    sei();
  }

  // this is to reset the state machine to synchronize
  // receiver when /SS is pulled low
  void restart()
  {
    SPDR=0;
    state=0;
    sdata=0;
  }

  // for getting the SPI data register loaded fast enough
  // the data for loading needs to be pre-computed
  // on each SPI interrupt the first thing is to send out
  // the data, then there is time to prepare the next byte
  //
  // when an interrupt occurs, a new byte has just been received
  // and with that one byte has already been clocked out too
  void receive()
  {
    SPDR=sdata;
    uint8_t x=SPDR;
    switch (state) {
      default:
        state=0;
      case 0: // command byte received
        // at this point first byte is already clocked out
        // and second is loaded to SPDR, so we are preparing
        // 3rd byte transmitted, which is status byte
        command=(uint32_t)x<<24;
        state++;
        sdata=((count>0)?1:0)|error;
        break;
      case 1: // address high byte
        // status byte is loaded to SPDR, in here
        // we are preparing the last byte to be sent
        // in this command. this is always a last read
        // result
        command|=(uint32_t)x<<16;
        state++;
        sdata=rdata;
        break;
      case 2: // address low byte
        // the byte that we are preparing now will be the
        // byte that gets clocked out when a first byte of
        // the next command is being received. for ease
        // of debugging we'll echo back the previous command
        // received
        command|=(uint32_t)x<<8;
        state++;
        sdata=(command>>24); // this will be a first result byte of next command
        break;
      case 3: // data byte in/out
        // the data prepared here will be clocked out in response
        // to second byte of the next command. again for ease of debugging
        // we'll set this to be data value of a previous command
        command|=(uint32_t)x;
        sdata=x;
        // READ_STATUS command is handled in this reception function
        // and is the only command that does not require further processing
        // the rest are queued up to be handled in main loop
        if (((command>>24)&0xff)!=READ_STATUS) {
          if (count<COUNTOF(queue)) {
            queue[head++]=command;
            head=head%COUNTOF(queue);
            count++;
          }
        }
        state=0;
        break;
    }
  }
    
};

SPISLAVE spislave;

// when /SS goes low, reset the slave state machine
ISR(PCINT1_vect)
{
  if ((PINB & _BV(PINB4))==0)
    spislave.restart();
}

// the SPI data register must be loaded in less than half a master generated clock
// period here
ISR(SPI_STC_vect)
{
  spislave.receive();
}
                                
ISR(WDT_vect)
{
}

/*
I/O configuration
-----------------
I/O pin                               direction    DDR  PORT
PA0 ADR12                             output       1    0
PA1 ADR13                             output       1    0
PA2 ADR14                             output       1    0
PA3 ADR15                             output       1    0
PA4 4040CLK                           output       1    0
PA5 4040RST                           output       1    0
PA6 unused                            output       1    0
PA7 unused                            output       1    0

PB0 unused                            output       1    0
PB1 unused                            output       1    0
PB2 unused                            output       1    0
PB3 unused                            output       1    0
PB4 /SS                               input        0    1
PB5 MOSI                              input        0    1
PB6 MISO                              input        0    1
PB7 SCK                               input        0    1

PC0 D0                                input        0    1
PC1 D1                                input        0    1
PC2 D2                                input        0    1
PC3 D3                                input        0    1
PC4 D4                                input        0    1
PC5 D5                                input        0    1
PC6 D6                                input        0    1
PC7 D7                                input        0    1

PD0 RxD (unused)                      input        0    1
PD1 TxD (unused)                      output       1    1
PD2 /LED                              output       1    1
PD3 27C512 mode                       output       1    0
PD4 /CE                               output       1    1
PD5 /OE                               output       1    1
PD6 VPP_12.5V                         output       1    0
PD7 VPP_21V                           output       1    0

*/
int main(void)
{
  MCUSR=0;
  MCUCR=(1<<JTD); // this does not actually seem to help, fuse needs to blown too
  // I/O directions and initial state
  DDRA=0xff;
  PORTA=0x00;
  DDRB=0x0f;
  PORTB=0xf0;
  DDRC=0x00;
  PORTC=0xff;
  DDRD=0xfe;
  PORTD=0x37;
  //
  set_sleep_mode(SLEEP_MODE_IDLE);
  sleep_enable();
  // configure watchdog to interrupt&reset, 4 sec timeout
  WDTCSR|=0x18;
  WDTCSR=0xe8;
  sei();
  eprom.reset();
  eprom.set_type(EPROM::_2764);
  spislave.init();
  while (1) {
    sleep_cpu(); // any interrupt, including watchdog, wakes up
    wdt_reset();
    WDTCSR|=0x40;
    if (spislave.command_ready())
      spislave.process_command();
  }
}

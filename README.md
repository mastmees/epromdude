# epromdude

Firmware and python code for avrtinyusp attached EPROM programmer. See project
page http://www.nomad.ee/eprom/ for hardware description  

!----------------------------------------------------------------------------------!
! uncharted waters ahead, this this code is only tested with 27C64 EPROMs this far !
!----------------------------------------------------------------------------------!

firmware implements a command set where each command is

a sequence of 4 bytes

	command
	address high byte
	address low byte
	data

the result of last read will be clocked out along with the last data byte
the 3rd data byte is status byte
 bit0=busy
 bit1=programming error

firmware commands

RESET		0	X	X	X
READ_STATUS	1	X	X	X
SEEK		2	AH	AL	X
SET_TYPE	3	X	X	type
SET_VPP		4	X	X	vpp
WRITE		5	X	X	data
READ		6	X	X	X
WRITE_INCA	7	X	X	data
READ_INCA	8	X	X	X


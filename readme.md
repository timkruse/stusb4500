# USB Type C Evaluation Board based on STUSB4500 by STM

This project implements the USB Type C connector based on the STM's STUSB4500 USB Power Delevery controller.
All signals are either routed to the dedicated USB connector or to an exteral connector to access signals such as I2C which is the config interface of the STUSB4500.  
The power lines are controled by FETs to suit the 100W specification of USB-C.
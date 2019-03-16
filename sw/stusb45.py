#!/usr/bin/env python2.7
from time import sleep
from collections import namedtuple
from smbus import SMBus
import RPi.GPIO as gpio

addr = 0x28 # I2C Address of the chip
bus = SMBus(1) # Raspi I2C bus

#	BCM-GPIO04 is on pin 7 of the header
reset_pin = 4
gpio.setmode(gpio.BCM)
gpio.setup(reset_pin, gpio.OUT)
def hard_reset():
	gpio.output(reset_pin, gpio.HIGH)
	sleep(0.2)
	gpio.output(reset_pin, gpio.LOW)


#	\brief Reads typec revision and usbpd revision of the chip
def version():
    BCD_TYPEC_REV_LOW = bus.read_byte_data(addr, 0x06)
    BCD_TYPEC_REV_HIGH = bus.read_byte_data(addr, 0x07)
    typec_rev = BCD_TYPEC_REV_HIGH << 8 | BCD_TYPEC_REV_LOW

    BCD_USBPD_REV_LOW = bus.read_byte_data(addr, 0x08)
    BCD_USBPD_REV_HIGH = bus.read_byte_data(addr, 0x09)
    usbpd_rev = BCD_USBPD_REV_HIGH << 8 | BCD_USBPD_REV_LOW
    Version = namedtuple("Version", "typec_rev, usbpd_rev")
    Version.__str__ = lambda v: "Version(typec_rev=" + hex(v.typec_rev) + ", usbpd_rev=" + hex(v.usbpd_rev)+ ")"
    Version.__repr__ = Version.__str__
	
    return Version(typec_rev=typec_rev, usbpd_rev=usbpd_rev)    

#	\brief Reads the current Status of the port (Sink-Source connection)
def port_status():
    PORT_STATUS_0 = bus.read_byte_data(addr, 0x0d)
    PORT_STATUS_1 = bus.read_byte_data(addr, 0x0e)

    attachedDeviceAsString = ["None", "Sink", "Source", "Debug Accessory", "Audio Accessory", "Power Accessory"]

    PortStatus = namedtuple("PortStatus", "stateChanged, attachedDevice, lowPowerStandby, powerMode, dataMode, attached")
    PortStatus.__str__ = lambda ps: "PortStatus(stateChanged=" + ("True" if ps.stateChanged == 1 else "False") + \
	", attachedDevice=" + (attachedDeviceAsString[ps.attachedDevice] if (ps.attachedDevice >= 0 and ps.attachedDevice <= 5) else "undefined(" + str(ps.attachedDevice) + ")") + \
	", lowPowerStandby=" +  ("standby mode" if ps.lowPowerStandby == 1 else "normal mode") + \
	", powerMode=" +  ("Source" if ps.powerMode == 1 else "Sink") + \
	", dataMode=" +  ("DFP" if ps.dataMode == 1 else "UFP") + \
	", attached=" +  ("True" if ps.attached == 1 else "False") + ")"
    PortStatus.__repr__ = PortStatus.__str__
    return PortStatus(stateChanged=PORT_STATUS_0 & 0x01, attachedDevice=PORT_STATUS_1 >> 5 & 0x07, lowPowerStandby=PORT_STATUS_1 >> 4 & 0x01, powerMode=PORT_STATUS_1 >> 3 & 0x01, dataMode=PORT_STATUS_1 >> 2 & 0x01, attached=PORT_STATUS_1 & 0x01)

#	\brief Reads the currently active PDO contract
def active_contract():
	DPM_PDO_NUMB = bus.read_byte_data(addr, 0x70)
	PDO_Contract = namedtuple("PDO_Contract", "num")
	return PDO_Contract(num=DPM_PDO_NUMB & 3)

#	\brief Forces to use another PDO contract
#	The STUSB4500 offers 3 PDO contracts and take effect after a soft reset
#	\param newValue: New contract PDO1, PDO2 or PDO3
def set_active_contract(newValue):
	# this is the active pdo contract. This takes effect after a sw reset (if source has the capability of the configured pdo)
	if newValue >= 0 and newValue < 4:
		return bus.write_byte_data(addr, 0x70, newValue)

#	\brief Reads all currently configured PDOs from the chip
#	REQ_SRC_CURRENT == unconstrainedPower
def read_pdo():
	base_reg = 0x85
	bvalues = [] # byte values
	for reg in range(0x85, 0x91):
		bvalues.append(bus.read_byte_data(addr, reg))
	
	supplyStr = ["Fixed", "Variable", "Battery"]

	PdoSinkFix = namedtuple("PdoSinkFix", "current, voltage, fastRoleReqCur, dualRoleData, usbCommunicationsCapable, unconstrainedPower, higherCapability, dualRolePower, supply, raw")
	PdoSinkFix.__str__ = lambda ps: "PdoSink("+ \
	"voltage=" + str(ps.voltage / 20.0) + "V" + \
	", current=" + str(ps.current / 100.0) + "A" + \
	", fastRoleReqCur=" + str(ps.fastRoleReqCur) + \
	", dualRoleData=" + str(ps.dualRoleData) + \
	", usbCommunicationsCapable=" + str(ps.usbCommunicationsCapable) + \
	", unconstrainedPower=" + str(ps.unconstrainedPower) + \
	", higherCapability=" + str(ps.higherCapability) + \
	", dualRolePower=" + str(ps.dualRolePower) + \
	", supply=" + (supplyStr[ps.supply] if ps.supply >= 0 and ps.supply < 3 else "Undefined") + \
	", raw=0x" + format(ps.raw, '08x') + \
	")"
	PdoSinkFix.__repr__ = PdoSinkFix.__str__

	PdoSinkVar = namedtuple("PdoSinkVar", "min_voltage, max_voltage, current, supply, raw")
	PdoSinkVar.__str__ = lambda ps: "PdoSink("+\
	"voltage=[" + str(ps.min_voltage / 20.0) + "V-" + str(ps.max_voltage / 20.0) + "V]" + \
	", current=" + str(ps.current / 100.0) + "A" + \
	", supply=" + (supplyStr[ps.supply] if ps.supply >= 0 and ps.supply < 3 else "Undefined") + \
	", raw=0x" + format(ps.raw, '08x') + \
	")"
	PdoSinkVar.__repr__ = PdoSinkVar.__str__

	PdoSinkBat = namedtuple("PdoSinkBat", "min_voltage, max_voltage, power, supply, raw")
	PdoSinkBat.__str__ = lambda ps: "PdoSink("+\
	"voltage=[" + str(ps.min_voltage / 20.0) + "V-" + str(ps.max_voltage / 20.0) + "V]" + \
	", power=" + str(ps.power) + "W" + \
	", supply=" + (supplyStr[ps.supply] if ps.supply >= 0 and ps.supply < 3 else "Undefined") + \
	", raw=0x" + format(ps.raw, '08x') + \
	")"
	PdoSinkBat.__repr__ = PdoSinkBat.__str__
	
	pdo = {}
	for i in range(0, 3):
		reg = bvalues[i * 4 + 3] << 24 | bvalues[i * 4 + 2] << 16 | bvalues[i * 4 + 1] << 8 | bvalues[i * 4]
		supply = reg >> 30 & 0x3
		if supply == 0: #  fixed
			pdo[i+1] = PdoSinkFix(supply=supply, dualRolePower=reg>>29 & 0x1, higherCapability=reg>>28 & 0x1, unconstrainedPower=reg>>27 & 0x1, usbCommunicationsCapable=reg>>26 & 0x1, dualRoleData=reg>>25 & 0x1, fastRoleReqCur=reg>>23 & 0x3, voltage=reg>>10 & 0x3ff, current=reg & 0x3ff, raw=reg)
		elif supply == 1: # variable
			pdo[i+1] = PdoSinkVar(supply=supply, max_voltage=reg>>20 & 0x3ff, min_voltage=reg>>10 & 0x3ff, current=reg&0x3ff, raw=reg)
		elif supply == 2: # battery
			pdo[i+1] = PdoSinkBat(supply=supply, max_voltage=reg>>20 & 0x3ff, min_voltage=reg>>10 & 0x3ff, power=reg&0x3ff, raw=reg)
	return pdo

#	\brief Reads and then prints the Power Data Object
def print_pdo():
	for k, v in read_pdo().iteritems():
		print "PDO#" + str(k) + ": ", v

#	\brief Read out the Requested Data Object (RDO)
def read_rdo():
	base_reg = 0x91
	bvalues = [] # byte values
	for reg in range(0x91, 0x95):
		bvalues.append(bus.read_byte_data(addr, reg))

	requested_voltage = bus.read_byte_data(addr, 0x21) # *100mV
	requested_voltage /= 10.0 # I want it in Volt not milli volt

	reg = bvalues[3] << 24 | bvalues[2] << 16 | bvalues[1] << 8 | bvalues[0]
	Rdo = namedtuple("RDO", "voltage, current, maxCurrent, unchunkedMess_sup, usbSuspend, usbComCap, capaMismatch, giveBack, objectPos, raw")
	Rdo.__str__ = lambda ps: "RDO("+ \
	"voltage=" + str(requested_voltage) + "V" + \
	", current=" + str(ps.current / 100.0) + "A" + \
	", maxCurrent=" + str(ps.maxCurrent / 100.0) + "A" + \
	", unchunkedMess_sup=" + str(ps.unchunkedMess_sup) + \
	", usbSuspend=" + str(ps.usbSuspend) + \
	", usbComCap=" + str(ps.usbComCap) + \
	", capaMismatch=" + str(ps.capaMismatch) + \
	", giveBack=" + str(ps.giveBack) + \
	", objectPos=" + str(ps.objectPos) + \
	", raw=0x" + format(ps.raw, '08x') + \
	")"
	Rdo.__repr__ = Rdo.__str__
	return Rdo(voltage=requested_voltage, objectPos=reg >> 28 & 0x7, giveBack=reg>>27 & 0x1, capaMismatch=reg>>26 & 0x1, usbComCap=reg>>25 & 0x1, usbSuspend=reg>>24 & 0x1, unchunkedMess_sup=reg>>23 & 0x1, current=reg>>10 & 0x3ff, maxCurrent=reg & 0x3ff, raw=reg)

#	\brief Perform a software reset
#	RESET_CTRL Register @0x23 bit 0 = {1 := reset, 0 := no reset}
def reset():
	RESET_CTRL = bus.read_byte_data(addr, 0x23)
	bus.write_byte_data(addr, 0x23, RESET_CTRL | 0x01)
	sleep(0.25)
	bus.write_byte_data(addr, 0x23, RESET_CTRL & ~0x01)

#	\param num: PDO to be changed (1..3)
#	\param volt: Desired voltage in mV
#	\param current: Desired current in mA
def set_pdo(num, volt, current):
	if num > 0 and num < 4:
		reg32 = ((current / 10) & 0x3ff) | (volt / 50) << 10 # | (1 << 29)
		bus.write_byte_data(addr, 0x85 + (num - 1) * 4, reg32 & 0xff)
		bus.write_byte_data(addr, 0x86 + (num - 1) * 4, (reg32 >> 8) & 0xff)
		# bus.write_byte_data(addr, 0x87 + (num - 1) * 4, (reg32 >> 16) & 0xff)
		# bus.write_byte_data(addr, 0x88 + (num - 1) * 4, (reg32 >> 24) & 0xff)
	else:
		print num, " is no valid pdo!"

#	\brief Configures a PDO with a variable Voltage/Current
#	\param pdo_num: PDO to be configured
#	\param current: Desired Current in mA
#	\param min_voltage: Min Voltage in mV
#	\param max_voltage: Max Voltage in mV
def set_pdo_variable(pdo_num, current, min_voltage, max_voltage):
	if pdo_num > 1 and pdo_num <= 3:
		if min_voltage >= 5000 and min_voltage <= 20000 and max_voltage >= 5000 and max_voltage <= 20000 and min_voltage <= max_voltage:
			reg32 = 1 << 30 # variable supply
			reg32 |= current / 10
			reg32 |= min_voltage / 50 << 10 # min voltage
			reg32 |= min_voltage / 50 << 20 # max voltage

			bus.write_byte_data(addr, 0x85 + (pdo_num - 1) * 4, reg32 & 0xff)
			bus.write_byte_data(addr, 0x86 + (pdo_num - 1) * 4, (reg32 >> 8) & 0xff)
			bus.write_byte_data(addr, 0x87 + (pdo_num - 1) * 4, (reg32 >> 16) & 0xff)
			bus.write_byte_data(addr, 0x88 + (pdo_num - 1) * 4, (reg32 >> 24) & 0xff)
	elif pdo_num == 1:
		print "PDO#1 cannot have a variable supply"

#	\brief Unlocks the internal NVM registers
#	\param lock: Unlocks if False, locks if True
def nvm_lock(lock):
	if lock is False:
		bus.write_byte_data(addr, 0x95, 0x47)
	else:
		bus.write_byte_data(addr, 0x95, 0x00)



#	\brief Dumps the NVM
#	\info factory nvm dump
# 		00 00 b0 aa 00 45 00 00 (0xc0-0xc7 hidden)
# 		10 40 9c 1c ff 01 3c df (0xc8-0xcf)
# 		02 40 0f 00 32 00 fc f1 (0xd0-0xd7)
# 		00 19 56 af f5 35 5f 00 (0xd8-0xdf)
# 		00 4b 90 21 43 00 40 fb (0xe0-0xe7)
def nvm_dump():
	nvm_lock(False) # unlock NVM

	def nvm_wait_for_execution():
		while True:
			reg8 = bus.read_byte_data(addr, 0x96)
			if reg8 & 0x10 == 0x00:
				break

	sector_data = []
	for num_sector in range(0, 5):
		# send command opcode READ(0x00) to FTP_CTRL_1(0x97)
		bus.write_byte_data(addr, 0x97, 0 & 0x07) 
		# execute command
		bus.write_byte_data(addr, 0x96, (num_sector & 0x07) | 0x80 | 0x40 | 0x10)
		nvm_wait_for_execution()
		# read 8 bytes that are copied from nvm to 0x53-0x5a
		sector = []
		for i in range(0, 8):
			sector.append(bus.read_byte_data(addr, 0x53 + i))
		sector_data.append(sector)
	nvm_lock(True) # lock NVM

	# nicely print out the values
	sec = 0
	for sector in sector_data:
		line = "%d: [" % sec
		sec += 1
		for byte in sector:
			line += "0x"+format(byte, '02x') + ", "
		line = line[:-2] # remove trailing comma
		line += "]"
		print(line)


#	Write procedure
#	Enter Write mode:
#	1. PASSWORD_REG(0x95) <= PASSWORD(0x47) to unlock flash
#	2. RW_BUFFER(0x53) <= 0 if partial erasing sectors
#	3. CTRL_0(0x96) <= PWR | RST_N to soft reset chip and power on 
#	4. CTRL_1(0x97) <= SECTORS_TOBE_ERASED_MASK << 3 | WRITE_SER to send erase command for the specified sectors (1 hot encoded)
#	5. CTRL_0(0x96) <= PWR | RST_N | REQ to commit command in CTRL_1 
#	6. Wait until REQ bit in CTRL_0 is cleared
#	7. CTRL_1(0x97) <= SOFT_PROG_SECTOR
#	8. CTRL_0(0x96) <= PWR | RST_N | REQ to commit command in CTRL_1
#	9. Wait until REQ bit in CTRL_0 is cleared
#	10. CTRL_1(0x97) <= ERASE_SECTOR
#	11. CTRL_0(0x96) <= PWR | RST_N | REQ to commit command in CTRL_1
#	12. Wait until REQ bit in CTRL_0 is cleared
#	Write Sector:
#	1. Write sector data into RW_BUFFER(0x53-0x5A)
#	2. CTRL_0(0x96) <= PWR | RST_N
#	3. CTRL_1(0x97) <= WRITE_PLR
#	4. CTRL_0(0x96) <= PWR | RST_N | REQ to commit command in CTRL_1
#	5. Wait until REQ bit in CTRL_0 is cleared
#	6. CTRL_1(0x97) <= PROG_SECTOR
#	7. CTRL_0(0x96) <= PWR | RST_N | REQ | SECTOR to commit command in CTRL_1
#	8. Wait until REQ bit in CTRL_0 is cleared
#	Exit Programming mode:
#	1. CTRL_0(0x96) <= RST_N
#	2. CTRL_1(0x97) <= 0
#	3. PASSWD(0x95) <= 0

#	\brief writes data into nvm
#	\param sector_data: dictionary where key is sector {0..4} and value is 8 bytes
#	\info: Requires a hard reset to take effect
def nvm_write(sector_data):
	pwr = 0x80
	rst_n = 0x40
	req = 0x10

	def nvm_wait_for_execution():
		while True:
			reg8 = bus.read_byte_data(addr, 0x96)
			if reg8 & 0x10 == 0x00:
				break

	section_mask = 0
	for k, v in sector_data.iteritems():
		if k >= 0 and k <= 4:
			if len(v) == 8:
				section_mask |= 1 << k
			else:
				print("New sector data has to many bytes (sector: %d)" % k)
				return
		else:
			print("Invalid sector %d" % k)
			return

	nvm_lock(False)
#	Erase specified sectors to be able to program them
	#bus.write_byte_data(addr, 0x53, 0x00)
	#bus.write_byte_data(addr, 0x96, pwr | rst_n)
	bus.write_byte_data(addr, 0x97, section_mask << 3 | 0x02) # WRITE_SER opcode
	bus.write_byte_data(addr, 0x96, pwr | rst_n | req)
	nvm_wait_for_execution()
	bus.write_byte_data(addr, 0x97, 0x07) # Soft_prog_sector opcode
	bus.write_byte_data(addr, 0x96, pwr | rst_n | req)
	nvm_wait_for_execution()
	bus.write_byte_data(addr, 0x97, 0x05) # erase_sector opcode
	bus.write_byte_data(addr, 0x96, pwr | rst_n | req)
	nvm_wait_for_execution()
#	Write data to sectors
	for k, v in sector_data.iteritems():
		# write new data into rw_bufer@0x53
		rw_buffer = 0x53
		for byte in v:
			bus.write_byte_data(addr, rw_buffer, byte)
			rw_buffer += 1
		bus.write_byte_data(addr, 0x97, 0x01) # WRITE_PLR opcode
		bus.write_byte_data(addr, 0x96, pwr | rst_n | req)
		nvm_wait_for_execution()
		bus.write_byte_data(addr, 0x97, 0x06) # PROG_SECTOR opcode
		bus.write_byte_data(addr, 0x96, pwr | rst_n | req | k)
		nvm_wait_for_execution()
#	Exit programming mode
	bus.write_byte_data(addr, 0x96, rst_n)
	bus.write_byte_data(addr, 0x97, 0)
	nvm_lock(True)

#	\brief These are the default values programmed by factory
nvm_factory_defaults = {0: [0x00, 0x00, 0xb0, 0xaa, 0x00, 0x45, 0x00, 0x00], 1: [0x10, 0x40, 0x9c, 0x1c, 0xff, 0x01, 0x3c, 0xdf], 2: [0x02, 0x40, 0x0f, 0x00, 0x32, 0x00, 0xfc, 0xf1], 3: [0x00, 0x19, 0x56, 0xaf, 0xf5, 0x35, 0x5f, 0x00], 4: [0x00, 0x4b, 0x90, 0x21, 0x43, 0x00, 0x40, 0xfb]}
nvm_12v = {0: [0x00,0x00,0xB0,0xAA,0x00,0x45,0x00,0x00], 1: [0x00,0x40,0x9D,0x1C,0xFF,0x01,0x3C,0xDF], 2: [0x02,0x40,0x0F,0x00,0x32,0x00,0xFC,0xF1], 3: [0x00,0x19,0xBF,0x55,0x57,0x55,0x55,0x00], 4: [0x00,0x2D,0xF0,0x20,0x43,0x00,0x00,0xFB]}


def vbus_ctrl():
#	Defining types
	Vbus = namedtuple("VBUS", "discharge_0v, discharge_trans, vbus_discharge, vsrc_discharge, sink_vbus_en")
	Vbus.__str__ = lambda v: "VBUS(discharge_time_transition=" + str(v.discharge_trans*24) + "ms" +\
							", discharge_to_0V=" + str(v.discharge_0v*84) + "ms" +\
							", vbus_discharge=" + ("Enabled" if v.vbus_discharge else "Disabled") +\
							", vsrc_discharge=" + ("Enabled" if v.vsrc_discharge else "Disabled") +\
							", sink_vbus_en=" + ("Enabled" if v.sink_vbus_en else "Disabled") +\
							")"
	Vbus.__repr__ = Vbus.__str__

#	Read out relevant registers
	VBUS_DISCHARGE_TIME_CTRL = bus.read_byte_data(addr, 0x25)
	VBUS_DISCHARGE_CTRL = bus.read_byte_data(addr, 0x26)
	VBUS_CTRL = bus.read_byte_data(addr, 0x27)

#	Map data to the type
	return Vbus(discharge_0v=VBUS_DISCHARGE_TIME_CTRL>>4 & 0x0f, discharge_trans=VBUS_DISCHARGE_TIME_CTRL & 0x0f, vbus_discharge=True if VBUS_DISCHARGE_CTRL >> 7 & 0x01 else False, vsrc_discharge=True if VBUS_DISCHARGE_CTRL >> 6 & 0x01 else False, sink_vbus_en=True if VBUS_CTRL >> 1 & 0x01 else False)



print read_rdo()
print_pdo()
print active_contract()


# PDO#1:  PdoSink(voltage=5.0V, current=3.0A, fastRoleReqCur=0, dualRoleData=0, usbCommunicationsCapable=1, unconstrainedPower=1, higherCapability=1, dualRolePower=0, supply=Fixed)
# PDO#2:  PdoSink(voltage=9.0V, current=2.0A, fastRoleReqCur=0, dualRoleData=0, usbCommunicationsCapable=0, unconstrainedPower=0, higherCapability=0, dualRolePower=0, supply=Fixed)
# PDO#3:  PdoSink(voltage=12.0V, current=1.5A, fastRoleReqCur=0, dualRoleData=0, usbCommunicationsCapable=0, unconstrainedPower=0, higherCapability=0, dualRolePower=0, supply=Fixed)

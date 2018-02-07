#!/usr/bin/env python
# -*- coding: utf8 -*-

# [1]: https://www.nxp.com/docs/en/data-sheet/MFRC522.pdf 

import pigpio

class IR:
    # Interrupt names
    # Bit 7 has different uses
    IRqInv  = 0x80
    Set1    = 0x80
    # Bits 0-6 are the same in enable and status regs
    Tx      = 0x40
    Rx      = 0x20
    Idle    = 0x10
    HiAlert = 0x08
    LoAlert = 0x04
    Err     = 0x02
    Timer   = 0x01
    
    # Clear all status
    ClearAll = 0x7F
    # Disable interrupts
    DisableAll = 0x00

# FIXME: Make class like IR
S_INIT = 0
S_DETECT = 1
S_ANTICOLL = 2
S_SELECT = 3
S_AUTHENTICATE = 4
S_READ = 5
S_STOP = 6


class MFRC522:
  # FIXME: Make configurable    
  RST_PIN = 25 # Pin number 22 
  IRQ_PIN = 24 # Pin number 18
  
  
  MAX_LEN = 16
  
  # FIXME: Make PCD, PICC, MI class like IR
  # Commands, see table 149 in [1]
  PCD_IDLE       = 0x00
  PCD_AUTHENT    = 0x0E
  # PCD_RECEIVE    = 0x08
  # PCD_TRANSMIT   = 0x04
  PCD_TRANSCEIVE = 0x0C
  PCD_RESETPHASE = 0x0F
  PCD_CALCCRC    = 0x03
  
  
  PICC_REQIDL    = 0x26
  # PICC_REQALL    = 0x52
  PICC_ANTICOLL  = 0x93
  PICC_SELECTTAG = 0x93
  PICC_AUTHENT1A = 0x60
  # PICC_AUTHENT1B = 0x61
  PICC_READ      = 0x30
  PICC_WRITE     = 0xA0
  # PICC_DECREMENT = 0xC0
  # PICC_INCREMENT = 0xC1
  # PICC_RESTORE   = 0xC2
  # PICC_TRANSFER  = 0xB0
  # PICC_HALT      = 0x50
  
  MI_OK       = 0
  MI_NOTAGERR = 1
  MI_ERR      = 2
  
  # FIXME: Make module constants
  # Reserved00     = 0x00
  CommandReg     = 0x01 # starts and stops command execution   
  CommIEnReg     = 0x02 # enable and disable interrupt request control bits (init: 0xA0, authent: 0x92, transceive: 0xF7)
  # DivIEnReg      = 0x03 # enable and disable interrupt request control bits
  CommIrqReg     = 0x04 # interrupt request bits
  DivIrqReg      = 0x05 # interrupt request bits
  ErrorReg       = 0x06 # error bits showing the error status of the last command executed
  # Status1Reg     = 0x07 # communication status bits
  Status2Reg     = 0x08 # receiver and transmitter status bits
  FIFODataReg    = 0x09 # input and output of 64 byte FIFO buffer
  FIFOLevelReg   = 0x0A # number of bytes stored in the FIFO buffer
  # WaterLevelReg  = 0x0B # level for FIFO underflow and overflow warning
  ControlReg     = 0x0C # miscellaneous control registers
  BitFramingReg  = 0x0D # adjustments for bit-oriented frames
  # CollReg        = 0x0E # bit position of the first bit-collision detected on the RF interface
  # Reserved01     = 0x0F
  
  # Reserved10     = 0x10
  ModeReg        = 0x11 # defines general modes for transmitting and receiving
  # TxModeReg      = 0x12 # defines transmission data rate and framing
  # RxModeReg      = 0x13 # defines reception data rate and framing
  TxControlReg   = 0x14 # controls the logical behavior of the antenna driver pins TX1 and TX2
  TxAutoReg      = 0x15 # controls the setting of the transmission modulation
  # TxSelReg       = 0x16
  # RxSelReg       = 0x17
  # RxThresholdReg = 0x18
  # DemodReg       = 0x19
  # Reserved11     = 0x1A
  # Reserved12     = 0x1B
  # MifareReg      = 0x1C
  # Reserved13     = 0x1D
  # Reserved14     = 0x1E
  # SerialSpeedReg = 0x1F
  
  # Reserved20        = 0x20  
  CRCResultRegM     = 0x21 # MSB value of the CRC calculation
  CRCResultRegL     = 0x22 # LSB value of the CRC calculation
  # Reserved21        = 0x23
  # ModWidthReg       = 0x24
  # Reserved22        = 0x25
  # RFCfgReg          = 0x26
  # GsNReg            = 0x27
  # CWGsPReg          = 0x28
  # ModGsPReg         = 0x29
  TModeReg          = 0x2A # defines settings for the internal timer
  TPrescalerReg     = 0x2B # the lower 8 bits of the TPrescaler value. The 4 high bits are in TModeReg.
  TReloadRegH       = 0x2C # defines high bits the 16-bit timer reload value
  TReloadRegL       = 0x2D # defines low bits the 16-bit timer reload value
  # TCounterValueRegH = 0x2E
  # TCounterValueRegL = 0x2F
  
  # Reserved30      = 0x30
  # TestSel1Reg     = 0x31
  # TestSel2Reg     = 0x32
  # TestPinEnReg    = 0x33
  # TestPinValueReg = 0x34
  # TestBusReg      = 0x35
  # AutoTestReg     = 0x36
  # VersionReg      = 0x37
  # AnalogTestReg   = 0x38
  # TestDAC1Reg     = 0x39
  # TestDAC2Reg     = 0x3A
  # TestADCReg      = 0x3B
  # Reserved31      = 0x3C
  # Reserved32      = 0x3D
  # Reserved33      = 0x3E
  # Reserved34      = 0x3F
      
 
  
########################################################################################
#
# Public API
#
########################################################################################

  # FIXME: Separate the hardware (GPIO/SPI) from the protocol
  def __init__(self, callback):
    self.pio = pigpio.pi()
    self.pio.write(MFRC522.RST_PIN, 1)
    self.pio.set_mode(MFRC522.IRQ_PIN, pigpio.INPUT)
    self.pio.set_pull_up_down(MFRC522.IRQ_PIN, pigpio.PUD_UP)
    self.cdcb = self.pio.callback(MFRC522.IRQ_PIN, pigpio.FALLING_EDGE, self._irq_handler) 
    self.spi_handle = self.pio.spi_open(0, 1000000)
    self.state  = S_INIT
    self.uid = None
    self.readout = None
    self._readout_cb = callback
        
    self.MFRC522_Init()


  def MFRC522_DetectCard(self):
    """
    Will wait for RFID tag to show up, and read it.
    Caller should wait for MFRC522.state to be S_STOP 
    Result in MFRC522.uid and MFRC522.readout. 
    """  
    self.state = S_DETECT
    self.uid = None
    self.readout = None  
    reqMode =  MFRC522.PICC_REQIDL
    # Check up on these
    self.reg_write(self.CommIrqReg, IR.ClearAll)
    self.reg_write(self.DivIrqReg, IR.ClearAll)
    self.reg_write(self.CommIEnReg, IR.IRqInv | IR.Rx | IR.Timer)
    self.reg_write(self.FIFOLevelReg, 0x80) # Flush FIFO
    self.reg_write(self.FIFODataReg, self.PICC_REQIDL)
    self.reg_write(self.CommandReg, self.PCD_TRANSCEIVE)
    self.reg_write(self.BitFramingReg, 0x87)
    
    
  def close(self):
      self.pio.spi_close(self.spi_handle)
      self.pio.stop()
  
########################################################################################
#
# Private methods
#
########################################################################################
  
  def print_irq_status(self):
      irqmap = {
          0x40 : "Tx",     
          0x20 : "Rx",     
          0x10 : "Idle",   
          0x08 : "HiAlert",
          0x04 : "LoAlert",
          0x02 : "Err",    
          0x01 : "Timer",  
      }
      irq_enabled = self.reg_read(self.CommIEnReg)
      irq_status = self.reg_read(self.CommIrqReg)
      div_status = self.reg_read(self.DivIrqReg)
      flags = [irqmap[key] for key in [0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01] if key & irq_enabled]
      print "ComIEnReg : " + "|".join(flags)       
      flags = [irqmap[key] for key in [0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01] if key & irq_status]
      print "CommIrqReg : " + "|".join(flags) 
      # print "DivIrqReg : 0x%02x" %  (div_status & 0x14)  
      # print "irq_status : 0x%02x, div_status : 0x%02x" % (irq_status, div_status)
  
  def _fsm_restart(self):
      # print "_fsm_restart"
      self.state = S_DETECT
      self.MFRC522_DetectCard()
      
  def _check_uid(self, status, data, nBits):
      if status != self.MI_OK:
          return status
      if nBits != 40:
          return self.MI_ERR

      serNumCheck = 0
      for byte in data[0:-1]:
        serNumCheck = serNumCheck ^ byte

      if serNumCheck != data[-1]:
        return self.MI_ERR
    
      return self.MI_OK
            
  def _irq_handler(self, pin, edge, tick):
      # print "FSM_STATE:", self.state
      # self.print_irq_status() 
      irq_enabled = self.reg_read(self.CommIEnReg) & 0x7F
      irq_status = self.reg_read(self.CommIrqReg) & 0x7F
      self.reg_write(self.CommIrqReg, IR.ClearAll)
      self.reg_write(self.DivIrqReg, IR.ClearAll)    
      if irq_enabled and (irq_enabled & irq_status):
          
          if irq_status & IR.Timer:
              # Fail, start over
              self._fsm_restart()
              return
                        
          if self.state == S_DETECT:
              # print "S_DETECT"
              self.state = S_ANTICOLL
              self.async_anticoll()
              return
              
          if self.state == S_ANTICOLL:
              # print "S_ANTICOLL"
              status = self._get_result()
              data, nBits = self._recv()
              # print status, data, nBits
              if self._check_uid(status, data, nBits) == self.MI_OK:
                  self.state = S_SELECT
                  self.uid = data
                  self.async_select(data)
              else:
                  self._fsm_restart()
              return
                  
          if self.state == S_SELECT:
              # print "S_SELECT"
              status = self._get_result()
              data, nBits = self._recv()
              # print status, data, nBits
              if status == self.MI_OK:
                  self.state = S_AUTHENTICATE
                  key = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
                  self.async_authenticate(self.PICC_AUTHENT1A, 8, key, self.uid)
              else:
                  self._fsm_restart()
              return
           
          if self.state == S_AUTHENTICATE:
              # print "S_AUTHENTICATE"
              status = self._get_result()
              # print status
              if status == self.MI_OK:
                  self.state = S_READ
                  self.async_read(8)
              else:
                  self._fsm_restart()
              return
              
          if self.state == S_READ:
              # print "S_READ"
              status = self._get_result()
              data, nBits = self._recv()
              # print status, data, nBits
              self.MFRC522_StopCrypto1()
          if status == self.MI_OK:
              self.state = S_STOP
              self.readout = data
              self._readout_cb()
          else:
              self._fsm_restart()
          return
                             
      else:
          pass
          # print "BOGUS interrupt"
                       
  def reg_write(self, addr, val):
    self.pio.spi_xfer(self.spi_handle, [(addr<<1) & 0x7E, val])
  
  def reg_read(self, addr):
    n, nbytes = self.pio.spi_xfer(self.spi_handle, [((addr<<1) & 0x7E) | 0x80, 0])
    vals = list(nbytes)
    return vals[1] 
  
  # Unused
  def reg_set_bits(self, reg, mask):
    tmp = self.reg_read(reg)
    self.reg_write(reg, tmp | mask)
    
  def reg_clear_bits(self, reg, mask):
    tmp = self.reg_read(reg)
    self.reg_write(reg, tmp & ~mask)

  def reset(self):
    self.reg_write(self.CommandReg, self.PCD_RESETPHASE)
  
  def antenna_on(self):
    temp = self.reg_read(self.TxControlReg)
    if not temp & 0x03 == 0x03:
      self.reg_write(self.TxControlReg, temp | 0x03)
  
  def antenna_off(self):
    temp = self.reg_read(self.TxControlReg)
    self.reg_write(self.TxControlReg, temp & 0xFC)
  
  # def authenticate(self, buf):
  #     status = self._authenticate(buf)
  #     return status
  
  # FIXME: Merge transceive, _authenticate,and _send
  def transceive(self, buf, crc=True, rxAlign=0x0, txLastBits=0x0):
      crc_bytes = self._calulate_CRC(buf) if crc else []
      status = self._send(buf + crc_bytes, rxAlign, txLastBits)
      # data, nBits = self._recv()
      # return (status, data, nBits)
      
  def _authenticate(self, data):
    irqEn = IR.IRqInv | IR.Idle | IR.Timer
    waitIRq = IR.Idle | IR.Timer
    
    self.reg_write(self.FIFOLevelReg, 0x80) # Flush FIFO
    self.reg_write(self.CommIrqReg, IR.ClearAll)   # Clear IRQ flags
    self.reg_write(self.CommIEnReg, irqEn)
    
    self.reg_write(self.CommandReg, self.PCD_IDLE)  
    
    for byte in data:
        self.reg_write(self.FIFODataReg, byte)
    
    self.reg_write(self.CommandReg, self.PCD_AUTHENT)
      
              
  def _send(self, data, rxAlign, txLastBits):
    irqEn = IR.IRqInv | IR.Rx | IR.Timer
    waitIRq = IR.Rx | IR.Timer
    bitFraming = (rxAlign << 4) & 0x70
    bitFraming |= txLastBits & 0x07 
    
    self.reg_write(self.FIFOLevelReg, 0x80) # Flush FIFO
    self.reg_write(self.CommIrqReg, IR.ClearAll)   # Clear IRQ flags
    self.reg_write(self.CommIEnReg, irqEn)
    
    self.reg_write(self.CommandReg, self.PCD_IDLE)  
    
    for byte in data:
        self.reg_write(self.FIFODataReg, byte)
    
    self.reg_write(self.CommandReg, self.PCD_TRANSCEIVE)
      
    self.reg_write(self.BitFramingReg, 0x80 | bitFraming) # Start transmission
    

  # FIXME: Rename
  def _get_result(self):
    status = self.MI_ERR
    self.reg_write(self.BitFramingReg, 0x00)
    if (self.reg_read(self.ErrorReg) & 0x1B)==0x00:
        status = self.MI_OK
    return status
          
      
  # FIXME: Rename
  def _recv(self):
    n = self.reg_read(self.FIFOLevelReg)
    lastBits = self.reg_read(self.ControlReg) & 0x07
    backLen = (n-1)*8 + lastBits if lastBits else n*8
   
    if n == 0:
      n = 1
    if n > self.MAX_LEN:
      n = self.MAX_LEN
    
    backData = []    
    for i in range(0, n):
      backData.append(self.reg_read(self.FIFODataReg))

    return (backData, backLen)

  def _calulate_CRC(self, buf):
    self.reg_write(self.DivIrqReg, 0x04)
    self.reg_write(self.FIFOLevelReg, 0x80)
    
    for byte in buf:
      self.reg_write(self.FIFODataReg, byte)
      
    self.reg_write(self.CommandReg, self.PCD_CALCCRC)

    for i in range(0, 256):
      if self.reg_read(self.DivIrqReg) & 0x04:
        break
        
    crc_bytes = [self.reg_read(self.CRCResultRegL), self.reg_read(self.CRCResultRegM)]
    return crc_bytes

  # # FIXME: What does this do? Just detecting presence?
  # def MFRC522_Request(self, reqMode):
  #   status, _, backBits = self.transceive([reqMode], crc=False, txLastBits=0x07)
  #   if status != self.MI_OK or backBits != 0x10:
  #     status = self.MI_ERR
  #
  #   return (status, backBits)
    
  def async_anticoll(self):
    serNum = [self.PICC_ANTICOLL, 0x20]
    self.transceive(serNum, crc=False)  
  
  def async_select(self, uid):
    buf = [self.PICC_SELECTTAG, 0x70] + uid
    self.transceive(buf, crc=True)
  
  # FIXME: make BlockAddr, Sectorkey (and perhaps authMode too) params to calling function
  def async_authenticate(self, authMode, BlockAddr, Sectorkey, serNum):
    # First byte should be the authMode (A or B)
    # Second byte is the trailerBlock (usually 7)
    # Now we need to append the authKey which usually is 6 bytes of 0xFF
    # Next we append the first 4 bytes of the UID
    buf = [authMode, BlockAddr] + Sectorkey + serNum[0:4]
    self._authenticate(buf)
  
  # Exit encrypted session
  def MFRC522_StopCrypto1(self):
    self.reg_clear_bits(self.Status2Reg, 0x08)
  
  def async_read(self, blockAddr):
    buf = [self.PICC_READ, blockAddr]
    self.transceive(buf, crc=True)
        
  # FIXME: Implement?
  def MFRC522_Write(self, blockAddr, writeData):
    buf = [self.PICC_WRITE, blockAddr]
    status, backData, backLen = self.transceive(buf, crc=True)    
    if status != self.MI_OK or backLen != 4 or (backData[0] & 0x0F) != 0x0A:
        return (self.MI_ERR, backData)
    
    print str(backLen)+" backdata &0x0F == 0x0A "+str(backData[0]&0x0F)

    buf = writeData[0:16]
    status, backData, backLen = self.authenticated(buf, crc=True)
    if status != self.MI_OK or backLen != 4 or (backData[0] & 0x0F) != 0x0A:
       status = self.MI_ERR
    return (status, backData)
      
  def timer_setup(self, period):
    """Set timer period in seconds"""
    mode = 0x08  
    # With these prescaler settings, a tick is very close to 0.5ms
    prescale_hi = 0x0D
    prescale_lo = 0x3E
    # Compute settings for timer_hit and timer_lo
    divider = 256*prescale_hi + prescale_lo
    f_timer = 13.56e6/(2.0*divider+1.0)
    tick_s = 1.0/f_timer
    ticks = int(period/tick_s)
    timer_hi = ticks>>8 & 0xFF
    timer_lo = ticks & 0xFF
    
    print f_timer, tick_s, tick_s * ticks
    
    self.reg_write(self.TModeReg, mode<<4 | prescale_hi)
    self.reg_write(self.TPrescalerReg, prescale_lo)
    self.reg_write(self.TReloadRegL, timer_lo)
    self.reg_write(self.TReloadRegH, timer_hi)
      

  # FIXME: Move to init
  def MFRC522_Init(self):
  
    self.reset()
    
    self.reg_write(self.CommIrqReg, IR.ClearAll)
    self.reg_write(self.DivIrqReg, IR.ClearAll)
    self.reg_write(self.CommIEnReg, IR.DisableAll)
        
    # FIXME: Make parameter 
    self.timer_setup(0.1)

    self.reg_write(self.TxAutoReg, 0x40)
    self.reg_write(self.ModeReg, 0x3D)
    
    self.antenna_on()
    

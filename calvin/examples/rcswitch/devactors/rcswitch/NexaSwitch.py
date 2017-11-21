from calvin.actor.actor import Actor, condition, manage, stateguard, calvinsys

class Waveform(object):
    
    # Times in microseconds
    T1 = 250
    T5 = 5*T1
    T10 = 10*T1
    T40 = 40*T1
    
    def __init__(self):
        pass

    def sequence(self, databits):
        self.wf = []
        self.start()
        self.message(databits)
        self.stop()
        return self.wf

    def high(self, t):
        self.wf.append((1, t))

    def low(self, t):
        self.wf.append((0, t))
                
    def encode_one(self):
        self.high(self.T1)
        self.low(self.T1)
        self.high(self.T1)
        self.low(self.T5)

    def encode_zero(self):
        self.high(self.T1)
        self.low(self.T5)
        self.high(self.T1)
        self.low(self.T1)

    def start(self):
        self.high(self.T1)
        self.low(self.T10)

    def stop(self):
        self.high(self.T1)
        self.low(self.T40)
                
    def message(self, data):
        for _ in range(0, 32):
            if data & 0x80000000:
                self.encode_one()
            else:
                self.encode_zero()
            data <<= 1
        

class NexaSwitch(Actor):
    """
    Control a wireless power outlet
        
    Inputs:
      state : 1/0 for on/off
    """

    @manage(['databits', 'tx'])
    def init(self, tx_id, group_cmd, channel, unit):
        self.databits = (tx_id & 0x03FFFFFF) << 6
        self.databits |= ((group_cmd & 0x1) << 5)
        self.databits |= ((channel & 0x3) << 2)
        self.databits |= (unit & 0x3)
        self.databits &= 0xFFFFFFEF
        self.tx = calvinsys.open(self, "io.tx433MHz")
        
        
    @stateguard(lambda self: calvinsys.can_write(self.tx))
    @condition(action_input=["state"])
    def switch_state(self, state):
        data = self.databits
        data |= ((int(not state) & 0x1) << 4)
        wf = Waveform()
        calvinsys.write(self.tx, wf.sequence(data))

    action_priority = (switch_state, )
    requires = ["io.tx433MHz"]


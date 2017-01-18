from calvin.actor.actor import Actor, condition, manage


class RCSwitch(Actor):
    """
    Control a wireless power outlet
    Inputs:
      state : 1/0 for on/off
    """

    @manage(['gpio_pin', 'databits', 'startBit', 'stopBit', 'oneBit', 'zeroBit', 'repeat'])
    def init(self, gpio_pin, homecode, group, channel, startBit, stopBit, oneBit, zeroBit, repeat):
        self.gpio_pin = gpio_pin
        self.databits = homecode
        self.databits &= 0xFFFFFFC0
        self.databits |= ((group & 1) << 5)
        self.databits |= ((~channel) & 15)
        self.startBit = startBit
        self.stopBit = stopBit
        self.oneBit = oneBit
        self.zeroBit = zeroBit
        self.repeat = repeat
        self.setup()

    def setup(self):
        self.use("calvinsys.io.gpiohandler", shorthand="gpiohandler")
        self.gpio = self["gpiohandler"].open(self.gpio_pin, "o")

    def will_end(self):
        self.gpio.close()

    def did_migrate(self):
        self.gpio.close()

    @condition(action_input=["state"])
    def switch_state(self, state):
        data = self.databits
        data |= (state << 4)

        bits = []

        # Start bits
        bits.append((self.startBit[0]["state"], self.startBit[0]["time"]))
        bits.append((self.startBit[1]["state"], self.startBit[1]["time"]))

        # Data bits
        for bit in range(0, 32):
            if data & 0x80000000:
                bits.append((self.oneBit[0]["state"], self.oneBit[0]["time"]))
                bits.append((self.oneBit[1]["state"], self.oneBit[1]["time"]))
                bits.append((self.zeroBit[0]["state"], self.zeroBit[0]["time"]))
                bits.append((self.zeroBit[1]["state"], self.zeroBit[1]["time"]))
            else:
                bits.append((self.zeroBit[0]["state"], self.zeroBit[0]["time"]))
                bits.append((self.zeroBit[1]["state"], self.zeroBit[1]["time"]))
                bits.append((self.oneBit[0]["state"], self.oneBit[0]["time"]))
                bits.append((self.oneBit[1]["state"], self.oneBit[1]["time"]))
            data <<= 1

        # Stop bit
        bits.append((self.stopBit[0]["state"], self.stopBit[0]["time"]))
        bits.append((self.stopBit[1]["state"], self.stopBit[1]["time"]))

        # Output data
        self.gpio.shift_out(bits, self.repeat)
        

    action_priority = (switch_state, )
    requires = ["calvinsys.io.gpiohandler"]

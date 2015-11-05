from calvin.actor.actor import Actor, ActionResult, condition


class Display(Actor):
    """
    Control a display
    Inputs:
      text : text to display
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.io.display", shorthand="display")
        self.display = self["display"]
        self.display.enable(True)

    def will_end(self):
        self.display.enable(False)

    def did_migrate(self):
        self.setup()

    @condition(action_input=["text"])
    def show_text(self, text):
        self.display.show_text(str(text))
        return ActionResult()

    action_priority = (show_text, )
    requires = ["calvinsys.io.display"]

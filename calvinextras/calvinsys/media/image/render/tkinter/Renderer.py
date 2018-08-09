# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from PIL import ImageTk, Image
import Tkinter as tkinter
import StringIO
import base64
from calvin.runtime.south.async import async
from calvin.utilities.calvinlogger import get_logger
from calvinextras.calvinsys.media.image.render import BaseRenderer

_log = get_logger(__name__)


class Renderer(BaseRenderer.BaseRenderer):
    """
        Renderer implementation based on Tkinter and Python Imaging Library (PIL)
    """

    def init(self):
        self._render_in_progress = False
        self._running = False
        async.call_in_thread(self._local_mainloop)


    def can_write(self):
        return self._running and not self._render_in_progress

    def _mainloop(self, root):
        panel = None
        while self._running:
            root.update()
            if self._render_in_progress:
                raw_image = base64.b64decode(self._b64image)
                buf = StringIO.StringIO(raw_image)
                pil_image = Image.open(buf)
                tk_image = ImageTk.PhotoImage(pil_image)
                if not panel:
                    panel = tkinter.Label(root, image=tk_image)
                    panel.pack()
                else :
                    panel.configure(image=tk_image)
                    panel.image = tk_image
                panel.update()
                self._render_in_progress = False
                # Done -> awaken scheduler
                async.call_from_thread(self.scheduler_wakeup)

            else :
                import time
                time.sleep(0.1)

    def _local_mainloop(self):
        root = tkinter.Tk()
        self._running = True
        try:
            self._mainloop(root)
        except Exception as e:
            _log.error("Encountered error: {}".format(e))
        root.destroy()

    def write(self, b64img):
        self._b64image = b64img
        self._render_in_progress = True

    def close(self):
        self._running = False

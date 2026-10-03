import numpy as np
import sounddevice as sd
from .core import Renderer


class Player:
    def __init__(self):
        self.project = None
        self.renderer = None
        self.stream = None
        self.position = 0
        self.master = 0.5
        self.peak = 0.0
        self.error = ''
        self.underruns = 0

    @property
    def playing(self):
        return self.stream is not None and self.stream.active

    def load(self, project):
        self.close()
        self.project = project
        self.renderer = Renderer(project)
        self.position = 0

    def play(self):
        if not self.project or self.playing:
            return
        self.pause()
        if self.position >= self.project.length:
            self.position = 0
        self.error = ''
        self.stream = sd.OutputStream(samplerate=self.project.rate, channels=2,
                                      dtype='float32', blocksize=2048, latency='high', callback=self.callback)
        self.stream.start()

    def callback(self, outdata, frames, time, status):
        outdata.fill(0)
        if status:
            self.underruns += 1
        count = min(frames, self.project.length-self.position)
        if count <= 0:
            raise sd.CallbackStop()
        try:
            block = self.renderer.mix(self.position, count, self.master)
            self.peak = float(np.max(np.abs(block)))
            outdata[:count] = np.clip(block, -1, 1)
            self.position += count
        except Exception as exc:
            self.error = str(exc)
            raise sd.CallbackAbort() from exc

    def pause(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def seek(self, position):
        resume = self.playing
        self.pause()
        self.position = max(0, min(position, self.project.length if self.project else 0))
        if resume:
            self.play()

    def close(self):
        self.pause()
        if self.renderer:
            self.renderer.close()
            self.renderer = None

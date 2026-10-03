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
        self.center_mono = False
        self.loop = False

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
        try:
            lo, hi = self.project.export_range if self.loop and self.project.export_range else (0, self.project.length)
            looping = self.loop and self.project.export_range is not None
            if looping and not lo <= self.position < hi:
                self.position = lo
            offset, self.peak = 0, 0.0
            while offset < frames:
                count = min(frames-offset, hi-self.position)
                if count <= 0:
                    if looping:
                        self.position = lo
                        continue
                    if offset == 0:
                        raise sd.CallbackStop()
                    break
                block = self.renderer.mix(self.position, count, self.master, self.center_mono)
                self.peak = max(self.peak, float(np.abs(block).max(initial=0)))
                outdata[offset:offset+count] = np.clip(block, -1, 1)
                offset += count
                self.position += count
                if looping and self.position == hi:
                    self.position = lo
        except sd.CallbackStop:
            raise
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

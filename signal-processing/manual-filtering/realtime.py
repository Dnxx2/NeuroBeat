"""
Sliding-window real-time processor.

Usage:
    proc = RealtimeProcessor()
    while True:
        sample = unicorn.get_sample()   # shape (8,)
        state = proc.push(sample)
        if state:
            send_to_game(state)
"""
import numpy as np
from collections import deque
from pipeline import EEGPipeline


class RealtimeProcessor:
    def __init__(self, window_sec: float = 2.0, step_sec: float = 0.25,
                 fs: float = 250.0, n_channels: int = 8):
        self.fs = fs
        self.window_len = int(window_sec * fs)
        self.step_len   = int(step_sec * fs)
        self.buffer = deque(maxlen=self.window_len)
        # ICA disabled in real-time: window is too short and latency matters
        self.pipeline = EEGPipeline(fs=fs, n_channels=n_channels, use_ica=False)
        self._tick = 0

    def push(self, sample: np.ndarray) -> str | None:
        """
        Push one sample of shape (n_channels,).
        Returns a state string every `step_sec` seconds once the buffer is full, else None.
        """
        self.buffer.append(sample)
        self._tick += 1

        if len(self.buffer) == self.window_len and self._tick % self.step_len == 0:
            window = np.array(self.buffer)   # (window_len, n_channels)
            return self.pipeline.classify(window)
        return None

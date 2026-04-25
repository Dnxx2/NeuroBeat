"""
Sliding-window real-time processor.
ICA is skipped (too slow for live inference); CAR + filters run on every window.
Load a calibration file from pipeline.calibrate() to get subject-specific classification.

Usage:
    pipeline = EEGPipeline(use_ica=False)
    pipeline.load_calibration('calibration.npz')

    proc = RealtimeProcessor(pipeline=pipeline)
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
    def __init__(self, pipeline: EEGPipeline | None = None,
                 window_sec: float = 2.0, step_sec: float = 0.25,
                 fs: float = 250.0, n_channels: int = 8):
        self.window_len = int(window_sec * fs)
        self.step_len   = int(step_sec * fs)
        self.buffer = deque(maxlen=self.window_len)
        self.pipeline = pipeline or EEGPipeline(fs=fs, n_channels=n_channels, use_ica=False)
        self._tick = 0

    def push(self, sample: np.ndarray) -> str | None:
        """
        Push one sample (n_channels,).
        Returns a state string every step_sec once the buffer is full, else None.
        """
        self.buffer.append(sample)
        self._tick += 1
        if len(self.buffer) == self.window_len and self._tick % self.step_len == 0:
            return self.pipeline.classify(np.array(self.buffer))
        return None

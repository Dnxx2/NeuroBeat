import time
import numpy as np
import matplotlib.pyplot as plt

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes

# =============================
# CONFIGURACIÓN
# =============================

board_id = BoardIds.UNICORN_BOARD.value  # diadema Unicorn
params = BrainFlowInputParams()

# ⚠️ IMPORTANTE:
# si usas Bluetooth, necesitas poner el serial port
# ejemplo:
# params.serial_port = "COM3"  (Windows)
# params.serial_port = "/dev/ttyUSB0" (Linux/Mac)

# =============================
# INICIALIZAR
# =============================

board = BoardShim(board_id, params)
board.prepare_session()
board.start_stream()

sampling_rate = BoardShim.get_sampling_rate(board_id)
eeg_channels = BoardShim.get_eeg_channels(board_id)

print(f"Grabando 5 segundos de EEG ({sampling_rate} Hz, {len(eeg_channels)} canales)...")
time.sleep(5)

data = board.get_board_data()
board.stop_stream()
board.release_session()

# =============================
# VISUALIZAR
# =============================

fig, axes = plt.subplots(len(eeg_channels), 1, figsize=(12, 10), sharex=True)
fig.suptitle("EEG Crudo — Unicorn Black (8 canales)")

channel_names = ['FZ', 'C3', 'CZ', 'C4', 'PZ', 'PO7', 'OZ', 'PO8']
t = np.arange(data.shape[1]) / sampling_rate

for i, ch in enumerate(eeg_channels):
    axes[i].plot(t, data[ch], linewidth=0.8)
    axes[i].set_ylabel(channel_names[i], fontsize=8)
    axes[i].tick_params(labelsize=7)

axes[-1].set_xlabel("Tiempo (s)")
plt.tight_layout()
plt.show()

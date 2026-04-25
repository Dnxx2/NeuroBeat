import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

class RealTimeScope:
    def __init__(self, board):
        self.board = board
        self.board_id = BoardIds.UNICORN_BOARD.value
        self.ex_channels = BoardShim.get_eeg_channels(self.board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)

        # Ventana de tiempo: mostraremos los últimos 5 segundos en movimiento
        self.window_seconds = 5
        self.max_points = self.window_seconds * self.sampling_rate

        # Configurar la ventana de la gráfica
        self.app = QtWidgets.QApplication(sys.argv)
        self.win = pg.GraphicsLayoutWidget(title="Brain-Stream Papu Edition")
        self.win.resize(1000, 700)

        self.plots = []
        self.curves = []

        # Crear los 8 canales
        for i in range(len(self.ex_channels)):
            p = self.win.addPlot(row=i, col=0)
            p.showAxis('left', False)
            p.setMenuEnabled(False)
            # Dibujamos una línea verde neón tipo Matrix
            curve = p.plot(pen=pg.mkPen(color=(0, 255, 120), width=1))
            self.plots.append(p)
            self.curves.append(curve)

        # Timer para refrescar la pantalla (30 veces por segundo)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(33)

    def update_plot(self):
        # Obtenemos los datos actuales del buffer de la Unicorn
        data = self.board.get_current_board_data(self.max_points)

        if data.any():
            for i, channel in enumerate(self.ex_channels):
                signal = data[channel]
                if len(signal) > 0:
                    # Filtro rápido: Centrar la señal para que no "vuele" fuera del cuadro
                    signal = signal - np.mean(signal)
                    self.curves[i].setData(signal)

    def run(self):
        self.win.show()
        self.app.exec()

def main():
    # Limpieza previa de puertos
    params = BrainFlowInputParams()
    params.serial_port = 'COM5'
    board = BoardShim(BoardIds.UNICORN_BOARD.value, params)

    try:
        board.prepare_session()
        board.start_stream()
        print("¡Streaming iniciado! Tienes un osciloscopio cerebral en vivo.")

        scope = RealTimeScope(board)
        scope.run()

    except Exception as e:
        print(f"Error de conexión: {e}")
    finally:
        if board.is_prepared():
            board.stop_stream()
            board.release_session()
            print("Puerto COM5 liberado. Todo limpio.")

if __name__ == "__main__":
    main()

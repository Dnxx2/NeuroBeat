import time
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

def main():
    # Configuración básica
    params = BrainFlowInputParams()
    params.serial_port = 'COM5'
    board_id = BoardIds.UNICORN_BOARD.value
    board = BoardShim(board_id, params)

    try:
        print("--- Intentando conexión ---")
        board.prepare_session()
        board.start_stream()

        print("¡CONECTADO CON ÉXITO!")
        print("Recibiendo datos durante 5 segundos...")

        time.sleep(5)

        # Recuperamos todo lo que se acumuló en esos 5 segundos
        data = board.get_board_data()

        # data.shape[1] nos dice cuántas muestras (puntos de datos) llegaron
        print(f"--- RESULTADO ---")
        print(f"Muestras recibidas: {data.shape[1]}")
        print(f"Shape completo: {data.shape}")
        print(f"Frecuencia de muestreo esperada: {BoardShim.get_sampling_rate(board_id)} Hz")

    except Exception as e:
        print(f"Error de conexión: {e}")
    finally:
        if board.is_prepared():
            board.stop_stream()
            board.release_session()
            print("Sesión cerrada correctamente.")

if __name__ == "__main__":
    main()

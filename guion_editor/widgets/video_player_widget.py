# guion_editor/widgets/video_player_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSlider, QLabel,
    QFileDialog, QShortcut, QMessageBox, QHBoxLayout
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence, QFont

import logging


class VideoPlayerWidget(QWidget):
    """
    Widget personalizado para reproducir videos y controlar marcas de tiempo.
    """
    inOutSignal = pyqtSignal(str, int)  # Señal para enviar 'IN'/'OUT' y la posición en ms
    detachRequested = pyqtSignal(QWidget)  # Señal para solicitar la separación del widget
    setPositionSignal = pyqtSignal(int)  # Señal para establecer la posición del video

    def __init__(self):
        super().__init__()
        self.setup_logging()
        self.init_ui()
        self.setup_shortcuts()
        self.setup_timers()
        self.last_f11_press_time = None
        self.f11_pressed = False
        self.frame_interval_timer = QTimer()
        self.frame_interval_timer.setSingleShot(True)
        self.frame_interval_timer.timeout.connect(self.check_frame_interval)
        self.logger.debug("VideoPlayerWidget inicializado correctamente.")

    def setup_logging(self) -> None:
        """
        Configura el sistema de logging para la clase.
        """
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def init_ui(self) -> None:
        """
        Configura la interfaz de usuario del reproductor de video.
        """
        self.setGeometry(100, 100, 800, 600)
        self.setup_video_player()
        self.setup_controls()
        self.setup_layouts()
        self.setFocusPolicy(Qt.StrongFocus)

    def setup_video_player(self) -> None:
        """
        Configura el reproductor de video y sus conexiones.
        """
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.videoWidget = QVideoWidget()
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.stateChanged.connect(self.update_play_button)
        self.mediaPlayer.positionChanged.connect(self.update_slider)
        self.mediaPlayer.durationChanged.connect(self.update_slider_range)
        self.mediaPlayer.volumeChanged.connect(self.update_volume_slider)
        self.mediaPlayer.mediaStatusChanged.connect(self.on_media_status_changed)
        self.mediaPlayer.error.connect(self.on_media_error)

    def setup_controls(self) -> None:
        """
        Configura los controles de reproducción y otros botones.
        """
        # Botones de control con mayor tamaño de fuente
        button_font = QFont()
        button_font.setPointSize(12)  # Tamaño de fuente más grande

        self.playButton = QPushButton("Play/Pausa")
        self.playButton.setFont(button_font)
        self.playButton.clicked.connect(self.toggle_play)

        self.rewindButton = QPushButton("Retroceder")
        self.rewindButton.setFont(button_font)
        self.rewindButton.clicked.connect(lambda: self.change_position(-5000))

        self.forwardButton = QPushButton("Avanzar")
        self.forwardButton.setFont(button_font)
        self.forwardButton.clicked.connect(lambda: self.change_position(5000))

        self.detachButton = QPushButton("Detachar")
        self.detachButton.setFont(button_font)
        self.detachButton.clicked.connect(self.detach_widget)  # Conectar el botón

        # Slider de posición del video
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)

        # Botón de volumen
        self.volumeButton = QPushButton("Volumen")
        self.volumeButton.setFont(button_font)
        self.volumeButton.clicked.connect(self.toggle_volume_slider)

        # Slider de volumen vertical, inicialmente oculto
        self.volumeSliderVertical = QSlider(Qt.Vertical)
        self.volumeSliderVertical.setRange(0, 100)
        self.volumeSliderVertical.setValue(100)
        self.volumeSliderVertical.setVisible(False)
        self.volumeSliderVertical.valueChanged.connect(self.set_volume)

        # Etiqueta de Time Code
        self.timeCodeLabel = QLabel("00:00:00:00")
        self.timeCodeLabel.setAlignment(Qt.AlignCenter)
        self.timeCodeLabel.setStyleSheet("font-size: 12px;")  # Reduce tamaño de fuente
        self.timeCodeLabel.setFixedHeight(20)  # Fija la altura para limitar el espacio

        # Botones IN y OUT con mayor tamaño de fuente
        self.inButton = QPushButton("IN")
        self.inButton.setFont(button_font)
        self.inButton.clicked.connect(self.mark_in)

        self.outButton = QPushButton("OUT")
        self.outButton.setFont(button_font)
        self.outButton.clicked.connect(self.mark_out)

        # Estilosheets para mejorar la apariencia
        self.volumeSliderVertical.setStyleSheet("""
            QSlider::handle:vertical {
                background: #5A5A5A;
                border: 1px solid #5A5A5A;
                height: 20px;
                margin: -5px 0;
                border-radius: 5px;
            }
            QSlider::groove:vertical {
                background: #B0B0B0;
                width: 8px;
                border-radius: 4px;
            }
        """)

        # Estilos para los botones
        self.playButton.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.rewindButton.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.forwardButton.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.detachButton.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.inButton.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        self.outButton.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)

    def setup_layouts(self) -> None:
        """
        Configura los layouts de la interfaz de usuario.
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Video widget ocupa ~80% del espacio
        layout.addWidget(self.videoWidget, 8)

        # Slider de posición ocupa ~10% (stretch factor 1)
        layout.addWidget(self.slider, 1)

        # Layout horizontal para los botones
        buttonsLayout = QHBoxLayout()
        buttonsLayout.setSpacing(10)

        # Botón de Detachar a la izquierda
        buttonsLayout.addWidget(self.detachButton)

        # Botón de Play/Pausa
        buttonsLayout.addWidget(self.playButton)

        # Botón de Retroceder
        buttonsLayout.addWidget(self.rewindButton)

        # Botón de Avanzar
        buttonsLayout.addWidget(self.forwardButton)

        # Botón IN
        buttonsLayout.addWidget(self.inButton)

        # Botón OUT
        buttonsLayout.addWidget(self.outButton)

        # Espaciador para empujar el botón de volumen a la derecha
        buttonsLayout.addStretch()

        # Botón de volumen
        buttonsLayout.addWidget(self.volumeButton)

        # Slider de volumen vertical, oculto inicialmente
        buttonsLayout.addWidget(self.volumeSliderVertical)

        # Agregar el layout de botones al layout principal con stretch factor 1
        layout.addLayout(buttonsLayout, 1)

        # Etiqueta de Time Code ocupa ~5% (stretch factor 1)
        layout.addWidget(self.timeCodeLabel, 1)

        self.setLayout(layout)

    def setup_shortcuts(self) -> None:
        """
        Configura los atajos de teclado para controlar el reproductor.
        """
        shortcuts = {
            "F8": self.toggle_play,
            "F7": lambda: self.change_position(-5000),
            "F9": lambda: self.change_position(5000),
            "F10": self.mark_in,
        }
        for key, slot in shortcuts.items():
            QShortcut(QKeySequence(key), self, slot)

    def setup_timers(self) -> None:
        """
        Configura los timers utilizados para actualizar el Time Code.
        """
        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / 25))  # 25 fps
        self.timer.timeout.connect(self.update_time_code)
        self.timer.start()

    def keyPressEvent(self, event) -> None:
        """
        Maneja el evento de presionar una tecla.
        """
        if event.key() == Qt.Key_F11 and not event.isAutoRepeat():
            self.handle_f11_press()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        """
        Maneja el evento de soltar una tecla.
        """
        if event.key() == Qt.Key_F11 and not event.isAutoRepeat():
            self.handle_f11_release()
        else:
            super().keyReleaseEvent(event)

    def handle_f11_press(self) -> None:
        """
        Maneja la lógica cuando se presiona la tecla F11.
        """
        current_time = self.mediaPlayer.position()
        self.logger.debug(f"F11 pressed: current_time={current_time}")
        self.f11_pressed = True
        self.last_f11_press_time = current_time
        if not self.frame_interval_timer.isActive():
            self.frame_interval_timer.start(40)  # Aproximadamente 1 frame a 25 fps

    def handle_f11_release(self) -> None:
        """
        Maneja la lógica cuando se suelta la tecla F11.
        """
        current_time = self.mediaPlayer.position()
        self.logger.debug(f"F11 released: current_time={current_time}")
        self.f11_pressed = False
        time_elapsed = current_time - self.last_f11_press_time
        if time_elapsed >= 80:  # 2 frames a 25 fps
            self.mark_out()
        else:
            self.frame_interval_timer.start(80 - time_elapsed)

    def check_frame_interval(self) -> None:
        """
        Verifica si se deben marcar los eventos IN/OUT basándose en el tiempo transcurrido.
        """
        current_time = self.mediaPlayer.position()
        if self.last_f11_press_time is not None:
            time_elapsed = current_time - self.last_f11_press_time

            if not self.f11_pressed and time_elapsed >= 80:  # 2 frames a 25 fps
                self.mark_out()
                self.last_f11_press_time = None
            elif self.f11_pressed:
                self.frame_interval_timer.start(40)  # Revisar nuevamente en 1 frame
            else:
                self.frame_interval_timer.start(80 - time_elapsed)

    def mark_in(self) -> None:
        """
        Marca el tiempo 'IN' y emite la señal correspondiente.
        """
        try:
            position_ms = self.mediaPlayer.position()
            self.logger.debug(f"mark_in: position_ms={position_ms}")
            self.inOutSignal.emit("IN", position_ms)
        except Exception as e:
            self.logger.error(f"Error en mark_in: {e}")

    def mark_out(self) -> None:
        """
        Marca el tiempo 'OUT' y emite la señal correspondiente.
        """
        try:
            position_ms = self.mediaPlayer.position()
            self.logger.debug(f"mark_out: position_ms={position_ms}")
            self.inOutSignal.emit("OUT", position_ms)
        except Exception as e:
            self.logger.error(f"Error en mark_out: {e}")

    def toggle_play(self) -> None:
        """
        Alterna la reproducción del video entre Play y Pausa.
        """
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def change_position(self, change: int) -> None:
        """
        Cambia la posición actual del video.

        Args:
            change (int): Cambio en milisegundos (positivo para avanzar, negativo para retroceder).
        """
        new_position = self.mediaPlayer.position() + change
        new_position = max(0, min(new_position, self.mediaPlayer.duration()))
        self.mediaPlayer.setPosition(new_position)

    def set_position(self, position: int) -> None:
        """
        Establece la posición del video.

        Args:
            position (int): Nueva posición en milisegundos.
        """
        self.mediaPlayer.setPosition(position)

    def set_volume(self, volume: int) -> None:
        """
        Establece el volumen del reproductor.

        Args:
            volume (int): Volumen entre 0 y 100.
        """
        self.mediaPlayer.setVolume(volume)

    def update_volume_slider(self, volume: int) -> None:
        """
        Actualiza el slider de volumen vertical con el nuevo valor.

        Args:
            volume (int): Nuevo valor de volumen.
        """
        self.volumeSliderVertical.setValue(volume)

    def update_play_button(self, state: QMediaPlayer.State) -> None:
        """
        Actualiza el texto del botón de play/pausa basado en el estado del reproductor.

        Args:
            state (QMediaPlayer.State): Nuevo estado del reproductor.
        """
        self.playButton.setText("Pausa" if state == QMediaPlayer.PlayingState else "Play")

    def update_slider(self, position: int) -> None:
        """
        Actualiza el slider de posición del video.

        Args:
            position (int): Nueva posición en milisegundos.
        """
        self.slider.setValue(position)

    def update_slider_range(self, duration: int) -> None:
        """
        Actualiza el rango del slider de posición basado en la duración del video.

        Args:
            duration (int): Duración total del video en milisegundos.
        """
        self.slider.setRange(0, duration)

    def update_time_code(self) -> None:
        """
        Actualiza la etiqueta de Time Code con la posición actual del video.
        """
        position = self.mediaPlayer.position()
        hours, remainder = divmod(position, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, msecs = divmod(remainder, 1000)
        frames = int(msecs / (1000 / 25))
        self.timeCodeLabel.setText(f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}")

    def get_current_time_code(self) -> str:
        """
        Obtiene el time code actual en formato HH:MM:SS:FF.

        Returns:
            str: Time code actual.
        """
        position = self.mediaPlayer.position()
        hours, remainder = divmod(position, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, msecs = divmod(remainder, 1000)
        frames = int(msecs / (1000 / 25))
        return f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}"

    def load_video(self, video_path: str) -> None:
        """
        Carga y reproduce un video desde la ruta especificada.

        Args:
            video_path (str): Ruta al archivo de video.
        """
        try:
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.mediaPlayer.play()
            self.logger.debug(f"Video cargado desde: {video_path}")
        except Exception as e:
            self.logger.error(f"Error al cargar el video: {e}")
            QMessageBox.warning(self, "Error", f"Error al cargar el video: {str(e)}")

    def on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """
        Maneja los cambios en el estado del media player.

        Args:
            status (QMediaPlayer.MediaStatus): Nuevo estado del media player.
        """
        if status == QMediaPlayer.LoadedMedia:
            self.logger.debug("Media loaded and ready to play")
        else:
            self.logger.debug(f"Current media status: {status}")

    def on_media_error(self, error: QMediaPlayer.Error) -> None:
        """
        Maneja los errores del media player.

        Args:
            error (QMediaPlayer.Error): Código de error del media player.
        """
        self.logger.error(f"Error en la reproducción del video: {self.mediaPlayer.errorString()}")
        QMessageBox.warning(self, "Error de Reproducción", self.mediaPlayer.errorString())

    def set_position_public(self, milliseconds: int) -> None:
        """
        Método público para establecer la posición del video en milisegundos.

        Args:
            milliseconds (int): Nueva posición en milisegundos.
        """
        try:
            if 0 <= milliseconds <= self.mediaPlayer.duration():
                self.mediaPlayer.setPosition(milliseconds)
                self.logger.debug(f"Video position set to {milliseconds} ms")
            else:
                self.logger.warning(f"Position {milliseconds} ms fuera del rango del video")
                QMessageBox.warning(self, "Error", "La posición especificada está fuera del rango del video.")
        except Exception as e:
            self.logger.error(f"Error al establecer la posición del video: {e}")
            QMessageBox.warning(self, "Error", f"Error al establecer la posición del video: {str(e)}")

    def detach_widget(self) -> None:
        """
        Emitir una señal para solicitar que el widget sea detachado en una nueva ventana.
        """
        self.detachRequested.emit(self)

    def toggle_volume_slider(self) -> None:
        """
        Alternar la visibilidad del slider de volumen vertical.
        """
        self.volumeSliderVertical.setVisible(not self.volumeSliderVertical.isVisible())

    def update_fonts(self, font_size: int) -> None:
        """
        Actualiza el tamaño de fuente de todos los botones y el Time Code.

        Args:
            font_size (int): Nuevo tamaño de fuente.
        """
        font = QFont()
        font.setPointSize(font_size)

        # Actualizar botones
        self.playButton.setFont(font)
        self.rewindButton.setFont(font)
        self.forwardButton.setFont(font)
        self.detachButton.setFont(font)
        self.inButton.setFont(font)
        self.outButton.setFont(font)
        self.volumeButton.setFont(font)

        # Actualizar Time Code
        tc_font = QFont()
        tc_font.setPointSize(max(font_size - 2, 8))  # Tamaño ligeramente menor para el TC
        self.timeCodeLabel.setFont(tc_font)

        self.logger.debug(f"Fuentes actualizadas a tamaño {font_size} pt")

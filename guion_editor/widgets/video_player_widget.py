# guion_editor/widgets/video_player_widget.py

import logging
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QFileDialog,
    QShortcut,
    QMessageBox,
    QHBoxLayout,
)


class VideoPlayerWidget(QWidget):
    """
    Widget personalizado para reproducir videos y controlar marcas de tiempo.
    """

    in_out_signal = pyqtSignal(
        str, int
    )  # Señal para enviar 'IN'/'OUT' y la posición en ms
    detach_requested = pyqtSignal(
        QWidget
    )  # Señal para solicitar la separación del widget
    set_position_signal = pyqtSignal(int)  # Señal para establecer la posición del video

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
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
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
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.stateChanged.connect(self.update_play_button)
        self.media_player.positionChanged.connect(self.update_slider)
        self.media_player.durationChanged.connect(self.update_slider_range)
        self.media_player.volumeChanged.connect(self.update_volume_slider)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.error.connect(self.on_media_error)

    def setup_controls(self) -> None:
        """
        Configura los controles de reproducción y otros botones.
        """
        # Botones de control con mayor tamaño de fuente
        button_font = QFont()
        button_font.setPointSize(12)  # Tamaño de fuente más grande

        self.play_button = QPushButton("Play/Pausa")
        self.play_button.setFont(button_font)
        self.play_button.clicked.connect(self.toggle_play)

        self.rewind_button = QPushButton("Retroceder")
        self.rewind_button.setFont(button_font)
        self.rewind_button.clicked.connect(lambda: self.change_position(-5000))

        self.forward_button = QPushButton("Avanzar")
        self.forward_button.setFont(button_font)
        self.forward_button.clicked.connect(lambda: self.change_position(5000))

        self.detach_button = QPushButton("Detachar")
        self.detach_button.setFont(button_font)
        self.detach_button.clicked.connect(self.detach_widget)  # Conectar el botón

        # Slider de posición del video
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)

        # Botón de volumen
        self.volume_button = QPushButton("Volumen")
        self.volume_button.setFont(button_font)
        self.volume_button.clicked.connect(self.toggle_volume_slider)

        # Slider de volumen vertical, inicialmente oculto
        self.volume_slider_vertical = QSlider(Qt.Vertical)
        self.volume_slider_vertical.setRange(0, 100)
        self.volume_slider_vertical.setValue(100)
        self.volume_slider_vertical.setVisible(False)
        self.volume_slider_vertical.valueChanged.connect(self.set_volume)

        # Etiqueta de Time Code
        self.time_code_label = QLabel("00:00:00:00")
        self.time_code_label.setAlignment(Qt.AlignCenter)
        self.time_code_label.setStyleSheet(
            "font-size: 12px;"
        )  # Reduce tamaño de fuente
        self.time_code_label.setFixedHeight(
            20
        )  # Fija la altura para limitar el espacio

        # Botones IN y OUT con mayor tamaño de fuente
        self.in_button = QPushButton("IN")
        self.in_button.setFont(button_font)
        self.in_button.clicked.connect(self.mark_in)

        self.out_button = QPushButton("OUT")
        self.out_button.setFont(button_font)
        self.out_button.clicked.connect(self.mark_out)

        # Estilosheets para mejorar la apariencia
        self.volume_slider_vertical.setStyleSheet(
            """
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
        """
        )

        # Estilos para los botones
        self.play_button.setStyleSheet(
            """
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
        """
        )
        self.rewind_button.setStyleSheet(
            """
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
        """
        )
        self.forward_button.setStyleSheet(
            """
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
        """
        )
        self.detach_button.setStyleSheet(
            """
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
        """
        )
        self.in_button.setStyleSheet(
            """
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
        """
        )
        self.out_button.setStyleSheet(
            """
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
        """
        )

    def setup_layouts(self) -> None:
        """
        Configura los layouts de la interfaz de usuario.
        """
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Video widget ocupa ~80% del espacio
        layout.addWidget(self.video_widget, 8)

        # Slider de posición ocupa ~10% (stretch factor 1)
        layout.addWidget(self.slider, 1)

        # Layout horizontal para los botones
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Botón de Detachar a la izquierda
        buttons_layout.addWidget(self.detach_button)

        # Botón de Play/Pausa
        buttons_layout.addWidget(self.play_button)

        # Botón de Retroceder
        buttons_layout.addWidget(self.rewind_button)

        # Botón de Avanzar
        buttons_layout.addWidget(self.forward_button)

        # Botón IN
        buttons_layout.addWidget(self.in_button)

        # Botón OUT
        buttons_layout.addWidget(self.out_button)

        # Espaciador para empujar el botón de volumen a la derecha
        buttons_layout.addStretch()

        # Botón de volumen
        buttons_layout.addWidget(self.volume_button)

        # Slider de volumen vertical, oculto inicialmente
        buttons_layout.addWidget(self.volume_slider_vertical)

        # Agregar el layout de botones al layout principal con stretch factor 1
        layout.addLayout(buttons_layout, 1)

        # Etiqueta de Time Code ocupa ~5% (stretch factor 1)
        layout.addWidget(self.time_code_label, 1)

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
        current_time = self.media_player.position()
        self.logger.debug(f"F11 pressed: current_time={current_time}")
        self.f11_pressed = True
        self.last_f11_press_time = current_time
        if not self.frame_interval_timer.isActive():
            self.frame_interval_timer.start(40)  # Aproximadamente 1 frame a 25 fps

    def handle_f11_release(self) -> None:
        """
        Maneja la lógica cuando se suelta la tecla F11.
        """
        current_time = self.media_player.position()
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
        current_time = self.media_player.position()
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
            position_ms = self.media_player.position()
            self.logger.debug(f"mark_in: position_ms={position_ms}")
            self.in_out_signal.emit("IN", position_ms)
        except Exception as e:
            self.logger.error(f"Error en mark_in: {e}")

    def mark_out(self) -> None:
        """
        Marca el tiempo 'OUT' y emite la señal correspondiente.
        """
        try:
            position_ms = self.media_player.position()
            self.logger.debug(f"mark_out: position_ms={position_ms}")
            self.in_out_signal.emit("OUT", position_ms)
        except Exception as e:
            self.logger.error(f"Error en mark_out: {e}")

    def toggle_play(self) -> None:
        """
        Alterna la reproducción del video entre Play y Pausa.
        """
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def change_position(self, change: int) -> None:
        """
        Cambia la posición actual del video.

        Args:
            change (int): Cambio en milisegundos (positivo para avanzar, negativo para retroceder).
        """
        new_position = self.media_player.position() + change
        new_position = max(0, min(new_position, self.media_player.duration()))
        self.media_player.setPosition(new_position)

    def set_position(self, position: int) -> None:
        """
        Establece la posición del video.

        Args:
            position (int): Nueva posición en milisegundos.
        """
        self.media_player.setPosition(position)

    def set_volume(self, volume: int) -> None:
        """
        Establece el volumen del reproductor.

        Args:
            volume (int): Volumen entre 0 y 100.
        """
        self.media_player.setVolume(volume)

    def update_volume_slider(self, volume: int) -> None:
        """
        Actualiza el slider de volumen vertical con el nuevo valor.

        Args:
            volume (int): Nuevo valor de volumen.
        """
        self.volume_slider_vertical.setValue(volume)

    def update_play_button(self, state: QMediaPlayer.State) -> None:
        """
        Actualiza el texto del botón de play/pausa basado en el estado del reproductor.

        Args:
            state (QMediaPlayer.State): Nuevo estado del reproductor.
        """
        self.play_button.setText(
            "Pausa" if state == QMediaPlayer.PlayingState else "Play"
        )

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
        position = self.media_player.position()
        hours, remainder = divmod(position, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, msecs = divmod(remainder, 1000)
        frames = int(msecs / (1000 / 25))
        self.time_code_label.setText(
            f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}"
        )

    def get_current_time_code(self) -> str:
        """
        Obtiene el time code actual en formato HH:MM:SS:FF.

        Returns:
            str: Time code actual.
        """
        position = self.media_player.position()
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
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.media_player.play()
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
        if error != QMediaPlayer.NoError:
            self.logger.error(
                f"Error en la reproducción del video: {self.media_player.errorString()}"
            )
            QMessageBox.warning(
                self, "Error de Reproducción", self.media_player.errorString()
            )

    def set_position_public(self, milliseconds: int) -> None:
        """
        Método público para establecer la posición del video en milisegundos.

        Args:
            milliseconds (int): Nueva posición en milisegundos.
        """
        try:
            if 0 <= milliseconds <= self.media_player.duration():
                self.media_player.setPosition(milliseconds)
                self.logger.debug(f"Video position set to {milliseconds} ms")
            else:
                self.logger.warning(
                    f"Position {milliseconds} ms fuera del rango del video"
                )
                QMessageBox.warning(
                    self,
                    "Error",
                    "La posición especificada está fuera del rango del video.",
                )
        except Exception as e:
            self.logger.error(f"Error al establecer la posición del video: {e}")
            QMessageBox.warning(
                self, "Error", f"Error al establecer la posición del video: {str(e)}"
            )

    def detach_widget(self) -> None:
        """
        Emitir una señal para solicitar que el widget sea detachado en una nueva ventana.
        """
        self.detach_requested.emit(self)

    def toggle_volume_slider(self) -> None:
        """
        Alternar la visibilidad del slider de volumen vertical.
        """
        self.volume_slider_vertical.setVisible(
            not self.volume_slider_vertical.isVisible()
        )

    def update_fonts(self, font_size: int) -> None:
        """
        Actualiza el tamaño de fuente de todos los botones y el Time Code.

        Args:
            font_size (int): Nuevo tamaño de fuente.
        """
        font = QFont()
        font.setPointSize(font_size)

        # Actualizar botones
        self.play_button.setFont(font)
        self.rewind_button.setFont(font)
        self.forward_button.setFont(font)
        self.detach_button.setFont(font)
        self.in_button.setFont(font)
        self.out_button.setFont(font)
        self.volume_button.setFont(font)

        # Actualizar Time Code
        tc_font = QFont()
        tc_font.setPointSize(
            max(font_size - 2, 8)
        )  # Tamaño ligeramente menor para el TC
        self.time_code_label.setFont(tc_font)

        self.logger.debug(f"Fuentes actualizadas a tamaño {font_size} pt")

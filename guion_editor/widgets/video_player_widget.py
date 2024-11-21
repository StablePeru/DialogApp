from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSlider, QLabel,
    QFileDialog, QShortcut, QMessageBox, QHBoxLayout
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence, QFont

import os


class VideoPlayerWidget(QWidget):
    """
    Widget personalizado para reproducir videos y controlar marcas de tiempo.
    """
    in_out_signal = pyqtSignal(str, int)
    out_released = pyqtSignal()
    detach_requested = pyqtSignal(QWidget)
    set_position_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_stylesheet()
        self.setup_shortcuts()
        self.setup_timers()
        self.f6_pressed = False
        self.out_timer = QTimer(self)
        self.out_timer.setInterval(40)
        self.out_timer.timeout.connect(self.mark_out)
        self.out_timer.setSingleShot(False)

    def init_ui(self) -> None:
        self.setGeometry(100, 100, 800, 600)
        self.setup_video_player()
        self.setup_controls()
        self.setup_layouts()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def setup_video_player(self) -> None:
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
        button_font = QFont()
        button_font.setPointSize(12)

        self.play_button = QPushButton("Play/Pausa")
        self.play_button.setFont(button_font)
        self.play_button.setObjectName("play_button")
        self.play_button.clicked.connect(self.toggle_play)

        self.rewind_button = QPushButton("Retroceder")
        self.rewind_button.setFont(button_font)
        self.rewind_button.setObjectName("rewind_button")
        self.rewind_button.clicked.connect(lambda: self.change_position(-5000))

        self.forward_button = QPushButton("Avanzar")
        self.forward_button.setFont(button_font)
        self.forward_button.setObjectName("forward_button")
        self.forward_button.clicked.connect(lambda: self.change_position(5000))

        self.detach_button = QPushButton("Separar")
        self.detach_button.setFont(button_font)
        self.detach_button.setObjectName("detach_button")
        self.detach_button.clicked.connect(self.detach_widget)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setObjectName("position_slider")
        self.slider.sliderMoved.connect(self.set_position)

        self.volume_button = QPushButton("Volumen")
        self.volume_button.setFont(button_font)
        self.volume_button.setObjectName("volume_button")
        self.volume_button.clicked.connect(self.toggle_volume_slider)

        self.volume_slider_vertical = QSlider(Qt.Vertical)
        self.volume_slider_vertical.setRange(0, 100)
        self.volume_slider_vertical.setValue(100)
        self.volume_slider_vertical.setObjectName("volume_slider_vertical")
        self.volume_slider_vertical.setVisible(False)
        self.volume_slider_vertical.valueChanged.connect(self.set_volume)

        self.time_code_label = QLabel("00:00:00:00")
        self.time_code_label.setAlignment(Qt.AlignCenter)
        self.time_code_label.setObjectName("time_code_label")
        self.time_code_label.setFixedHeight(20)

        self.in_button = QPushButton("IN")
        self.in_button.setFont(button_font)
        self.in_button.setObjectName("in_button")
        self.in_button.clicked.connect(self.mark_in)

        self.out_button = QPushButton("OUT")
        self.out_button.setFont(button_font)
        self.out_button.setObjectName("out_button")
        self.out_button.clicked.connect(self.mark_out)

    def setup_layouts(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        layout.addWidget(self.time_code_label, 1)
        layout.addWidget(self.video_widget, 8)
        layout.addWidget(self.slider, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        buttons_layout.addWidget(self.detach_button)
        buttons_layout.addWidget(self.play_button)
        buttons_layout.addWidget(self.rewind_button)
        buttons_layout.addWidget(self.forward_button)
        buttons_layout.addWidget(self.in_button)
        buttons_layout.addWidget(self.out_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.volume_button)
        buttons_layout.addWidget(self.volume_slider_vertical)

        layout.addLayout(buttons_layout, 1)

        self.setLayout(layout)

    def load_stylesheet(self) -> None:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            css_path = os.path.join(current_dir, '..', 'styles', 'main.css')

            with open(css_path, 'r') as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            QMessageBox.warning(self, "Error de Estilos", f"Error al cargar el stylesheet: {str(e)}")

    def setup_shortcuts(self) -> None:
        shortcuts = {
            "F8": self.toggle_play,
            "F7": lambda: self.change_position(-5000),
            "F9": lambda: self.change_position(5000),
            "F5": self.mark_in,
        }
        for key, slot in shortcuts.items():
            QShortcut(QKeySequence(key), self, slot)

    def setup_timers(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / 25))
        self.timer.timeout.connect(self.update_time_code)
        self.timer.start()

    def start_out_timer(self):
        if not self.out_timer.isActive():
            self.out_timer.start()

    def stop_out_timer(self):
        if self.out_timer.isActive():
            self.out_timer.stop()
            self.out_released.emit()

    def mark_in(self) -> None:
        try:
            position_ms = self.media_player.position()
            self.in_out_signal.emit("IN", position_ms)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error en mark_in: {str(e)}")

    def mark_out(self) -> None:
        try:
            position_ms = self.media_player.position()
            self.in_out_signal.emit("OUT", position_ms)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error en mark_out: {str(e)}")

    def toggle_play(self) -> None:
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def change_position(self, change: int) -> None:
        new_position = self.media_player.position() + change
        new_position = max(0, min(new_position, self.media_player.duration()))
        self.media_player.setPosition(new_position)

    def set_position(self, position: int) -> None:
        self.media_player.setPosition(position)

    def set_volume(self, volume: int) -> None:
        self.media_player.setVolume(volume)

    def update_volume_slider(self, volume: int) -> None:
        self.volume_slider_vertical.setValue(volume)

    def update_play_button(self, state: QMediaPlayer.State) -> None:
        self.play_button.setText("Pausa" if state == QMediaPlayer.PlayingState else "Play")

    def update_slider(self, position: int) -> None:
        self.slider.setValue(position)

    def update_slider_range(self, duration: int) -> None:
        self.slider.setRange(0, duration)

    def update_time_code(self) -> None:
        position = self.media_player.position()
        hours, remainder = divmod(position, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, msecs = divmod(remainder, 1000)
        frames = int(msecs / (1000 / 25))
        self.time_code_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}")

    def load_video(self, video_path: str) -> None:
        try:
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.media_player.play()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al cargar el video: {str(e)}")

    def on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        pass

    def on_media_error(self, error: QMediaPlayer.Error) -> None:
        if error != QMediaPlayer.NoError:
            QMessageBox.warning(self, "Error de Reproducción", self.media_player.errorString())

    def set_position_public(self, milliseconds: int) -> None:
        try:
            if 0 <= milliseconds <= self.media_player.duration():
                self.media_player.setPosition(milliseconds)
            else:
                QMessageBox.warning(self, "Error", "La posición especificada está fuera del rango del video.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al establecer la posición del video: {str(e)}")

    def detach_widget(self) -> None:
        self.detach_requested.emit(self)

    def toggle_volume_slider(self) -> None:
        self.volume_slider_vertical.setVisible(not self.volume_slider_vertical.isVisible())

    def update_fonts(self, font_size: int) -> None:
        font = QFont()
        font.setPointSize(font_size)

        self.play_button.setFont(font)
        self.rewind_button.setFont(font)
        self.forward_button.setFont(font)
        self.detach_button.setFont(font)
        self.in_button.setFont(font)
        self.out_button.setFont(font)
        self.volume_button.setFont(font)

        tc_font = QFont()
        tc_font.setPointSize(max(font_size - 2, 8))
        self.time_code_label.setFont(tc_font)

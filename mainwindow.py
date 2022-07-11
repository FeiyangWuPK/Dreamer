import sys, os
from typing import Optional
import wave
from pathlib import Path
import datetime

import PySide6
from PySide6 import QtCore
from PySide6.QtCore import QByteArray, QDir, QIODevice, QMargins, QRect, Qt, Signal, Slot, QThread, QUrl 
from PySide6.QtGui import QPainter, QPalette, QIcon
from PySide6.QtMultimedia import (
    QAudio,
    QAudioDevice,
    QAudioFormat,
    QAudioSource,
    QMediaDevices,
    QMediaCaptureSession,
    QAudioInput,
    QMediaRecorder,
    QMediaFormat,
)
from PySide6.QtWidgets import (
    QSpinBox,
    QMenu,
    QLabel,
    QLineEdit,
    QApplication,
    QComboBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

class AudioInfo:
    def __init__(self, format: QAudioFormat):
        super().__init__()
        self.m_format = format
        self.m_level = 0.0

    def calculate_level(self, data: bytes, length: int) -> float:
        channel_bytes: int = int(self.m_format.bytesPerSample())
        sample_bytes: int = int(self.m_format.bytesPerFrame())
        num_samples: int = int(length / sample_bytes)

        maxValue: float = 0
        m_offset: int = 0

        for i in range(num_samples):
            for j in range(self.m_format.channelCount()):
                value = 0
                if len(data) > m_offset:
                    data_sample = data[m_offset:]
                    value = self.m_format.normalizedSampleValue(data_sample)
                maxValue = max(value, maxValue)
                m_offset = m_offset + channel_bytes

        return maxValue

class RenderArea(QWidget):
    """
    For rendering audio level
    """
    def __init__(self, parent: Optional[PySide6.QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.m_level = 0
        # self.setBackgroundRole(QPalette.Base)
        self.setAutoFillBackground(True)
        self.setMinimumHeight(30)
        self.setMinimumWidth(200)
        self.setMaximumHeight(50)
        # self.setMaximumWidth(200)

    def set_level(self, value):
        self.m_level = value
        self.update()

    def paintEvent(self, event: PySide6.QtGui.QPaintEvent) -> None:
        with QPainter(self) as painter:
            painter.setPen(Qt.black)
            frame = painter.viewport() - QMargins(10, 10, 10, 10)

            painter.drawRect(frame)

            if self.m_level == 0.0:
                return

            pos: int = round((frame.width() - 1) * self.m_level)
            painter.fillRect(
                frame.left() + 1, frame.top() + 1, pos, frame.height() - 1, Qt.gray
            )


class DreamerMainWindow(QWidget):
    """
    Main window for dreamer
    """
    def __init__(self) -> None:
        super().__init__()
        self.m_devices = QMediaDevices(self)
        self.initialize_window()
        self.initialize_audio(QMediaDevices.defaultAudioInput())
    
    def initialize_window(self):
        '''
        Initialize layout
        '''

        self.resize(400, 200)
        self.layout = QVBoxLayout(self)

        self.m_canvas = RenderArea(self)

        # button for start pause and resume recording
        self.start_icon = QIcon("resources/start_btn.png")
        self.pause_icon = QIcon("resources/pause_btn.png")
        self.startbutton = QPushButton(self)
        self.startbutton.setFixedSize(QtCore.QSize(50, 50))
        self.startbutton.setIcon(self.start_icon)
        self.startbutton.setStyleSheet("background:transparent")

        self.pausebutton = QPushButton(self)
        self.pausebutton.setIcon(self.pause_icon)
        self.pausebutton.setStyleSheet("background:transparent")
        self.pausebutton.setFixedSize(QtCore.QSize(50, 50))

        recording_layout = QHBoxLayout()
        recording_layout.addWidget(self.startbutton)
        recording_layout.addWidget(self.pausebutton)
        recording_layout.addWidget(self.m_canvas)
        
        
        self.m_device_box = QComboBox(self)
        self.m_device_box.setMaximumWidth(200)
        default_device_info = QMediaDevices.defaultAudioInput()
        self.m_device_box.addItem(
            default_device_info.description(), default_device_info
        )

        for device_info in self.m_devices.audioInputs():
            if device_info != default_device_info:
                self.m_device_box.addItem(device_info.description(), device_info)

        self.m_device_box.activated[int].connect(self.device_changed)
        self.layout.addWidget(self.m_device_box)

        self.edit = QLineEdit("Waiting for audio input...")
        generate_hbox = QHBoxLayout()
        generate_hbox.addStretch(1)
        self.generate_btn = QPushButton()
        self.generate_btn.setMaximumWidth(100)
        self.generate_btn.setText("Generate")
        generate_hbox.addWidget(self.generate_btn)

        language_layout = QHBoxLayout()
        self.language_label = QLabel("Lanuage:")
        self.language_label.setMaximumWidth(100)
        self.language = QComboBox(self)
        self.language.addItems(["English", "Chinese", "German", "French", "Spanish"])
        self.language.setMaximumWidth(100)
        language_layout.addWidget(self.language_label)
        language_layout.addStretch(0)
        language_layout.addWidget(self.language)

        self.layout.addLayout(language_layout)
        self.layout.addWidget(self.edit)

        self.layout.addLayout(generate_hbox)

        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Select input device"))
        device_layout.addStretch(1)
        device_layout.addWidget(self.m_device_box)
        self.layout.addLayout(device_layout)
        self.layout.addLayout(recording_layout)

    def initialize_audio(self, device_info: QAudioDevice):
        self.session = QMediaCaptureSession()
        self.audioInput = QAudioInput()
        self.session.setAudioInput(self.audioInput)
        self.recorder = QMediaRecorder()
        self.session.setRecorder(self.recorder)
        self.recorder.setMediaFormat(QMediaFormat.Wave)
        self.recorder.setQuality(QMediaRecorder.HighQuality)
        now = datetime.datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
        fixent = now+"/recording"
        os.makedirs(now, exist_ok=True)
        filename = Path(QDir.currentPath()) / fixent
        url = QUrl.fromLocalFile(os.fspath(filename))
        self.recorder.setOutputLocation(url)
        self.recorder.stop()
        self.startbutton.clicked.connect(self.recorder.record)
        self.startbutton.clicked.connect(self.start_recording)

        self.pausebutton.clicked.connect(self.recorder.pause)
        self.pausebutton.clicked.connect(self.pause_recording)
        self.pausebutton.setVisible(False)

    
    @Slot(int)
    def start_recording(self):
        self.startbutton.setVisible(False)
        self.pausebutton.setVisible(True)
    
    @Slot(int)
    def pause_recording(self):
        self.pausebutton.setVisible(False)
        self.startbutton.setVisible(True)
        

    @Slot(int)
    def device_changed(self, index):
        self.recorder.stop()

    @Slot(int)
    def slider_changed(self, value):
        linearVolume = QAudio.convertVolume(
            value / float(100), QAudio.LogarithmicVolumeScale, QAudio.LinearVolumeScale
        )
        self.m_audio_input.setVolume(linearVolume)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Voice to image generation")
    mainwindow = DreamerMainWindow()
    mainwindow.show()
    sys.exit(app.exec())

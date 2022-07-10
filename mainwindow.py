import sys, os
from typing import Optional
import wave
from pathlib import Path
import datetime

import PySide6
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
        self.setMaximumHeight(30)
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
        # self.m_suspend_resume_button = QPushButton(self)
        # self.m_suspend_resume_button.setIcon(self.start_icon)
        # self.m_suspend_resume_button.setMaximumWidth(30)
        # self.m_suspend_resume_button.clicked.connect(self.toggle_suspend)
        # self.m_suspend_resume_button.setStyleSheet("background:transparent")
        self.startbutton = QPushButton(self)
        self.startbutton.setMaximumWidth(30)
        self.startbutton.setIcon(self.start_icon)
        self.startbutton.setStyleSheet("background:transparent")

        self.pausebutton = QPushButton(self)
        self.pausebutton.setIcon(self.pause_icon)
        self.pausebutton.setStyleSheet("background:transparent")
        self.pausebutton.setMaximumWidth(30)

        recording_layout = QHBoxLayout()
        recording_layout.addWidget(self.startbutton)
        recording_layout.addWidget(self.pausebutton)
        recording_layout.addWidget(self.m_canvas)
        self.layout.addLayout(recording_layout)
        
        self.m_device_box = QComboBox(self)
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
        
        self.generate_btn = QPushButton()
        self.layout.addWidget(self.edit)


    def initialize_audio(self, device_info: QAudioDevice):
        self.session = QMediaCaptureSession()
        self.audioInput = QAudioInput()
        self.session.setAudioInput(self.audioInput)
        self.recorder = QMediaRecorder()
        self.session.setRecorder(self.recorder)
        self.recorder.setMediaFormat(QMediaFormat.MP3)
        self.recorder.setQuality(QMediaRecorder.HighQuality)
        now = datetime.datetime.now().strftime("%m-%d-%Y-%H-%M-%S")
        fixent = now+"/recording"
        os.makedirs(now, exist_ok=True)
        filename = Path(QDir.currentPath()) / fixent
        url = QUrl.fromLocalFile(os.fspath(filename))
        self.recorder.setOutputLocation(url)
        self.recorder.stop()
        self.startbutton.clicked.connect(self.recorder.record)
        self.pausebutton.clicked.connect(self.recorder.pause)
        
    @Slot(int)
    def device_changed(self, index):
        self.m_audio_input.stop()
        self.m_audio_input.disconnect(self)
        self.initialize_audio(self.m_device_box.itemData(index))

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

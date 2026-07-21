from __future__ import annotations

from pathlib import Path

from src.shared.qt import (
    QAudioOutput,
    QLabel,
    QMediaPlayer,
    QSlider,
    Qt,
    QUrl,
    QVBoxLayout,
    QVideoWidget,
    QWidget,
)


class VideoPlayer(QWidget):
    """A small video surface used by the validation page."""

    def __init__(self, placeholder: str, parent=None):
        super().__init__(parent)
        self._path: Path | None = None
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.0)
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setObjectName("videoView")
        self.video_widget.setMinimumHeight(180)
        self.player.setVideoOutput(self.video_widget)

        self.placeholder = QLabel(placeholder, self)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setObjectName("imageView")
        self.placeholder.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget, 1)
        layout.addWidget(self.placeholder, 1)
        self.video_widget.hide()

    @property
    def path(self) -> Path | None:
        return self._path

    def set_source(self, path: str | Path | None, *, autoplay: bool = True) -> None:
        resolved = Path(path).resolve() if path else None
        if resolved == self._path and resolved is not None:
            self.placeholder.hide()
            self.video_widget.show()
            if autoplay:
                self.player.play()
            else:
                self.player.pause()
                self.player.setPosition(0)
            return
        self.player.stop()
        self._path = resolved
        if resolved is None or not resolved.exists():
            self.player.setSource(QUrl())
            self.video_widget.hide()
            self.placeholder.show()
            return
        self.player.setSource(QUrl.fromLocalFile(str(resolved)))
        self.placeholder.hide()
        self.video_widget.show()
        if autoplay:
            self.player.play()
        else:
            self.player.pause()
            self.player.setPosition(0)

    def clear(self) -> None:
        self.set_source(None, autoplay=False)

    def play(self) -> None:
        self.player.play()

    def stop(self) -> None:
        self.player.stop()

    def pause(self) -> None:
        self.player.pause()


class VideoPlaybackController:
    """Synchronize source/result playback and the shared seek slider."""

    def __init__(self, source: VideoPlayer, result: VideoPlayer, slider: QSlider):
        self.source = source
        self.result = result
        self.slider = slider
        self._duration = 0
        self._seeking = False
        self.source.player.positionChanged.connect(self._on_source_position)
        self.source.player.durationChanged.connect(self._on_duration_changed)
        self.slider.sliderPressed.connect(self._start_seek)
        self.slider.sliderReleased.connect(self._finish_seek)
        self.slider.sliderMoved.connect(self.seek_percent)

    def load_source(self, path: str | Path | None, *, autoplay: bool = True) -> None:
        self.source.set_source(path, autoplay=autoplay)
        if path is None or Path(path).resolve() != self.result.path:
            self.result.clear()
        self.slider.setValue(0)

    def load_result(self, path: str | Path | None, *, autoplay: bool = True) -> None:
        self.result.set_source(path, autoplay=autoplay)
        if path and autoplay:
            self._play_pair(restart=True)

    def play_pair(self, *, restart: bool = False) -> None:
        self._play_pair(restart=restart)

    def stop(self) -> None:
        self.source.stop()
        self.result.stop()

    def pause_pair(self) -> None:
        self.source.pause()
        self.result.pause()

    def seek_percent(self, value: int) -> None:
        if self._duration <= 0:
            return
        position = round(self._duration * max(0, min(1000, int(value))) / 1000)
        self.source.player.setPosition(position)
        if self.result.player.duration() > 0:
            self.result.player.setPosition(position)

    def _play_pair(self, *, restart: bool) -> None:
        if restart:
            self.source.player.setPosition(0)
            if self.result.player.duration() > 0:
                self.result.player.setPosition(0)
            self.slider.setValue(0)
        self.source.play()
        if self.result.path is not None:
            self.result.play()

    def _on_duration_changed(self, duration: int) -> None:
        self._duration = max(0, int(duration))

    def _on_source_position(self, position: int) -> None:
        if self._duration > 0 and not self._seeking:
            self.slider.setValue(round(position * 1000 / self._duration))
        if self.result.player.duration() > 0 and not self._seeking:
            result_position = min(position, self.result.player.duration())
            if abs(self.result.player.position() - result_position) > 80:
                self.result.player.setPosition(result_position)

    def _start_seek(self) -> None:
        self._seeking = True

    def _finish_seek(self) -> None:
        self._seeking = False
        self.seek_percent(self.slider.value())


__all__ = ["VideoPlayer", "VideoPlaybackController"]

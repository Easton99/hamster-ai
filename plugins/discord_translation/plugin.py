"""Discord Translation plugin — captures system audio and transcribes it locally.

Dependencies (all optional — plugin degrades gracefully if absent):
  pip install PyAudioWPatch faster-whisper webrtcvad

PyAudioWPatch provides WASAPI loopback for system audio on Windows.
faster-whisper runs Whisper locally (no internet, no audio saved to disk).
webrtcvad filters silence so Whisper only runs on speech segments.
"""
from __future__ import annotations

import collections
import struct
import threading
import time
from typing import TYPE_CHECKING

from app.plugins.plugin_base import PluginBase

if TYPE_CHECKING:
    from app.core.app_context import AppContext

# ── Optional dependency probes ────────────────────────────────────────────────

try:
    import pyaudiowpatch as _pa_lib
    _PYAUDIO_OK = True
except ImportError:
    try:
        import pyaudio as _pa_lib  # type: ignore
        _PYAUDIO_OK = True
    except ImportError:
        _pa_lib = None
        _PYAUDIO_OK = False

try:
    from faster_whisper import WhisperModel as _WhisperModel
    _WHISPER_OK = True
except ImportError:
    _WhisperModel = None
    _WHISPER_OK = False

try:
    import webrtcvad as _webrtcvad_lib
    _VAD_OK = True
except ImportError:
    _webrtcvad_lib = None
    _VAD_OK = False

_MISSING: list[str] = []
if not _PYAUDIO_OK:
    _MISSING.append("PyAudioWPatch (pip install PyAudioWPatch)")
if not _WHISPER_OK:
    _MISSING.append("faster-whisper (pip install faster-whisper)")

# ── Audio constants ────────────────────────────────────────────────────────────

_SAMPLE_RATE     = 16000
_CHANNELS        = 1
_SAMPLE_WIDTH    = 2        # 16-bit PCM
_FRAME_MS        = 30       # webrtcvad frame size
_FRAME_BYTES     = _SAMPLE_RATE * _CHANNELS * _SAMPLE_WIDTH * _FRAME_MS // 1000

_SILENCE_FRAMES  = 20       # ~600 ms silence ends a speech segment
_MAX_SEGMENT_SEC = 30       # discard segments longer than this (likely noise)
_MIN_SEGMENT_SEC = 0.4      # discard very short blips

_WHISPER_MODEL   = "tiny"   # tiny / base / small — use tiny for lowest resource use
_CAPTION_HISTORY = 20       # how many captions to keep in memory


class Plugin(PluginBase):
    name = "discord_translation"
    description = "Transcribes system/Discord audio locally using Whisper (offline)"
    enabled_by_default = False
    dependencies = []
    permissions_required = []

    def on_start(self, app: "AppContext") -> None:
        self._app = app
        self._active = False
        self._stop_evt = threading.Event()
        self._captions: collections.deque[str] = collections.deque(maxlen=_CAPTION_HISTORY)
        self._model = None
        self._thread: threading.Thread | None = None

        if _MISSING:
            app.logger.info(
                f"discord_translation: missing deps — {', '.join(_MISSING)}"
            )

    def on_stop(self, app: "AppContext") -> None:
        self._stop_capture()

    def on_event(self, event: str, data) -> None:
        modes = self._app.modes
        if modes and (modes.work_mode or modes.private_mode or modes.game_safe_mode):
            if self._active:
                self._stop_capture()
                app_ctx = self._app
                app_ctx.logger.info("discord_translation: paused due to protected mode.")

    def get_commands(self) -> dict:
        return {
            "/translate":  self._cmd_translate,
            "/captions":   self._cmd_captions,
        }

    # ── Start / stop capture ──────────────────────────────────────────────────

    def _start_capture(self) -> str:
        if _MISSING:
            return "Cannot start — missing: " + ", ".join(_MISSING)

        modes = self._app.modes
        if modes and (modes.work_mode or modes.private_mode or modes.game_safe_mode):
            return "Translation paused — a protected mode is active."

        if self._active:
            return "Translation already running."

        if self._model is None:
            self._app.logger.info(
                f"discord_translation: loading Whisper '{_WHISPER_MODEL}' model..."
            )
            try:
                self._model = _WhisperModel(
                    _WHISPER_MODEL,
                    device="cpu",
                    compute_type="int8",
                )
                self._app.logger.info("discord_translation: Whisper model loaded.")
            except Exception as exc:
                return f"Failed to load Whisper model: {exc}"

        self._stop_evt.clear()
        self._active = True
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="DiscordTranslation"
        )
        self._thread.start()

        self._app.event_bus.emit("notify", {
            "title": "Hamster AI",
            "body": "Translation active — listening to system audio.",
        })
        return "Translation started. Captions will appear as notifications."

    def _stop_capture(self) -> None:
        if not self._active:
            return
        self._active = False
        self._stop_evt.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=4)
        self._thread = None

    # ── Capture loop ──────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        pa = _pa_lib.PyAudio()
        stream = None
        try:
            device_index = _find_loopback_device(pa)
            if device_index is None:
                self._app.logger.warning(
                    "discord_translation: no WASAPI loopback device found. "
                    "Try PyAudioWPatch: pip install PyAudioWPatch"
                )
                self._active = False
                return

            dev_info = pa.get_device_info_by_index(device_index)
            host_rate = int(dev_info.get("defaultSampleRate", _SAMPLE_RATE))
            n_channels = min(int(dev_info.get("maxInputChannels", 1)), 2)

            stream = pa.open(
                format=_pa_lib.paInt16,
                channels=n_channels,
                rate=host_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
            )

            self._app.logger.info(
                f"discord_translation: capturing from device {device_index} "
                f"@ {host_rate} Hz, {n_channels}ch"
            )

            vad = _webrtcvad_lib.Vad(2) if _VAD_OK else None
            self._segment_loop(stream, host_rate, n_channels, vad)

        except Exception as exc:
            self._app.logger.error(f"discord_translation: capture error — {exc}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()
            self._active = False

    def _segment_loop(self, stream, host_rate: int, n_channels: int, vad) -> None:
        """Read from stream, segment on silence, transcribe each segment."""
        segment: list[bytes] = []
        silent_frames = 0
        speaking = False

        read_bytes = int(host_rate * _SAMPLE_WIDTH * n_channels * _FRAME_MS / 1000)

        while not self._stop_evt.is_set():
            try:
                raw = stream.read(read_bytes, exception_on_overflow=False)
            except Exception:
                break

            # Convert to mono 16-bit at 16000 Hz for VAD + Whisper
            mono = _to_mono_16k(raw, n_channels, host_rate)

            is_speech = _frame_is_speech(mono, vad, _SAMPLE_RATE)

            if is_speech:
                silent_frames = 0
                if not speaking:
                    speaking = True
                segment.append(mono)
            else:
                if speaking:
                    silent_frames += 1
                    segment.append(mono)
                    if silent_frames >= _SILENCE_FRAMES:
                        speaking = False
                        silent_frames = 0
                        self._transcribe_segment(segment)
                        segment = []

            # Safety: discard segments that grow too long (noise / music)
            seg_secs = len(segment) * _FRAME_MS / 1000
            if seg_secs > _MAX_SEGMENT_SEC:
                segment = []
                speaking = False

        # Transcribe whatever remains
        if segment:
            self._transcribe_segment(segment)

    # ── Transcription ─────────────────────────────────────────────────────────

    def _transcribe_segment(self, frames: list[bytes]) -> None:
        if not frames:
            return

        seg_secs = len(frames) * _FRAME_MS / 1000
        if seg_secs < _MIN_SEGMENT_SEC:
            return

        audio_bytes = b"".join(frames)
        try:
            import numpy as np
            audio_np = (
                np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            )
        except ImportError:
            # numpy unavailable — skip
            return

        try:
            segments, _ = self._model.transcribe(
                audio_np,
                language=self._app.settings.get("translation_language", None),
                task=self._app.settings.get("translation_task", "transcribe"),
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
        except Exception as exc:
            self._app.logger.debug(f"discord_translation: transcription error — {exc}")
            return

        if not text:
            return

        self._captions.append(text)
        self._app.logger.info(f"discord_translation: [{text}]")
        self._app.event_bus.emit("translation_caption", {"text": text})
        self._app.event_bus.emit("notify", {
            "title": "Translation",
            "body": text,
        })

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_translate(self, app: "AppContext", args: str) -> str:
        arg = args.strip().lower()
        if arg in ("on", "start", "enable"):
            return self._start_capture()
        if arg in ("off", "stop", "disable"):
            if not self._active:
                return "Translation is not running."
            self._stop_capture()
            return "Translation stopped."
        if self._active:
            self._stop_capture()
            return "Translation stopped."
        return self._start_capture()

    def _cmd_captions(self, app: "AppContext", args: str) -> str:
        if not self._captions:
            return "No captions yet."
        lines = list(self._captions)[-10:]
        return "Recent captions:\n" + "\n".join(f"  {c}" for c in lines)


# ── Audio helpers ──────────────────────────────────────────────────────────────

def _find_loopback_device(pa) -> int | None:
    """Find a WASAPI loopback input device (PyAudioWPatch adds these)."""
    try:
        # PyAudioWPatch exposes get_loopback_device_info_generator()
        for loopback in pa.get_loopback_device_info_generator():
            return loopback["index"]
    except AttributeError:
        pass

    # Fallback: scan for device names containing "loopback" or "stereo mix"
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info.get("name", "").lower()
        if info.get("maxInputChannels", 0) > 0 and (
            "loopback" in name or "stereo mix" in name or "what u hear" in name
        ):
            return i
    return None


def _to_mono_16k(raw: bytes, n_channels: int, host_rate: int) -> bytes:
    """Downmix to mono and resample to 16 kHz if needed."""
    n_samples = len(raw) // (_SAMPLE_WIDTH * n_channels)
    samples = struct.unpack(f"<{n_samples * n_channels}h", raw)

    # Downmix channels
    if n_channels > 1:
        mono_samples = [
            sum(samples[i * n_channels:(i + 1) * n_channels]) // n_channels
            for i in range(n_samples)
        ]
    else:
        mono_samples = list(samples)

    # Nearest-neighbour resample to 16000 Hz
    if host_rate != _SAMPLE_RATE:
        ratio = _SAMPLE_RATE / host_rate
        out_len = int(len(mono_samples) * ratio)
        resampled = [
            mono_samples[min(int(i / ratio), len(mono_samples) - 1)]
            for i in range(out_len)
        ]
        mono_samples = resampled

    return struct.pack(f"<{len(mono_samples)}h", *mono_samples)


def _frame_is_speech(frame: bytes, vad, rate: int) -> bool:
    """Return True if the frame likely contains speech."""
    if vad is None:
        # Simple energy gate when webrtcvad not available
        if len(frame) < 2:
            return False
        samples = struct.unpack(f"<{len(frame) // 2}h", frame)
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        return rms > 300

    try:
        # webrtcvad requires exact 10/20/30 ms frames at 8/16/32/48 kHz
        expected = rate * _SAMPLE_WIDTH * _FRAME_MS // 1000
        chunk = frame[:expected]
        if len(chunk) < expected:
            return False
        return vad.is_speech(chunk, rate)
    except Exception:
        return False

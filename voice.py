
"""
voice.py
JARVIS Voice Engine

Azure Speech:
- постійне розпізнавання
- wake word "Джарвіс" / "Назар"
- режим follow-up без wake word
- українська мова
- захист від дублікатів
- Azure TTS
- FIFINE AM8 через стандартний мікрофон Windows
"""

import os
import re
import time
import threading
import queue
import io
import wave

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

import requests
import sounddevice as sd
import numpy as np


# ============================================================
# ENV
# ============================================================

load_dotenv()

AZURE_SPEECH_KEY = os.getenv(
    "AZURE_SPEECH_KEY"
)

AZURE_SPEECH_REGION = os.getenv(
    "AZURE_SPEECH_REGION",
    ""
).strip().strip('"').strip("'")


if not AZURE_SPEECH_KEY:
    raise RuntimeError(
        "Не знайдено AZURE_SPEECH_KEY у .env"
    )


if not AZURE_SPEECH_REGION:
    raise RuntimeError(
        "Не знайдено AZURE_SPEECH_REGION у .env"
    )


# ============================================================
# SETTINGS
# ============================================================

DUPLICATE_TIMEOUT = 0.8

MIN_COMMAND_LENGTH = 2

FOLLOW_UP_TIMEOUT = 8

CONFIRM_TIMEOUT = 8


# ============================================================
# GLOBAL STATE
# ============================================================

TTS_ACTIVE = False

recognition_running = False

recognition_lock = threading.Lock()

recognition_queue = queue.Queue()

last_text = ""

last_text_time = 0.0


# ============================================================
# WAKE WORDS
# ============================================================

WAKE_WORDS = {
    # --------------------------------------------------------
    # JARVIS
    # --------------------------------------------------------

    "джарвис",
    "джарвіз",
    "джарвіс",
    "джарвісе",
    "джарвізе",

    "джервіс",
    "джервіз",
    "джервісе",

    "жарвіс",
    "жарвіз",
    "жарвісе",

    "джавис",
    "джавіс",
    "джавиз",

    "jarvis",

    # --------------------------------------------------------
    # NAZAR
    # --------------------------------------------------------

    "назар",
    "назaр",
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = str(text).lower().strip()

    text = (
        text
        .replace("ё", "е")
        .replace("’", "'")
        .replace("`", "'")
    )

    text = re.sub(
        r"[,.!?;:]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# WAKE WORD
# ============================================================

def is_wake_word(word: str) -> bool:

    word = normalize_text(word)

    return word in WAKE_WORDS


def remove_wake_word(text: str):

    if not text:
        return None

    text = normalize_text(text)

    if not text:
        return None

    words = text.split()

    if not words:
        return None

    # --------------------------------------------------------
    # Wake word перше слово
    # --------------------------------------------------------

    if is_wake_word(words[0]):

        return " ".join(
            words[1:]
        ).strip()

    # --------------------------------------------------------
    # Wake word десь у фразі
    # --------------------------------------------------------

    for index, word in enumerate(words):

        if is_wake_word(word):

            return " ".join(
                words[index + 1:]
            ).strip()

    return None


# ============================================================
# SPEECH CONFIG
# ============================================================

speech_config = speechsdk.SpeechConfig(
    subscription=AZURE_SPEECH_KEY,
    region=AZURE_SPEECH_REGION,
)

speech_config.speech_recognition_language = "uk-UA"

speech_config.output_format = (
    speechsdk.OutputFormat.Detailed
)


# ============================================================
# MICROPHONE
# ============================================================

audio_config = speechsdk.audio.AudioConfig(
    use_default_microphone=True
)


# ============================================================
# RECOGNIZER
# ============================================================

recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config,
    audio_config=audio_config,
)


# ============================================================
# DUPLICATE PROTECTION
# ============================================================

def is_duplicate(text: str) -> bool:

    global last_text
    global last_text_time

    normalized = normalize_text(text)

    if not normalized:
        return True

    now = time.time()

    if (
        normalized == last_text
        and
        now - last_text_time < DUPLICATE_TIMEOUT
    ):

        print(
            "[voice] Ігнорую дублікат."
        )

        return True

    last_text = normalized
    last_text_time = now

    return False


# ============================================================
# QUEUE CLEANUP
# ============================================================

def clear_recognition_queue():

    while True:

        try:

            recognition_queue.get_nowait()

        except queue.Empty:

            break


# ============================================================
# AZURE EVENTS
# ============================================================

def on_session_started(event):

    print(
        "[voice] Azure: session started."
    )


def on_session_stopped(event):

    global recognition_running

    recognition_running = False

    print(
        "[voice] Azure: session stopped."
    )


def on_canceled(event):

    print(
        "[voice] Azure cancellation:",
        event.reason
    )

    if (
        event.reason
        ==
        speechsdk.CancellationReason.Error
    ):

        print(
            "[voice] Azure error:",
            event.error_details
        )


def on_recognizing(event):

    # --------------------------------------------------------
    # НЕ використовуємо проміжні результати.
    #
    # Azure може давати:
    #
    # "відк..."
    # "відкрий..."
    # "відкрий відео..."
    #
    # Використовуємо тільки фінальний результат.
    # --------------------------------------------------------

    return


def on_recognized(evt):

    global TTS_ACTIVE

    # --------------------------------------------------------
    # Поки JARVIS говорить, не слухаємо власний голос.
    # --------------------------------------------------------

    if TTS_ACTIVE:

        return

    try:

        text = evt.result.text.strip()

    except Exception:

        return

    if not text:

        return

    # --------------------------------------------------------
    # Захист від дублікатів
    # --------------------------------------------------------

    if is_duplicate(text):

        return

    print(
        f"[voice] Azure почув: {text}"
    )

    recognition_queue.put(
        text
    )


# ============================================================
# CONNECT EVENTS
# ============================================================

_events_connected = False


def _connect_events():

    global _events_connected

    if _events_connected:

        return

    recognizer.session_started.connect(
        on_session_started
    )

    recognizer.session_stopped.connect(
        on_session_stopped
    )

    recognizer.canceled.connect(
        on_canceled
    )

    recognizer.recognizing.connect(
        on_recognizing
    )

    recognizer.recognized.connect(
        on_recognized
    )

    _events_connected = True


# ============================================================
# START RECOGNITION
# ============================================================

def start_recognition():

    global recognition_running

    with recognition_lock:

        if recognition_running:

            return

        clear_recognition_queue()

        _connect_events()

        recognition_running = True

        print(
            "[voice] Запускаю Azure "
            "continuous recognition..."
        )

        try:

            recognizer.start_continuous_recognition()

            print(
                "[voice] Azure recognition "
                "запущено."
            )

        except Exception as e:

            recognition_running = False

            print(
                f"[voice] Помилка запуску Azure: {e}"
            )

            raise


# ============================================================
# STOP RECOGNITION
# ============================================================

def stop_recognition():

    global recognition_running

    with recognition_lock:

        if not recognition_running:

            return

        try:

            recognizer.stop_continuous_recognition()

        except Exception as e:

            print(
                f"[voice] Помилка зупинки: {e}"
            )

        recognition_running = False


# ============================================================
# WAIT FOR TEXT
# ============================================================

def _wait_for_text(timeout=None):

    try:

        if timeout is None:

            return recognition_queue.get()

        return recognition_queue.get(
            timeout=timeout
        )

    except queue.Empty:

        return None


# ============================================================
# TTS
# ============================================================

def speak(text: str):

    global TTS_ACTIVE

    if not text:

        return

    text = str(text).strip()

    if not text:

        return

    TTS_ACTIVE = True

    print(
        "[voice] TTS: запуск синтезу..."
    )

    try:

        # ----------------------------------------------------
        # На час TTS очищаємо старі результати.
        # ----------------------------------------------------

        clear_recognition_queue()

        url = (
            f"https://{AZURE_SPEECH_REGION}"
            ".tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )

        headers = {

            "Ocp-Apim-Subscription-Key":
                AZURE_SPEECH_KEY,

            "Content-Type":
                "application/ssml+xml",

            "X-Microsoft-OutputFormat":
                "riff-24khz-16bit-mono-pcm",

            "User-Agent":
                "JARVIS",
        }

        escaped_text = (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        ssml = f"""
<speak version="1.0"
       xmlns="http://www.w3.org/2001/10/synthesis"
       xml:lang="uk-UA">
    <voice name="uk-UA-PolinaNeural">
        <prosody rate="0%" pitch="0%">
            {escaped_text}
        </prosody>
    </voice>
</speak>
"""

        response = requests.post(
            url,
            headers=headers,
            data=ssml.encode("utf-8"),
            timeout=15,
        )

        if response.status_code != 200:

            print(
                "[voice] TTS HTTP:",
                response.status_code
            )

            print(
                response.text
            )

            return

        with wave.open(
            io.BytesIO(
                response.content
            ),
            "rb"
        ) as wav:

            sample_rate = wav.getframerate()

            channels = wav.getnchannels()

            frames = wav.readframes(
                wav.getnframes()
            )

        audio = np.frombuffer(
            frames,
            dtype=np.int16
        )

        if channels > 1:

            audio = audio.reshape(
                -1,
                channels
            )

        print(
            f"[voice] TTS: "
            f"{sample_rate} Hz"
        )

        sd.play(
            audio,
            samplerate=sample_rate,
            blocking=True
        )

        sd.stop()

        print(
            "[voice] TTS завершено."
        )

        # ----------------------------------------------------
        # Даємо мікрофону час перестати ловити залишки TTS.
        # ----------------------------------------------------

        time.sleep(0.35)

        clear_recognition_queue()

    except Exception as e:

        print(
            f"[voice] TTS помилка: {e}"
        )

    finally:

        TTS_ACTIVE = False


# ============================================================
# LISTEN FOR COMMAND
# ============================================================

def listen_for_command(
    require_wake_word=True
) -> str:

    """
    require_wake_word=True

        Чекаємо:
        "Джарвіс + команда"

        або:
        "Назар + команда"

    require_wake_word=False

        Чекаємо одну команду протягом
        FOLLOW_UP_TIMEOUT секунд.
    """

    start_recognition()

    # ========================================================
    # FOLLOW-UP
    # ========================================================

    if not require_wake_word:

        print(
            "[voice] Follow-up режим: "
            "wake word НЕ потрібен. "
            f"Очікування {FOLLOW_UP_TIMEOUT} сек."
        )

        text = _wait_for_text(
            timeout=FOLLOW_UP_TIMEOUT
        )

        if not text:

            print(
                "[agent] Follow-up завершено: "
                f"{FOLLOW_UP_TIMEOUT} секунд "
                "минули без команди."
            )

            return ""

        command = normalize_text(
            text
        )

        if not command:

            return ""

        # ----------------------------------------------------
        # Якщо навіть у follow-up сказали:
        #
        # "Джарвіс відкрий Steam"
        #
        # прибираємо wake word.
        # ----------------------------------------------------

        possible = remove_wake_word(
            command
        )

        if possible is not None:

            if not possible:

                return ""

            command = possible

        if len(command) < MIN_COMMAND_LENGTH:

            return ""

        print(
            "[voice] Follow-up команда:",
            command
        )

        return command

    # ========================================================
    # NORMAL MODE
    # ========================================================

    print(
        "[voice] Слухаю фонові фрази..."
    )

    while True:

        text = _wait_for_text()

        if not text:

            continue

        command = remove_wake_word(
            text
        )

        # ----------------------------------------------------
        # Нема wake word
        # ----------------------------------------------------

        if command is None:

            print(
                "[voice] Ігнорую фразу "
                "без wake word."
            )

            continue

        print(
            "[voice] Wake word знайдено."
        )

        # ====================================================
        # ЛИШЕ WAKE WORD
        # ====================================================

        if not command:

            print(
                "🎤 Слухаю команду..."
            )

            command_text = _wait_for_text(
                timeout=FOLLOW_UP_TIMEOUT
            )

            if not command_text:

                speak(
                    "Не почув команду."
                )

                continue

            command = normalize_text(
                command_text
            )

            if not command:

                continue

            # ------------------------------------------------
            # Якщо користувач повторно сказав wake word,
            # прибираємо його.
            # ------------------------------------------------

            possible = remove_wake_word(
                command
            )

            if possible is not None:

                if possible:

                    command = possible

                else:

                    continue

            if len(command) < MIN_COMMAND_LENGTH:

                continue

            print(
                f"[voice] Команда: {command}"
            )

            return command

        # ====================================================
        # WAKE WORD + COMMAND
        # ====================================================

        if len(command) < MIN_COMMAND_LENGTH:

            continue

        print(
            f"[voice] Команда: {command}"
        )

        return command


# ============================================================
# VOICE CONFIRMATION
# ============================================================

YES_WORDS = (
    "так",
    "да",
    "yes",
    "підтверджую",
    "підтвердити",
    "confirm",
    "давай",
)

NO_WORDS = (
    "ні",
    "нет",
    "no",
    "скасувати",
    "скасувати дію",
    "відміна",
    "відміни",
    "не треба",
)


def voice_confirm(question: str) -> bool:

    """
    Озвучує питання і чекає голосової
    відповіді "так"/"ні".

    Якщо відповідь незрозуміла
    або користувач мовчить,
    дія скасовується.
    """

    speak(
        question +
        " Скажи так або ні."
    )

    text = listen_for_command(
        require_wake_word=False
    )

    if not text:

        speak(
            "Не почув відповідь. "
            "Скасовую дію."
        )

        return False

    normalized = normalize_text(
        text
    )

    # --------------------------------------------------------
    # Спочатку перевіряємо NO.
    #
    # Це важливо для фраз типу:
    # "ні, не треба"
    # --------------------------------------------------------

    if any(
        word in normalized
        for word in NO_WORDS
    ):

        return False

    if any(
        word in normalized
        for word in YES_WORDS
    ):

        return True

    speak(
        "Не зрозумів відповідь. "
        "Скасовую дію про всяк випадок."
    )

    return False


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 60
    )

    print(
        "JARVIS AZURE VOICE TEST"
    )

    print(
        "=" * 60
    )

    speak(
        "Голосовий модуль Джарвіса запущено."
    )

    try:

        while True:

            command = listen_for_command(
                require_wake_word=True
            )

            if not command:

                continue

            print(
                f"\nКОМАНДА: {command}"
            )

            if normalize_text(
                command
            ) in (
                "вихід",
                "вийти",
                "стоп",
                "exit",
            ):

                speak(
                    "До зустрічі."
                )

                break

    except KeyboardInterrupt:

        print(
            "\n[voice] Завершення..."
        )

    finally:

        stop_recognition()


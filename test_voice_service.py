import os
import sys
import django
import numpy as np
from scipy.io.wavfile import write

# Setup Django
sys.path.append('d:\\DISHA\\learnbridge')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learnbridge.settings')
django.setup()

from ai_tutor.voice_service import transcribe_audio, text_to_speech

def create_dummy_wav(filename):
    # Create a simple sine wave to avoid "random noise" looking like nothing to Whisper
    rate = 16000
    t = np.linspace(0, 3, rate * 3) # 3 seconds
    data = 0.5 * np.sin(2 * np.pi * 440 * t) # 440 Hz tone
    write(filename, rate, data.astype(np.float32))
    return filename

def test_tts():
    print("Testing TTS...")
    try:
        url = text_to_speech("Hello, this is a test of the emergency broadcast system.")
        print(f"TTS URL: {url}")
        if url and url.endswith(".wav"):
            print("TTS SUCCESS")
            # Check if file exists
            from django.conf import settings
            path = os.path.join(settings.MEDIA_ROOT, 'voice', os.path.basename(url))
            if os.path.exists(path):
                print(f"File verified at: {path}")
            else:
                print("File NOT found on disk!")
        else:
            print("TTS FAILED")
    except Exception as e:
        print(f"TTS CRASHED: {e}")

def test_stt():
    print("Testing STT (Tone)...")
    # Whisper might transcribe tone as music notes or silence or hallucinations
    # We just want to ensure it flows through the model without error.
    filename = "test_tone.wav"
    create_dummy_wav(filename)
    try:
        # Check if model loads
        text = transcribe_audio(filename)
        print(f"STT Result: '{text}'")
        print("STT RUN SUCCESS")
    except Exception as e:
        print(f"STT RUN FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_tts()
    print("-" * 20)
    test_stt()

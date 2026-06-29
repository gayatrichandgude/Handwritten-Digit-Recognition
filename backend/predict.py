# backend/predict.py
import os
import io
import base64
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from PIL import Image, ImageOps

# Load trained model
model_path = os.path.join(os.path.dirname(__file__), "../model/digit_model.h5")
model = load_model(model_path)

def predict_digit(img_path):
    """Predict digit from an uploaded image file."""
    img = image.load_img(img_path, target_size=(28, 28), color_mode="grayscale")
    img_array = image.img_to_array(img).reshape(1, 28, 28, 1) / 255.0
    prediction = model.predict(img_array, verbose=0)
    digit = int(np.argmax(prediction))
    confidence = round(float(np.max(prediction) * 100), 2)
    return digit, confidence

def predict_digit_from_canvas(img_data):
    import base64, os, time
    from PIL import Image, ImageOps
    import io
    import numpy as np

    # Decode base64
    img_str = img_data.split(",")[1]
    img_bytes = base64.b64decode(img_str)

    # Save image 🔥
    filename = f"draw_{int(time.time())}.png"
    save_path = os.path.join("static/uploads", filename)

    with open(save_path, "wb") as f:
        f.write(img_bytes)

    print("Saved DRAW image:", save_path)

    # Open image
    img = Image.open(io.BytesIO(img_bytes)).convert("L")

    # Preprocess
    img_array = np.array(img)
    if np.mean(img_array) < 128:
        img = Image.fromarray(255 - img_array)

    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        img = img.crop(bbox)

    img = img.resize((20, 20), Image.LANCZOS)

    new_img = Image.new("L", (28, 28), 255)
    new_img.paste(img, ((28 - 20)//2, (28 - 20)//2))

    img_array = np.array(new_img) / 255.0
    img_array = img_array.reshape(1, 28, 28, 1)

    # Predict
    pred = model.predict(img_array, verbose=0)
    digit = int(np.argmax(pred))
    confidence = round(float(np.max(pred) * 100), 2)

    # 🔥 IMPORTANT: return image_path also
    return {
        "digit": digit,
        "confidence": confidence,
        "image_path": filename
    }
    
def predict_digit_from_voice(audio_path):
    import speech_recognition as sr
    from pydub import AudioSegment
    import os

    recognizer = sr.Recognizer()

    try:
        # DEBUG
        print("File size:", os.path.getsize(audio_path))

        # Convert to proper WAV
        sound = AudioSegment.from_file(audio_path)
        wav_path = audio_path.replace(".wav", "_converted.wav")
        sound = sound.set_frame_rate(16000).set_channels(1)
        sound.export(wav_path, format="wav")

        # Read audio
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio, language='en-US')
            print("Recognized text:", text)
        except Exception as e:
            print("Recognition failed FULL:", repr(e))
            return 0, 10.0

        # Process text
        text = text.lower().strip()
        print("Processed text:", text)

        digit_words = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9
        }

        # Exact match
        if text in digit_words:
            return digit_words[text], 95.0

        # Partial match fallback
        for word, digit in digit_words.items():
            if word in text:
                return digit, 80.0

        return 0, 50.0

    except Exception as e:
        print("FULL ERROR:", e)
        return 0, 10.0
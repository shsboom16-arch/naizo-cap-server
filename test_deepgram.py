import os
import json
import urllib.request
import urllib.parse
import mimetypes

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"

def transcribe_audio_deepgram(audio_path_or_url, api_key, language="ar", model="nova-3"):
    """
    Transcribes audio using Deepgram API and requests word-level timestamps.
    Supports either a local audio file or a direct audio URL.
    """
    query_params = {
        "model": model,
        "smart_format": "true",
        "punctuate": "true",
        "words": "true"
    }
    
    # If language is 'auto' or empty, use detect_language
    if language in ("auto", "detect", ""):
        query_params["detect_language"] = "true"
    else:
        query_params["language"] = language
        
    url = f"{DEEPGRAM_API_URL}?{urllib.parse.urlencode(query_params)}"
    
    headers = {
        "Authorization": f"Token {api_key}"
    }

    if audio_path_or_url.startswith("http://") or audio_path_or_url.startswith("https://"):
        headers["Content-Type"] = "application/json"
        data = json.dumps({"url": audio_path_or_url}).encode("utf-8")
    else:
        if not os.path.exists(audio_path_or_url):
            raise FileNotFoundError(f"Audio file not found: {audio_path_or_url}")
            
        mime_type, _ = mimetypes.guess_type(audio_path_or_url)
        headers["Content-Type"] = mime_type or "audio/wav"
        with open(audio_path_or_url, "rb") as f:
            data = f.read()

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"Deepgram API Error ({e.code}): {error_body}")

def extract_words_with_timestamps(deepgram_response):
    """
    Extracts structured words and timestamps:
    [
        {"word": "أهلاً", "start": 0.42, "end": 0.85, "confidence": 0.98},
        ...
    ]
    """
    results = deepgram_response.get("results", {})
    channels = results.get("channels", [])
    if not channels:
        return []
        
    words = []
    alternatives = channels[0].get("alternatives", [])
    if alternatives:
        raw_words = alternatives[0].get("words", [])
        for w in raw_words:
            words.append({
                "word": w.get("punctuated_word", w.get("word")),
                "start": w.get("start"),
                "end": w.get("end"),
                "confidence": round(w.get("confidence", 0), 2)
            })
    return words

if __name__ == "__main__":
    import sys
    print("Deepgram Transcription Client Ready.")
    if len(sys.argv) > 2:
        api_key = sys.argv[1]
        audio_target = sys.argv[2]
        lang = sys.argv[3] if len(sys.argv) > 3 else "ar"
        print(f"Transcribing {audio_target} in language {lang}...")
        try:
            res = transcribe_audio_deepgram(audio_target, api_key, language=lang)
            extracted = extract_words_with_timestamps(res)
            print(f"Success! Extracted {len(extracted)} words.")
            print(json.dumps(extracted[:5], ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python3 test_deepgram.py <DEEPGRAM_API_KEY> <AUDIO_FILE_OR_URL> [LANGUAGE]")

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import cgi
import tempfile
from test_deepgram import transcribe_audio_deepgram, extract_words_with_timestamps
from segmentation import segment_words_into_captions, generate_srt_content

PORT = int(os.environ.get("PORT", 8080))
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")

# Automatically load from local .env if present
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
                if k.strip() == "DEEPGRAM_API_KEY" and not DEEPGRAM_API_KEY:
                    DEEPGRAM_API_KEY = v.strip()

class CaptionsAPIHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        status_info = {
            "status": "online",
            "service": "Auto Captions Backend for Adobe Premiere",
            "has_deepgram_key": bool(DEEPGRAM_API_KEY)
        }
        self.wfile.write(json.dumps(status_info).encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/transcribe":
            self.handle_transcribe()
        elif self.path == "/api/segment":
            self.handle_segment()
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Endpoint not found"}')

    def handle_transcribe(self):
        """
        Receives multipart audio file from Premiere UXP plugin,
        sends to Deepgram, and returns word-level timestamps JSON.
        """
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_response(400)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Expected multipart/form-data"}')
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
        )

        audio_item = form.getfirst("audio")
        lang = form.getfirst("language", "ar")
        api_key_override = form.getfirst("api_key", DEEPGRAM_API_KEY)

        if not api_key_override:
            self.send_response(400)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Deepgram API key is required"}')
            return

        if not audio_item:
            self.send_response(400)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "No audio file provided in field \'audio\'"}')
            return

        # Save temporarily
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            if hasattr(audio_item, "file"):
                temp_audio.write(audio_item.file.read())
            else:
                temp_audio.write(audio_item.encode("latin1") if isinstance(audio_item, str) else audio_item)
            temp_audio.close()

            # Call Deepgram
            deepgram_res = transcribe_audio_deepgram(temp_audio.name, api_key_override, language=lang)
            words = extract_words_with_timestamps(deepgram_res)

            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "words": words}, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        finally:
            if os.path.exists(temp_audio.name):
                try:
                    os.remove(temp_audio.name)
                except Exception:
                    pass

    def handle_segment(self):
        """
        Takes raw words list and segment params, returns re-calculated caption blocks and SRT.
        """
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            req_data = json.loads(body.decode("utf-8"))
            words = req_data.get("words", [])
            max_words_per_line = int(req_data.get("max_words_per_line", 4))
            max_lines = int(req_data.get("max_lines", 2))
            
            blocks = segment_words_into_captions(words, max_words_per_line, max_lines)
            srt = generate_srt_content(blocks)
            
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "blocks": blocks, "srt": srt}, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_response(400)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), CaptionsAPIHandler)
    print(f"Captions Backend Server running on http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()

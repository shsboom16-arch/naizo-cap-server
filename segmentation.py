import math

def format_timestamp_srt(seconds):
    """
    Converts seconds (e.g. 12.345) to SRT timestamp format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def segment_words_into_captions(words, max_words_per_line=4, max_lines=2, max_pause_sec=0.7):
    """
    Groups individual words with timestamps into optimal subtitle blocks.
    Respects:
      - max_words_per_line (e.g. 4 words)
      - max_lines (e.g. 1 or 2 lines)
      - Natural pauses in speech (if gap between words > max_pause_sec, break segment)
    """
    if not words:
        return []

    captions = []
    current_segment_words = []
    
    max_total_words = max_words_per_line * max_lines

    for i, w in enumerate(words):
        if not current_segment_words:
            current_segment_words.append(w)
            continue
            
        prev_word = current_segment_words[-1]
        pause = w["start"] - prev_word["end"]
        
        # Check breaking conditions:
        # 1. Total words limit reached
        # 2. Significant pause detected
        # 3. Punctuation ending strong sentence (. ؟ !)
        should_break = False
        
        if len(current_segment_words) >= max_total_words:
            should_break = True
        elif pause >= max_pause_sec:
            should_break = True
        elif prev_word["word"].endswith(('.', '؟', '!', '?')):
            should_break = True
            
        if should_break:
            captions.append(_build_caption_block(current_segment_words, max_words_per_line))
            current_segment_words = [w]
        else:
            current_segment_words.append(w)

    if current_segment_words:
        captions.append(_build_caption_block(current_segment_words, max_words_per_line))

    return captions

def _build_caption_block(words_chunk, max_words_per_line):
    start = words_chunk[0]["start"]
    end = words_chunk[-1]["end"]
    
    # Split into lines based on max_words_per_line
    lines = []
    for i in range(0, len(words_chunk), max_words_per_line):
        line_words = words_chunk[i:i + max_words_per_line]
        lines.append(" ".join(w["word"] for w in line_words))
        
    full_text = "\n".join(lines)
    return {
        "start": start,
        "end": end,
        "text": full_text,
        "words": words_chunk
    }

def generate_srt_content(caption_blocks):
    """
    Generates standard SRT formatted text from caption blocks.
    """
    srt_lines = []
    for idx, block in enumerate(caption_blocks, 1):
        start_srt = format_timestamp_srt(block["start"])
        end_srt = format_timestamp_srt(block["end"])
        srt_lines.append(str(idx))
        srt_lines.append(f"{start_srt} --> {end_srt}")
        srt_lines.append(block["text"])
        srt_lines.append("")  # Empty line separator
    return "\n".join(srt_lines)

if __name__ == "__main__":
    # Test example with Arabic words and timestamps
    sample_words = [
        {"word": "أهلاً", "start": 0.20, "end": 0.55},
        {"word": "وسهلاً", "start": 0.58, "end": 0.95},
        {"word": "بكم", "start": 0.98, "end": 1.25},
        {"word": "في", "start": 1.30, "end": 1.45},
        {"word": "تجربة", "start": 1.50, "end": 1.90},
        {"word": "Auto", "start": 1.95, "end": 2.30},
        {"word": "Captions", "start": 2.35, "end": 2.80},
        {"word": "لأدوبي", "start": 2.85, "end": 3.20},
        {"word": "بريمير", "start": 3.25, "end": 3.65},
        {"word": "برو.", "start": 3.70, "end": 4.10},
    ]
    
    print("Testing Smart Segmentation (4 words/line, 2 lines max):")
    blocks = segment_words_into_captions(sample_words, max_words_per_line=4, max_lines=2)
    srt_out = generate_srt_content(blocks)
    print("--- Generated SRT Output ---")
    print(srt_out)

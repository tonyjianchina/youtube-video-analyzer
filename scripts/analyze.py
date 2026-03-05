#!/usr/bin/env python3
"""
YouTube Video Analyzer - Extract transcripts and generate investment summaries
"""

import os
import sys
import argparse
import subprocess
import requests
import re
from pathlib import Path


def get_api_key():
    """Get LLM API key from environment variables"""
    # Priority order: MINIMAX > OPENAI > MOONSHOT
    api_key = (
        os.environ.get("MINIMAX_API_KEY") or
        os.environ.get("OPENAI_API_KEY") or
        os.environ.get("MOONSHOT_API_KEY")
    )
    
    if not api_key:
        print("Error: No LLM API key configured.", file=sys.stderr)
        print("\nPlease set one of the following environment variables:", file=sys.stderr)
        print("  export MINIMAX_API_KEY='your-key'", file=sys.stderr)
        print("  export OPENAI_API_KEY='your-key'", file=sys.stderr)
        print("  export MOONSHOT_API_KEY='your-key'", file=sys.stderr)
        sys.exit(1)
    
    return api_key


def detect_api_provider(api_key):
    """Detect API provider from key format"""
    if os.environ.get("MINIMAX_API_KEY"):
        return "minimax"
    elif os.environ.get("OPENAI_API_KEY"):
        return "openai"
    elif os.environ.get("MOONSHOT_API_KEY"):
        return "moonshot"
    else:
        # Fallback detection
        if api_key.startswith("sk-cp-"):
            return "minimax"
        elif api_key.startswith("sk-") and len(api_key) > 50:
            return "moonshot"
        else:
            return "openai"


def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_video_title(video_id):
    """Get video title from YouTube page"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--print', 'title', f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "Unknown Title"


def extract_transcript(video_id, language="Chinese"):
    """Extract transcript from video - tries subtitles first, then Whisper"""
    print(f"Extracting transcript for {video_id}...")
    
    # Step 1: Try to get existing subtitles
    print("  Checking for existing subtitles...")
    result = subprocess.run(
        ['yt-dlp', '--list-subs', f'https://www.youtube.com/watch?v={video_id}'],
        capture_output=True, text=True, timeout=30
    )
    
    has_subs = 'has subtitles' in result.stdout or 'has automatic captions' in result.stdout
    
    if has_subs:
        # Try to download subtitles
        print("  Downloading subtitles...")
        for lang in ['zh-CN', 'zh-TW', 'zh-Hans', 'zh-Hant', 'zh', 'en']:
            result = subprocess.run(
                ['yt-dlp', '--write-sub', '--sub-langs', lang,
                 '--skip-download', '-o', f'/tmp/yt_{video_id}',
                 f'https://www.youtube.com/watch?v={video_id}'],
                capture_output=True, text=True, timeout=60
            )
            
            # Check for downloaded subtitle files
            for ext in ['.vtt', '.srt', '.ttml']:
                sub_file = f'/tmp/yt_{video_id}.{lang}{ext}'
                if os.path.exists(sub_file):
                    with open(sub_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Clean up
                    clean_vtt(content, sub_file)
                    transcript = extract_text_from_vtt(sub_file)
                    if transcript:
                        # Cleanup
                        try:
                            os.remove(sub_file)
                        except:
                            pass
                        return transcript
    
    # Step 2: Use Whisper for transcription
    print("  No subtitles found. Using Whisper...")
    return transcribe_with_whisper(video_id, language)


def clean_vtt(content, output_file):
    """Clean VTT file for processing"""
    lines = content.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        # Skip VTT headers and timing lines
        if line and not line.startswith(('WEBVTT', 'NOTE', 'STYLE', '-->')):
            if not re.match(r'^\d{2}:\d{2}', line):
                cleaned.append(line)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned))


def extract_text_from_vtt(file_path):
    """Extract plain text from VTT/SRT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove timing lines and tags
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not re.match(r'^\d+$', line) and '-->' not in line:
                # Remove HTML-like tags
                line = re.sub(r'<[^>]+>', '', line)
                lines.append(line)
        
        text = ' '.join(lines)
        # Limit length
        return text[:5000] if text else None
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None


def transcribe_with_whisper(video_id, language="Chinese"):
    """Transcribe video using Whisper"""
    print(f"  Downloading audio...")
    
    audio_file = f'/tmp/yt_{video_id}.mp3'
    
    # Download audio
    result = subprocess.run(
        ['yt-dlp', '-x', '--audio-format', 'mp3',
         '-o', audio_file,
         f'https://www.youtube.com/watch?v={video_id}'],
        capture_output=True, text=True, timeout=120
    )
    
    if not os.path.exists(audio_file):
        print("  Failed to download audio")
        return None
    
    print(f"  Transcribing with Whisper ({language})...")
    
    # Run Whisper
    result = subprocess.run(
        ['python3', '-m', 'whisper', audio_file,
         '--model', 'tiny',
         '--language', language,
         '--output_format', 'txt',
         '--output_dir', '/tmp'],
        capture_output=True, text=True, timeout=180
    )
    
    transcript_file = f'/tmp/yt_{video_id}.txt'
    transcript = None
    
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript = f.read()[:5000]
    
    # Cleanup
    try:
        if os.path.exists(audio_file):
            os.remove(audio_file)
        if os.path.exists(transcript_file):
            os.remove(transcript_file)
    except:
        pass
    
    return transcript


def generate_summary(transcript, title, api_key, provider):
    """Generate structured investment summary using LLM"""
    print("  Generating investment summary...")
    
    prompt = f"""你是一个专业的投资分析师。请分析以下YouTube视频内容，并按照固定格式输出投资摘要。

视频标题：{title}

转录内容：
{transcript[:4000]}

请按以下格式输出：

📌 **核心观点**
[用2-3句话说明：背景/前提 → 关键逻辑链条 → 结论]

🎯 **投资标的**
• [具体标的名称]：[一句话说明为什么这个标的最受益]

⚠️ **风险提示**
• [主要风险1]：[简要说明]
• [主要风险2]：[简要说明]

要求：
1. 核心观点要有逻辑推导过程
2. 投资标的要具体，说明受益逻辑
3. 风险要包含反方观点和市场误判
4. 简洁明了，总共不超过300字
"""
    
    if provider == "minimax":
        return call_minimax(prompt, api_key)
    elif provider == "openai":
        return call_openai(prompt, api_key)
    elif provider == "moonshot":
        return call_moonshot(prompt, api_key)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def call_minimax(prompt, api_key):
    """Call MiniMax API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "MiniMax-M2.5",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    response = requests.post(
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
        headers=headers, json=payload, timeout=120
    )
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def call_openai(prompt, api_key):
    """Call OpenAI API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers, json=payload, timeout=120
    )
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def call_moonshot(prompt, api_key):
    """Call Moonshot (Kimi) API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "kimi-k2.5",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0
    }
    
    response = requests.post(
        "https://api.moonshot.cn/v1/chat/completions",
        headers=headers, json=payload, timeout=120
    )
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def format_output(title, channel, summary, url):
    """Format final output"""
    return f"""📺 **YouTube Video Analysis**

**{channel}** — *{title}*

{summary}

🔗 [Watch Video]({url})
"""


def main():
    parser = argparse.ArgumentParser(description="Analyze YouTube videos and generate investment summaries")
    parser.add_argument("url", help="YouTube video URL or video ID")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--language", "-l", default="Chinese", help="Language for Whisper transcription (default: Chinese)")
    
    args = parser.parse_args()
    
    # Get API credentials
    api_key = get_api_key()
    provider = detect_api_provider(api_key)
    print(f"Using LLM provider: {provider}")
    
    # Extract video ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"Error: Could not extract video ID from: {args.url}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Video ID: {video_id}")
    
    # Get video title
    title = get_video_title(video_id)
    print(f"Title: {title}")
    
    # Extract transcript
    transcript = extract_transcript(video_id, args.language)
    
    if not transcript:
        print("Error: Could not extract transcript", file=sys.stderr)
        sys.exit(1)
    
    print(f"Transcript length: {len(transcript)} chars")
    
    # Generate summary
    summary = generate_summary(transcript, title, api_key, provider)
    
    # Format output
    channel = "YouTube Channel"  # Could extract this if needed
    output = format_output(title, channel, summary, f"https://www.youtube.com/watch?v={video_id}")
    
    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\nAnalysis saved to: {args.output}")
    else:
        print("\n" + "="*50)
        print(output)
        print("="*50)


if __name__ == "__main__":
    main()

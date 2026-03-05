---
name: youtube-video-analyzer
description: Analyze YouTube videos by extracting transcripts and generating investment summaries. Use when user wants to extract insights, transcripts, or investment analysis from YouTube videos. Supports automatic subtitle extraction, Whisper fallback for videos without subtitles, and LLM-powered summary generation with structured output (core thesis, investment targets, risk warnings).
---

# YouTube Video Analyzer

Extract transcripts from YouTube videos and generate structured investment analysis summaries.

## Features

- **Automatic subtitle extraction** - Uses yt-dlp to get existing subtitles
- **Whisper fallback** - Transcribes audio for videos without subtitles
- **LLM-powered analysis** - Generates structured investment summaries
- **Structured output** - Core thesis, investment targets, risk warnings

## Setup

### Prerequisites

```bash
# Install required tools
brew install yt-dlp ffmpeg

# Install Python dependencies
pip3 install openai-whisper requests
```

### API Configuration

This skill requires an LLM API key. Set one of the following environment variables:

```bash
# Option 1: MiniMax (recommended)
export MINIMAX_API_KEY="your-minimax-api-key"

# Option 2: OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# Option 3: Moonshot (Kimi)
export MOONSHOT_API_KEY="your-moonshot-api-key"
```

Or create a `.env` file in your workspace:

```
MINIMAX_API_KEY=your-api-key-here
```

## Usage

### Command Line

```bash
# Analyze a YouTube video
python3 scripts/analyze.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Output to file
python3 scripts/analyze.py "https://youtu.be/VIDEO_ID" --output analysis.md

# Specify language for Whisper
python3 scripts/analyze.py "URL" --language Chinese
```

### From OpenClaw

When this skill is triggered, Codex will:

1. Extract the video ID from the URL
2. Attempt to get existing subtitles (zh-CN, zh-TW, en)
3. Fall back to Whisper transcription if no subtitles available
4. Generate structured investment summary using LLM
5. Output formatted analysis

## Output Format

The generated analysis follows this structure:

```
📌 **核心观点**
[Background → Logic Chain → Conclusion]

🎯 **投资标的**
• [Ticker/Name]: [Benefit logic]

⚠️ **风险提示**
• [Risk 1]: [Description]
• [Risk 2]: [Description]
```

## How It Works

1. **Video Processing**: yt-dlp downloads subtitles or audio
2. **Transcription**: Whisper (local, free) transcribes audio when needed
3. **Analysis**: LLM generates structured investment summary
4. **Output**: Formatted markdown with emojis and sections

## Cost

- **Subtitles**: Free (uses YouTube's existing subtitles)
- **Whisper**: Free (runs locally on your machine)
- **LLM API**: Depends on your provider (MiniMax, OpenAI, etc.)

## Troubleshooting

**"No API key configured"**
→ Set MINIMAX_API_KEY, OPENAI_API_KEY, or MOONSHOT_API_KEY environment variable

**"yt-dlp not found"**
→ Run: `brew install yt-dlp`

**"Whisper model not found"**
→ Run: `pip3 install openai-whisper`

**"Video has no audio"**
→ Some videos may be region-restricted or removed

## Example

Input video: "霍尔木兹一封，全球AI停摆？华尔街没算到的致命死角"

Output:
```
📌 **核心观点**
霍尔木兹海峡若被封锁，卡塔尔氦气出口将中断。氦气是半导体制造的关键材料，亚洲库存仅2-4周。三星/SK海力士/台积电严重依赖卡塔尔氦气（50-60%），一旦断供将被迫减产，导致全球AI芯片供需失衡。

🎯 **投资标的**
• 美光科技(MU)：拥有北美本土氦气供应链，不受海峡封锁影响，可满产收割涨价红利并抢占HBM市场份额

⚠️ **风险提示**
• 战争结束快于预期：华尔街预期危机一个月内结束
• 替代供应方案：卡塔尔可能通过其他途径缓解短缺
• 需求端风险：AI硬件扩张计划若放缓，涨价逻辑失效
```

## License

MIT

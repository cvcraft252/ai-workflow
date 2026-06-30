# AI-Workflow 🏗️

> "Why read a construction summary for 10 seconds when you can spend 2 hours configuring API keys to let an LLM do it for you?"

## What is this?
A highly over-engineered script that takes paragraphs of civil engineering descriptions and converts them into nice, tidy JSON. Because reading actual text and copy-pasting is *so* last year.

## Features
- **Zero Brain Cells Required**: You feed it text, it feeds you JSON. 
- **Strictly No Guessing**: The LLM is explicitly forbidden from hallucinating floor counts. We don't want a 100-story skyscraper where a parking garage should be.
- **Windows-Proof**: Built-in encoding fixes so Windows PowerShell doesn't explode over a simple `👉` emoji.

## Setup (If you dare)
1. Copy `.env.example` to `.env`.
2. Insert your precious API key and base URL.
3. Run `python main.py` or `uv run main.py`.
4. Stare at the JSON output and wonder if it was worth the $0.002 API call.

## Tech Stack
- **Python**: Because indentation makes us feel organized.
- **Pydantic**: Keeping the LLM from outputting emojis when we asked for integers.
- **OpenAI SDK**: Talking to DeepSeek using OpenAI client, because API compatibility is a beautiful lie.

---
*Disclaimer: Do not use this tool to design actual bridges. We are not responsible for any falling concrete.*

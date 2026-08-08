# Using Claude Code with Ollama on Mac

A complete guide to running Claude Code locally using open-source models via Ollama — no Anthropic API costs, full privacy.

---

## What's Happening Here?

Claude Code is Anthropic's terminal-based agentic coding tool. Normally it talks to Anthropic's cloud. But since **Ollama v0.14+**, Ollama supports the Anthropic Messages API format — meaning Claude Code can be pointed at your local Ollama server instead, and it won't know the difference.

**What you get:**
- Zero API costs (inference runs on your machine)
- Your code never leaves your computer
- Works offline
- Use any Ollama-supported model

**The tradeoff:** Local models are slower and less capable than Anthropic's Sonnet/Opus. For most coding tasks, prototyping, and learning — they're more than good enough.

---

## Prerequisites

- macOS (Apple Silicon or Intel)
- Ollama already installed ✅
- Node.js v18+ installed (needed for Claude Code)
- At least **16GB RAM** (32GB recommended for better models)

Check your Node version:
```bash
node --version
```

If you don't have Node.js, install it via Homebrew:
```bash
brew install node
```

---

## Step 1 — Update Ollama to v0.14+

Tool calling support (which Claude Code's agentic loop requires) was added in Ollama v0.14. Make sure you're on a recent version.

Check your current version:
```bash
ollama --version
```

Update Ollama by downloading the latest version from [ollama.com/download](https://ollama.com/download) and re-running the installer, or via Homebrew if you installed it that way:
```bash
brew upgrade ollama
```

---

## Step 2 — Pull a Good Coding Model

Not all Ollama models work well with Claude Code. You need one with **native tool calling support** and a **large context window**.

These are the top recommended models:

| Model | Size | Good For |
|---|---|---|
| `qwen3-coder` | ~8B–32B | Best overall coding model |
| `glm-4.7-flash` | 30B MoE (3B active) | Fast, great tool calling |
| `devstral` | 24B | Strong coding, good on Apple Silicon |

Pull your chosen model (start with `qwen3-coder` if unsure):
```bash
ollama pull qwen3-coder
```

Or for a lighter/faster option:
```bash
ollama pull glm-4.7-flash
```

This will download the model files — may take a few minutes depending on your connection.

Verify it downloaded:
```bash
ollama list
```

---

## Step 3 — Configure Ollama's Context Window

Claude Code needs a **large context window** to function properly — it sends a lot of code and conversation history with each request. The default Ollama context is too small.

You need to restart Ollama with a larger context size.

**First, stop Ollama** if it's running (quit from the menu bar icon, or):
```bash
pkill ollama
```

**Then restart it with an extended context:**
```bash
OLLAMA_CONTEXT_LENGTH=65536 ollama serve
```

> **Why 65536?** That's 64k tokens. Claude Code's docs recommend at least 32k, and 64k gives comfortable headroom for larger codebases. If you run out of RAM, try 32768 instead.

Keep this terminal window open — Ollama needs to stay running. Open a new terminal tab for the remaining steps.

**Optional: Make this permanent**

If you want Ollama to always start with this context size, add it to your shell profile (`~/.zshrc` for most Macs):
```bash
echo 'export OLLAMA_CONTEXT_LENGTH=65536' >> ~/.zshrc
source ~/.zshrc
```

Then you can launch Ollama normally and it will use 64k context automatically.

---

## Step 4 — Install Claude Code

Claude Code is installed as an npm global package:
```bash
npm install -g @anthropic-ai/claude-code
```

Verify it installed:
```bash
claude --version
```

---

## Step 5 — Set Environment Variables

This is the key step. These three variables tell Claude Code to talk to your local Ollama server instead of Anthropic's cloud.

**Option A: Set them temporarily (for this terminal session only)**
```bash
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=http://localhost:11434
```

**Option B: Set them permanently (recommended)**

Add to your `~/.zshrc`:
```bash
echo 'export ANTHROPIC_AUTH_TOKEN=ollama' >> ~/.zshrc
echo 'export ANTHROPIC_API_KEY=""' >> ~/.zshrc
echo 'export ANTHROPIC_BASE_URL=http://localhost:11434' >> ~/.zshrc
source ~/.zshrc
```

**What each variable does:**

| Variable | Value | Why |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://localhost:11434` | Points Claude Code at your local Ollama server instead of Anthropic's API |
| `ANTHROPIC_AUTH_TOKEN` | `ollama` | Claude Code requires an auth token. This dummy value satisfies that requirement |
| `ANTHROPIC_API_KEY` | `""` | Set to empty so no real API key is used |

---

## Step 6 — Run Claude Code

Navigate to your project folder and launch Claude Code with your chosen model:
```bash
cd /path/to/your/project
claude --model qwen3-coder
```

Or with the flash model:
```bash
claude --model glm-4.7-flash
```

You should see the familiar Claude Code interface in your terminal. Start prompting!

---

## Step 7 — Optional: Disable Telemetry

By default, Claude Code sends some non-essential traffic (telemetry, update checks). To keep everything truly local:
```bash
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

Add to `~/.zshrc` to make it permanent.

---

## Verifying Everything is Working

**Check Ollama is running and serving the model:**
```bash
curl http://localhost:11434/api/tags
```
You should see a JSON list of your downloaded models.

**Check the context length is set correctly:**
```bash
ollama ps
```
This shows running models and their current context size.

**Test it's truly local** — disconnect from Wi-Fi and run a prompt in Claude Code. If you get a response, you're fully offline.

---

## Performance Tips for Apple Silicon

- Apple Silicon Macs (M1/M2/M3/M4) use unified memory, which is shared between CPU and GPU. More RAM = larger models run faster.
- **16GB RAM:** Stick to smaller models like `glm-4.7-flash` or `qwen3-coder:8b`
- **32GB RAM:** You can run `devstral` (24B) or `qwen3-coder:32b` comfortably
- **64GB+ RAM:** Run the largest available variants
- Expect responses to be slower than Anthropic's cloud — a few seconds to half a minute per response is normal
- Claude Code's agentic loop makes multiple model calls per task, so complex tasks may take a few minutes

---

## Switching Back to Anthropic's Cloud

If you want to use the real Anthropic models again, unset the environment variables:
```bash
unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN
export ANTHROPIC_API_KEY=your_real_key_here
```

Then run Claude Code normally — it will connect to Anthropic's cloud.

---

## Troubleshooting

**`connection refused` error**
Ollama isn't running. Start it:
```bash
OLLAMA_CONTEXT_LENGTH=65536 ollama serve
```

**`model not found` error**
Check the exact model name:
```bash
ollama list
```
Use the name exactly as shown, e.g., `qwen3-coder:latest` or just `qwen3-coder`.

**Claude Code is very slow**
Normal for local inference. Try a smaller/faster model like `glm-4.7-flash`. Make sure the model is running on GPU, not CPU — check with `ollama ps`.

**Tool calling not working / agentic loop breaks**
Make sure Ollama is on v0.14+. Tool calling support was added in this version. Update Ollama and retry.

**Context window errors**
Increase the context:
```bash
OLLAMA_CONTEXT_LENGTH=131072 ollama serve
```
(128k tokens — only do this if you have 32GB+ RAM)

**Model keeps stopping mid-response**
Usually a RAM issue. The model is being partially offloaded to CPU. Try a smaller model variant.

---

## Quick Reference — Full Setup Commands

```bash
# 1. Update Ollama
brew upgrade ollama

# 2. Pull model
ollama pull qwen3-coder

# 3. Start Ollama with large context
OLLAMA_CONTEXT_LENGTH=65536 ollama serve

# 4. (New terminal) Install Claude Code
npm install -g @anthropic-ai/claude-code

# 5. Set env variables
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""
export ANTHROPIC_BASE_URL=http://localhost:11434

# 6. Run Claude Code
cd your-project
claude --model qwen3-coder
```

---

*Last updated: February 2025 | Works with Ollama v0.14+ and Claude Code v2+*
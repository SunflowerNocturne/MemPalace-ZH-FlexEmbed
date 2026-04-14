# MemPalace-ZH-FlexEmbed

[English](#english) | [简体中文](./README.zh-CN.md)

## English

A MemPalace fork focused on three practical upgrades for local AI memory:

- flexible self-hosted embedding models
- transcript-aware long-chat mining
- stronger Chinese and mixed-language support

It also includes stdio MCP integration for local AI clients such as Chatbox,
Claude Code, Codex-style agents, and similar tools.
It can also run as a long-lived local MCP service over streamable HTTP, which
is often the more stable choice for desktop clients.

## Why this fork exists

Official MemPalace has already become much stronger in multilingual support.
This fork is not trying to replace upstream. Its goal is to push harder on the
parts that matter in real local memory workflows:

- swapping in stronger local embedding models
- handling exported chat transcripts more reliably
- improving retrieval on Chinese and mixed-language conversation data
- making MCP usage smoother in local stdio clients
- supporting service-style MCP deployment over streamable HTTP, not just stdio

## Key features

### 1. Flexible self-hosted embedding models

This is the biggest feature.

Instead of being stuck with one default embedding setup, you can point the
system at your own local model, including large self-hosted models such as
`Qwen3-Embedding-8B`.

Example:

```bash
export MEMPALACE_EMBED_MODEL=$HOME/.mempalace-zh/models/Qwen3-Embedding-8B
export MEMPALACE_EMBED_DEVICE=mps
export MEMPALACE_EMBED_BATCH_SIZE=2
```

Typical device values:

- `mps` for Apple Silicon
- `cuda` for NVIDIA GPUs
- `cpu` for fallback

### 2. Transcript-aware long-chat mining

This fork improves transcript normalization and chunking for long-form personal
conversation histories, especially markdown exports from chat tools.

That matters when memory is not just about storing short facts, but recovering:

- what was said on a specific day
- what happened right before an important event
- what gift, location, or coincidence tied an event together

### 3. Stronger Chinese and mixed-language support

This fork adds extra handling for Chinese and mixed Chinese-English material in:

- transcript normalization
- conversation mining
- general extraction
- query sanitization
- lightweight search reranking

### 4. MCP-ready local memory

The MCP workflow is not specific to one app.

If a host can launch a local stdio MCP server, this project can usually be
integrated into it.

Typical categories include:

- Chatbox
- Claude Code
- Codex-style local agent shells
- other desktop or terminal tools with stdio MCP support

This fork also fixes UTF-8 MCP output, so Chinese appears directly instead of
being escaped as `\uXXXX`.

### 5. stdio and service-style MCP transports

This fork supports both:

- `stdio` MCP, where the client launches the server process for you
- `streamable HTTP`, where you run one long-lived local MCP service and let
  multiple clients connect to it

That second mode is especially useful when a desktop client tends to leave
duplicate `stdio` Python processes behind after repeated reconnects.

## Recommended installation

For this project, the recommended pattern is editable install:

```bash
pip install -e ".[dev,local-embeddings]"
```

Why editable mode:

- it is best used as a local working tree
- MCP servers often point directly at the current repo environment
- local memory workflows often involve iterative tuning and retesting

Cloning the repo is not enough. The repository does not include:

- model weights
- optional local embedding runtime dependencies unless you install extras

The local embedding extra currently pulls in:

- `sentence-transformers>=2.7.0`
- `transformers>=4.51.0`
- `torch>=2.4`

## Quick start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/MemPalace-ZH-FlexEmbed.git
cd MemPalace-ZH-FlexEmbed
```

### 2. Create the environment

```bash
conda env create -f environment.yml
conda activate mempalace-zh-flexembed
```

### 3. Install

```bash
pip install -e ".[dev,local-embeddings]"
```

### 4. Install Hugging Face CLI helper

```bash
pip install "huggingface_hub[cli]>=0.23"
```

### 5. Prepare the model directory

```bash
mkdir -p ~/.mempalace-zh/models
```

### 6. Download `Qwen3-Embedding-8B`

Model page:

- [Qwen/Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B)

Example command:

```bash
hf download Qwen/Qwen3-Embedding-8B \
  --local-dir ~/.mempalace-zh/models/Qwen3-Embedding-8B
```

### 7. Export embedding environment variables

```bash
export MEMPALACE_EMBED_MODEL=$HOME/.mempalace-zh/models/Qwen3-Embedding-8B
export MEMPALACE_EMBED_DEVICE=mps
export MEMPALACE_EMBED_BATCH_SIZE=2
```

### 8. Create a palace

```bash
mkdir -p ~/.mempalace-zh/palace
```

### 9. Mine data

Project files:

```bash
mempalace init /path/to/project
mempalace mine /path/to/project --wing "MyProject"
```

Conversations:

```bash
mempalace mine /path/to/chatlogs --mode convos --wing "MyChats"
```

### 10. Search

```bash
mempalace --palace ~/.mempalace-zh/palace search "what you're looking for" --wing "MyChats"
```

## Generic MCP setup

Recommended for desktop clients:

- Use `Streamable HTTP` when your client supports it.
- Keep `stdio` as a fallback for older hosts.
- `Streamable HTTP` avoids the common problem where repeated reconnects can
  leave multiple heavy Python MCP processes running at once.

Core launch pattern:

```text
/absolute/path/to/conda/env/bin/python -m mempalace.mcp_server --palace /absolute/path/to/palace
```

Environment variables:

```text
MEMPALACE_EMBED_MODEL=/absolute/path/to/your/embedding-model
MEMPALACE_EMBED_DEVICE=mps
MEMPALACE_EMBED_BATCH_SIZE=2
```

Example stdio MCP command:

```text
/Users/your_name/miniconda3/envs/mempalace-zh-flexembed/bin/python -m mempalace.mcp_server --palace /Users/your_name/.mempalace-zh/palace
```

Recommended streamable HTTP launch:

```bash
/Users/your_name/miniconda3/envs/mempalace-zh-flexembed/bin/python -m mempalace.mcp_server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --mount-path /mcp \
  --palace /Users/your_name/.mempalace-zh/palace-fiction
```

Then configure your MCP client with:

```text
URL=http://127.0.0.1:8765/mcp
```

Field-by-field examples:

- Chatbox `远程 (http/sse)`:
  - `名称`: `mempalace-zh-fiction`
  - `URL`: `http://127.0.0.1:8765/mcp`
  - `HTTP Header`: leave blank
- Codex `Streamable HTTP`:
  - `Name`: `mempalace-zh-fiction`
  - `URL`: `http://127.0.0.1:8765/mcp`
  - `Bearer token env var`: leave blank
  - `Headers`: leave blank
  - `Headers from environment variables`: leave blank

If you want a second always-on palace, start it on another port:

```bash
/Users/your_name/miniconda3/envs/mempalace-zh-flexembed/bin/python -m mempalace.mcp_server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8766 \
  --mount-path /mcp \
  --palace /Users/your_name/.mempalace-zh/palace-personal
```

If you change:

- embedding model path
- batch size
- palace path
- MCP server command

restart the MCP server in your client.

## Repository layout

- `mempalace/`
- `tests/`
- `benchmarks/`
- `examples/`
- `hooks/`
- `docs/`

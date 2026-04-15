# MemPalace-ZH-FlexEmbed

[English](./README.md) | [简体中文](#简体中文)

## 简体中文

这是一个基于 MemPalace 的分支，重点强化三件事：

- **可自由切换的本地 embedding 模型**
- **面向长聊天记录的 transcript-aware 挖掘**
- **更强的中文 / 中英混杂支持**

同时，它也保留并强化了面向本地 AI 客户端的 `stdio MCP` 工作流，
适用于 Chatbox、Claude Code、Codex 风格 agent 以及其他支持本地 MCP 的工具。
此外，它也支持把 MCP 作为一个长期运行的本地 HTTP 服务启动，不局限于 `stdio`。

## 这个项目的定位

官方 MemPalace 已经在 `v3.2` 里增强了多语言能力。这个分支并不是为了
“替代官方”，而是把下面这些更贴近真实本地记忆场景的能力继续做强：

- 接入更强的本地 embedding 模型
- 更可靠地处理导出的聊天 transcript
- 提升中文与中英混杂长对话的检索效果
- 让本地 MCP 接入更稳、更容易复现
- 支持通过 streamable HTTP 作为常驻服务启动 MCP，而不只靠 stdio

## 最大亮点：可自选 embedding 模型

这是这个分支最重要的功能。

你不需要被固定在一个默认 embedding 路线上，可以直接把系统指向你自己
下载的本地模型，例如 `Qwen3-Embedding-8B`。

示例：

```bash
export MEMPALACE_EMBED_MODEL=$HOME/.mempalace-zh/models/Qwen3-Embedding-8B
export MEMPALACE_EMBED_DEVICE=mps
export MEMPALACE_EMBED_BATCH_SIZE=2
```

典型设备参数：

- `mps`：Apple Silicon
- `cuda`：NVIDIA GPU
- `cpu`：兜底

这意味着你可以：

- 使用比默认更强的 embedding
- 全程本地运行
- 根据语言和硬件自由调整
- 以后升级 embedding，而不必重写整个系统

## 第二亮点：适合长聊天记忆的 transcript-aware 挖掘

这个分支强化了聊天 transcript 的归一化和切分，尤其适合长时间积累的
个人聊天记录。

它真正擅长的是恢复这类细节：

- 某一天到底说了什么
- 某件大事发生前刚好发生了什么
- 某次关系转折前后的细节链条
- 某个礼物、地点、巧合是怎么串起来的

## 第三亮点：更强的中文 / 中英混杂支持

这个分支在这些模块里做了中文强化：

- transcript normalization
- conversation mining
- general extraction
- query sanitization
- 搜索阶段的轻量 rerank

所以它不只是“能处理中文”，而是更适合真实中文聊天语料。

## 第四亮点：通用的 stdio MCP 接入

这套 MCP 方法并不只属于 Chatbox。

只要一个 AI 客户端支持：

- 启动本地 `stdio MCP server`
- 传入启动命令
- 配置环境变量

那通常都可以接这个项目。

常见适用类别包括：

- Chatbox
- Claude Code
- Codex 风格本地 agent
- 其他支持 stdio MCP 的桌面端或终端端工具

另外，这个分支还修复了 MCP 中文输出显示为 `\uXXXX` 的问题，现在会直接输出 UTF-8 中文。

## 第五亮点：同时支持 stdio 与服务化 MCP

这个分支同时支持两种接法：

- `stdio`：由客户端帮你拉起 MCP server
- `streamable HTTP`：你自己启动一个长期运行的本地 MCP 服务，然后让多个客户端连它

第二种方式特别适合桌面端，因为有些客户端在频繁重连后会残留多份 `stdio`
Python 进程，而服务化 HTTP 模式能更稳定地避免这个问题。

## 推荐安装方式

推荐使用：

```bash
pip install -e ".[dev,local-embeddings]"
```

而不是普通的非 editable install。

原因：

- 这是一个更适合作为本地工作树使用的项目
- MCP 往往直接指向当前 repo 的 Python 环境
- 这类项目经常需要边改边测

注意：只 `git clone` 下来还不够。

仓库里不会包含：

- 模型权重
- 本地 embedding 依赖（除非你安装 extras）

当前 `local-embeddings` extra 会带上：

- `sentence-transformers>=2.7.0`
- `transformers>=4.51.0`
- `torch>=2.4`

## 一套能跑出强效果的推荐流程

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/MemPalace-ZH-FlexEmbed.git
cd MemPalace-ZH-FlexEmbed
```

### 2. 创建 Conda 环境

```bash
conda env create -f environment.yml
conda activate mempalace-zh-flexembed
```

### 3. 安装项目

```bash
pip install -e ".[dev,local-embeddings]"
```

### 4. 安装 Hugging Face CLI 辅助工具

```bash
pip install "huggingface_hub[cli]>=0.23"
```

### 5. 准备本地模型目录

```bash
mkdir -p ~/.mempalace-zh/models
```

### 6. 下载 `Qwen3-Embedding-8B`

模型地址：

- [Qwen/Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B)

示例命令：

```bash
hf download Qwen/Qwen3-Embedding-8B \
  --local-dir ~/.mempalace-zh/models/Qwen3-Embedding-8B
```

### 7. 设置 embedding 环境变量

```bash
export MEMPALACE_EMBED_MODEL=$HOME/.mempalace-zh/models/Qwen3-Embedding-8B
export MEMPALACE_EMBED_DEVICE=mps
export MEMPALACE_EMBED_BATCH_SIZE=2
```

### 8. 创建 palace 目录

```bash
mkdir -p ~/.mempalace-zh/palace
```

### 9. 导入数据

项目文件：

```bash
mempalace init /path/to/project
mempalace mine /path/to/project --wing "MyProject"
```

聊天记录：

```bash
mempalace mine /path/to/chatlogs --mode convos --wing "MyChats"
```

### 10. 测试搜索

```bash
mempalace --palace ~/.mempalace-zh/palace search "what you're looking for" --wing "MyChats"
```

## 通用 MCP 配置方式

桌面端客户端的推荐方式：

- 客户端支持的话，优先使用 `Streamable HTTP`
- `stdio` 作为兼容方案保留
- `Streamable HTTP` 可以避免重复重连后残留多份重型 Python MCP 进程的问题

核心命令模式：

```text
/absolute/path/to/conda/env/bin/python -m mempalace.mcp_server --palace /absolute/path/to/palace
```

环境变量：

```text
MEMPALACE_EMBED_MODEL=/absolute/path/to/your/embedding-model
MEMPALACE_EMBED_DEVICE=mps
MEMPALACE_EMBED_BATCH_SIZE=2
```

示例：

```text
/Users/your_name/miniconda3/envs/mempalace-zh-flexembed/bin/python -m mempalace.mcp_server --palace /Users/your_name/.mempalace-zh/palace
```

推荐的 Streamable HTTP 启动方式：

```bash
/Users/your_name/miniconda3/envs/mempalace-zh-flexembed/bin/python -m mempalace.mcp_server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --mount-path /mcp \
  --palace /Users/your_name/.mempalace-zh/palace-fiction
```

然后在 MCP 客户端里填写：

```text
URL=http://127.0.0.1:8765/mcp
```

逐项填写示例：

- Chatbox `远程 (http/sse)`：
  - `名称`：`mempalace-zh-fiction`
  - `URL`：`http://127.0.0.1:8765/mcp`
  - `HTTP Header`：留空
- Codex `Streamable HTTP`：
  - `Name`：`mempalace-zh-fiction`
  - `URL`：`http://127.0.0.1:8765/mcp`
  - `Bearer token env var`：留空
  - `Headers`：留空
  - `Headers from environment variables`：留空

MCP 下的短 query 自动恢复：

- 新版本会自动补救像 `Lux 起名`、`巴西牛排` 这种很短的记忆检索词，不再那么容易出现“库里明明有，但返回空列表”。
- 如果调用方没有强行设置很严格的阈值，服务端会对短 query 使用更宽松的默认距离、自动尝试扩写变体，并在语义召回过弱时回退到 lexical matching。
- 实际使用时，MCP 客户端对这类短标签 / 事件名查询，通常应该省略 `max_distance`，而不是强行传入 `0.5` 这种严格值。

如果你还想常驻第二套 palace，可以换另一个端口启动：

```bash
/Users/your_name/miniconda3/envs/mempalace-zh-flexembed/bin/python -m mempalace.mcp_server \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8766 \
  --mount-path /mcp \
  --palace /Users/your_name/.mempalace-zh/palace-personal
```

如果你修改了：

- embedding 模型路径
- batch size
- palace 路径
- MCP 启动命令

记得在客户端里重启 MCP server。

## 仓库结构

- `mempalace/`
- `tests/`
- `benchmarks/`
- `examples/`
- `hooks/`
- `docs/`

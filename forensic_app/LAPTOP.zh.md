# 取证引擎 — 笔记本版

整套产品**在你自己的笔记本上本地运行**,用一个小的本地模型。**数据不出这台机器** —— 装好之后不需要服务器、不需要联网。

🇬🇧 English: [LAPTOP.md](LAPTOP.md).

## 一次性准备
1. 安装 **Ollama**:https://ollama.com (Mac / Windows / Linux 都有原生版)
2. 安装 Python 3.9+ 及依赖:`pip install -r requirements-laptop.txt`

## 运行

**macOS / Linux**
```bash
./laptop.sh
```

**Windows** —— 双击 `laptop.bat`,或在 PowerShell / CMD 里:
```bat
laptop.bat
```

启动器会自动探测你的机器、选一个合适的模型、首次运行时下载(约 2–4.5 GB,之后缓存),
启动应用并自动打开浏览器 http://127.0.0.1:8800/。

- **普通笔记本(纯 CPU,8–16 GB):** 默认用 3B 模型 —— 跑得快,能给出表层问题
  **和全部确定性算术红旗**,但最深的结构性发现会弱一些。
- **Apple Silicon(16 GB+)或带 GPU 的笔记本:** 默认用 7B 模型 —— 完整分析
  (结构性"钳形"矛盾 + 单位经济学),同样全程本地。
- 强制指定模型:`FORCE_MODELS="llama3.2:3b" ./laptop.sh`(Windows:先 `set FORCE_MODELS=llama3.2:3b` 再 `laptop.bat`)

## 手动启动(任意系统,不用启动器)
```bash
ollama pull llama3.2:3b
# macOS / Linux:
MODELS="llama3.2:3b,qwen2.5-coder:7b" python3 -m uvicorn server:app --host 127.0.0.1 --port 8800
```
```powershell
# Windows PowerShell:
$env:MODELS="llama3.2:3b,qwen2.5-coder:7b"; python -m uvicorn server:app --host 127.0.0.1 --port 8800
```

## 更新
app **不会自动更新**(它是本地副本)。要拿最新版:
- **macOS / Linux:** `./update.sh`  ·  **Windows:** `update.bat`
它会拉取最新代码,**保留你的历史(`runs/`)和上传**,已缓存的 Ollama 模型不动(所以很快)。
更新后用 `laptop.sh` / `laptop.bat` 重启即可。app 启动时也会检查,有新版会显示横幅
(该检查需要联网;离线时静默,不影响使用)。

## 说明
- **PDF 导出(weasyprint)** 是可选的,在 Windows 上不好装(需要 GTK 系统库)。
  不装即可 —— 其它功能全部正常,导出会自动降级成"可打印 HTML"。
- 所有推理都走你本地的 Ollama;引擎从不联网(除上面的可选更新检查外)。

<div align="center">

# 🎹 LiveAgent Remote

**Programmable control surface for Ableton Live**

Control tracks, clips, MIDI notes, devices, and automation from any external script or AI agent via a simple JSON socket protocol.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-green.svg)
![Ableton Live](https://img.shields.io/badge/Ableton%20Live-11%20%7C%2012-orange.svg)
![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)

[English](#english) | [日本語](#日本語) | [中文](#中文) | [한국어](#한국어) | [Español](#español) | [Français](#français)

</div>

---

## English

### What is this?

LiveAgent is a MIDI Remote Script that runs **inside** Ableton Live and opens a TCP socket (`127.0.0.1:8765`). Any external program can send JSON commands to control Ableton programmatically — no additional software, plugins, or DAW modifications needed.

### Features

- 🎵 Create MIDI tracks, clips, and write notes programmatically
- 🎛️ Load plugins/devices, read and set parameters
- 🤖 Perfect for AI agent integration (ChatGPT, Claude, custom bots)
- 📊 Read clip automation and write envelope points
- 🔌 Works with any language that supports TCP sockets
- ⚡ Sub-millisecond latency, no MIDI routing needed

### Installation

1. Copy the `LiveAgent` folder into your Ableton MIDI Remote Scripts directory:

**macOS:**
```
/Applications/Ableton Live [version]/Contents/App-Resources/MIDI Remote Scripts/
```

**Windows:**
```
C:\ProgramData\Ableton\Live [version]\Resources\MIDI Remote Scripts\
```

2. Restart Ableton Live
3. Go to **Preferences → Link/Tempo/MIDI**
4. In the **Control Surface** dropdown, select **LiveAgent**
5. Done! The agent is now listening on `127.0.0.1:8765`

### Quick Start (Python)

```bash
pip install live-agent-remote
```

```python
from live_agent_client import LiveAgentClient

client = LiveAgentClient()

# Check connection
print(client.ping())

# List all tracks
tracks = client.list_tracks()

# Create a clip with notes
client.create_session_clip(track_index=1, slot_index=0, length_beats=16)
client.write_midi_notes(track_index=1, slot_index=0, notes=[
    {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 96},
    {"pitch": 64, "start": 1.0, "duration": 1.0, "velocity": 96},
])

# Load a plugin
client.load_device(track_index=1, device_name="Massive")

# Set a parameter
client.set_parameter_value(track_index=1, device_name="Massive", parameter_name="MASTER-VOLUME", value=0.7)

client.close()
```

### Quick Start (Node.js)

```javascript
const { LiveAgentClient } = require('./client/live_agent_client');

const client = new LiveAgentClient();

async function main() {
  const state = await client.ping();
  console.log('Connected:', state);

  const tracks = await client.listTracks();
  console.log('Tracks:', tracks);

  await client.loadDevice(1, 'Massive');
}

main();
```

### Quick Start (curl / any TCP client)

Send a JSON line followed by newline to `127.0.0.1:8765`:

```bash
echo '{"command":"ping"}' | nc 127.0.0.1 8765
```

### Command Reference

| Command | Description | Key Parameters |
|---|---|---|
| `ping` | Check connection | — |
| `get_live_state` | Get tempo, tracks, scenes, playing state | — |
| `list_tracks` | List all tracks with devices and clips | — |
| `create_midi_track` | Create a new MIDI track | `index` |
| `create_session_clip` | Create a clip in session view | `track_index`, `slot_index`, `length_beats`, `name` |
| `write_midi_notes` | Write MIDI notes to a clip | `track_index`, `slot_index`, `notes[]` |
| `read_clip_notes` | Read notes from a clip | `track_index`, `slot_index` |
| `clear_clip_notes` | Delete all notes in a clip | `track_index`, `slot_index` |
| `list_devices` | List devices on a track | `track_index` |
| `set_parameter_value` | Set a device parameter | `track_index`, `device_index/name`, `parameter_index/name`, `value` |
| `write_clip_automation` | Write automation envelope | `track_index`, `slot_index`, `device_*`, `parameter_*`, `points[]` |
| `load_device` | Load a plugin onto a track | `track_index`, `device_name`, `browser_type` |
| `list_browser_devices` | Search/list available plugins | `browser_type`, `query`, `max_results` |

### Note Format

```json
{
  "pitch": 60,
  "start": 0.0,
  "duration": 1.0,
  "velocity": 96,
  "muted": false
}
```

### Architecture

```
External Script / AI Agent
        │
        ▼
   TCP Socket (127.0.0.1:8765)
        │
        ▼
   LiveAgent.py (Ableton Control Surface)
        │
        ▼
   Ableton Live API (LOM)
```

### MCP Server (Claude Desktop / Cursor / etc.)

LiveAgent includes a built-in **MCP (Model Context Protocol) server** that lets AI agents control Ableton directly.

**Setup:**

1. Install dependencies:
```bash
cd live-agent-remote
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]"
```

2. Add to your MCP client config:

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ableton-live": {
      "command": "/absolute/path/to/live-agent-remote/.venv/bin/python3",
      "args": ["/absolute/path/to/live-agent-remote/mcp_server.py"]
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "ableton-live": {
      "command": "/absolute/path/to/live-agent-remote/.venv/bin/python3",
      "args": ["/absolute/path/to/live-agent-remote/mcp_server.py"]
    }
  }
}
```

3. Restart your MCP client. All 13 commands are now available as tools!

---

## 日本語

### これは何？

LiveAgentはAbleton Liveの**内部**で動作するMIDI Remote Scriptです。TCPソケット（`127.0.0.1:8765`）を開き、外部プログラムからJSONコマンドでAbletonを操作できるようにします。追加ソフトウェアやプラグイン不要です。

### 特徴

- 🎵 トラック作成、クリップ作成、MIDIノート書き込みをプログラムで実行
- 🎛️ プラグイン/デバイスのロード、パラメータ読み取り・設定
- 🤖 AIエージェント（ChatGPT、Claude等）との統合に最適
- 📊 オートメーションの読み取り・書き込み
- 🔌 TCPソケット対応の任意の言語から使用可能
- ⚡ ミリ秒未満のレイテンシ

### インストール手順

1. `LiveAgent`フォルダをAbletonのMIDI Remote Scriptsディレクトリにコピー：

**macOS:**
```
/Applications/Ableton Live [バージョン]/Contents/App-Resources/MIDI Remote Scripts/
```

**Windows:**
```
C:\ProgramData\Ableton\Live [バージョン]\Resources\MIDI Remote Scripts\
```

2. Ableton Liveを再起動
3. **Preferences → Link/Tempo/MIDI** を開く
4. **Control Surface** のドロップダウンから **LiveAgent** を選択
5. 完了！`127.0.0.1:8765`で待受開始

### クイックスタート（Python）

```python
from live_agent_client import LiveAgentClient

client = LiveAgentClient()

# 接続確認
print(client.ping())

# トラック一覧取得
tracks = client.list_tracks()

# クリップ作成＋ノート書き込み
client.create_session_clip(track_index=1, slot_index=0, length_beats=16)
client.write_midi_notes(track_index=1, slot_index=0, notes=[
    {"pitch": 60, "start": 0.0, "duration": 1.0, "velocity": 96},
    {"pitch": 64, "start": 1.0, "duration": 1.0, "velocity": 96},
])

# プラグイン読み込み
client.load_device(track_index=1, device_name="Massive")

client.close()
```

### コマンド一覧

| コマンド | 説明 |
|---|---|
| `ping` | 接続確認 |
| `get_live_state` | テンポ・トラック・シーン・再生状態を取得 |
| `list_tracks` | 全トラック情報を取得 |
| `create_midi_track` | MIDIトラック作成 |
| `create_session_clip` | セッションビューにクリップ作成 |
| `write_midi_notes` | クリップにMIDIノート書き込み |
| `read_clip_notes` | クリップのノート読み取り |
| `clear_clip_notes` | クリップのノート全削除 |
| `list_devices` | トラックのデバイス一覧 |
| `set_parameter_value` | デバイスパラメータ設定 |
| `write_clip_automation` | オートメーション書き込み |
| `load_device` | プラグインをトラックにロード |
| `list_browser_devices` | プラグイン一覧検索 |

---

## 中文

### 这是什么？

LiveAgent 是一个运行在 Ableton Live **内部** 的 MIDI Remote Script。它通过 TCP 套接字（`127.0.0.1:8765`）接收 JSON 命令，让你可以用任何外部程序控制 Ableton。无需额外软件或插件。

### 安装步骤

1. 将 `LiveAgent` 文件夹复制到 Ableton 的 MIDI Remote Scripts 目录：

**macOS:**
```
/Applications/Ableton Live [版本]/Contents/App-Resources/MIDI Remote Scripts/
```

**Windows:**
```
C:\ProgramData\Ableton\Live [版本]\Resources\MIDI Remote Scripts\
```

2. 重启 Ableton Live
3. 打开 **Preferences → Link/Tempo/MIDI**
4. 在 **Control Surface** 下拉菜单中选择 **LiveAgent**
5. 完成！现在可以通过 `127.0.0.1:8765` 发送命令

### 快速开始（Python）

```python
from live_agent_client import LiveAgentClient

client = LiveAgentClient()
print(client.ping())                    # 检查连接
tracks = client.list_tracks()           # 列出所有轨道
client.load_device(track_index=1, device_name="Massive")  # 加载插件
client.close()
```

### 命令列表

| 命令 | 说明 |
|---|---|
| `ping` | 连接检查 |
| `get_live_state` | 获取速度、轨道、场景、播放状态 |
| `list_tracks` | 列出所有轨道 |
| `create_midi_track` | 创建MIDI轨道 |
| `create_session_clip` | 创建Session剪辑 |
| `write_midi_notes` | 写入MIDI音符 |
| `read_clip_notes` | 读取音符 |
| `clear_clip_notes` | 清除所有音符 |
| `list_devices` | 列出设备 |
| `set_parameter_value` | 设置参数值 |
| `write_clip_automation` | 写入自动化 |
| `load_device` | 加载插件到轨道 |
| `list_browser_devices` | 搜索/列出可用插件 |

---

## 한국어

### 이것은 무엇인가요?

LiveAgent는 Ableton Live **내부**에서 실행되는 MIDI Remote Script입니다. TCP 소켓(`127.0.0.1:8765`)을 열어 외부 프로그램에서 JSON 명령으로 Ableton을 제어할 수 있습니다.

### 설치 방법

1. `LiveAgent` 폴더를 MIDI Remote Scripts 디렉토리에 복사:

**macOS:**
```
/Applications/Ableton Live [버전]/Contents/App-Resources/MIDI Remote Scripts/
```

**Windows:**
```
C:\ProgramData\Ableton\Live [버전]\Resources\MIDI Remote Scripts\
```

2. Ableton Live 재시작
3. **Preferences → Link/Tempo/MIDI** 열기
4. **Control Surface** 드롭다운에서 **LiveAgent** 선택
5. 완료!

### 빠른 시작 (Python)

```python
from live_agent_client import LiveAgentClient

client = LiveAgentClient()
print(client.ping())                    # 연결 확인
tracks = client.list_tracks()           # 트랙 목록
client.load_device(track_index=1, device_name="Massive")  # 플러그인 로드
client.close()
```

---

## Español

### ¿Qué es esto?

LiveAgent es un MIDI Remote Script que se ejecuta **dentro** de Ableton Live. Abre un socket TCP (`127.0.0.1:8765`) para recibir comandos JSON desde cualquier programa externo.

### Instalación

1. Copia la carpeta `LiveAgent` al directorio de MIDI Remote Scripts:

**macOS:** `/Applications/Ableton Live [versión]/Contents/App-Resources/MIDI Remote Scripts/`
**Windows:** `C:\ProgramData\Ableton\Live [versión]\Resources\MIDI Remote Scripts\`

2. Reinicia Ableton Live
3. **Preferences → Link/Tempo/MIDI**
4. Selecciona **LiveAgent** en **Control Surface**
5. ¡Listo!

### Inicio rápido (Python)

```python
from live_agent_client import LiveAgentClient

client = LiveAgentClient()
print(client.ping())
tracks = client.list_tracks()
client.load_device(track_index=1, device_name="Massive")
client.close()
```

---

## Français

### Qu'est-ce que c'est ?

LiveAgent est un MIDI Remote Script qui s'exécute **à l'intérieur** d'Ableton Live. Il ouvre un socket TCP (`127.0.0.1:8765`) pour recevoir des commandes JSON depuis n'importe quel programme externe.

### Installation

1. Copiez le dossier `LiveAgent` dans le répertoire MIDI Remote Scripts :

**macOS :** `/Applications/Ableton Live [version]/Contents/App-Resources/MIDI Remote Scripts/`
**Windows :** `C:\ProgramData\Ableton\Live [version]\Resources\MIDI Remote Scripts\`

2. Redémarrez Ableton Live
3. **Preferences → Link/Tempo/MIDI**
4. Sélectionnez **LiveAgent** dans **Control Surface**
5. C'est prêt !

### Démarrage rapide (Python)

```python
from live_agent_client import LiveAgentClient

client = LiveAgentClient()
print(client.ping())
tracks = client.list_tracks()
client.load_device(track_index=1, device_name="Massive")
client.close()
```

---

## License

MIT License — use freely, modify freely, share freely.

<div align="center">

Made with 💙 by Yuuka & Shota

</div>

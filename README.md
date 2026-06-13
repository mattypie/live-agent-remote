<div align="center">

# 🎹 LiveAgent Remote

**Programmable control surface for Ableton Live**

Control tracks, clips, MIDI notes, devices, and automation from any external script or AI agent via a simple JSON socket protocol.

<p>
  <a href="https://happytown-s.github.io/live-agent-remote/"><b>🌐 Landing Page</b></a> · <a href="https://happytown-s.github.io/sample-librarian/"><b>🔍 sample-librarian</b></a>
</p>

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
- 🥁 Create Drum Racks and load samples onto pads
- 🔊 Import audio clips, auto-warp with BPM/key detection
- 🎯 Pitch detection & Camelot Wheel harmonic matching
- 🤖 Perfect for AI agent integration (ChatGPT, Claude, custom bots)
- 📊 Read clip automation and write envelope points
- 🔌 Works with any language that supports TCP sockets
- ⚡ Sub-millisecond latency, no MIDI routing needed

### Installation

**Quick Setup:**
```bash
git clone https://github.com/happytown-s/live-agent-remote.git
cd live-agent-remote
./setup.sh
```

**Manual Setup:**
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
| `create_audio_track` | Create a new audio track | `index` |
| `import_audio_clip` | Import audio file to track slot | `track_index`, `slot_index`, `file_path` |
| `get_clip_info` | Get clip details (name, type, loop, warp) | `track_index`, `slot_index` |
| `set_clip_properties` | Set clip name, color, loop, pitch, gain | `track_index`, `slot_index`, `name`, `color`, etc. |
| `duplicate_clip` | Copy clip to another slot | `track_index`, `slot_index`, `dest_*` |
| `delete_clip` | Remove clip from slot | `track_index`, `slot_index` |
| `set_clip_warp` | Set warp on/off and warp mode | `track_index`, `slot_index`, `warping`, `warp_mode` |
| `analyze_and_warp` | Auto-warp with BPM/key from analyzer | `track_index`, `slot_index`, `bpm`, `key`, `warp_mode` |
| `analyze_audio_file` | Analyze audio file for BPM, key, beats | `file_path` |
| `detect_pitch` | Detect pitch of one-shot sample | `file_path` |
| `analyze_folder` | Batch analyze folder, sort by pitch | `folder_path`, `mode` |
| `find_compatible_samples` | Find samples matching target key (Camelot) | `folder_path`, `target_key`, `mode` |
| `create_smart_folder` | Smart folder of compatible samples in Ableton browser | `target_key`, `categories`, `base_path` |
| `create_drum_rack` | Create Drum Rack on a MIDI track | `track_index`, `name` |
| `load_sample_to_pad` | Load sample onto Drum Rack pad | `track_index`, `pad_index`, `file_path`, `drum_rack_index` |
| `inspect_drum_rack` | Inspect Drum Rack pad structure (debug) | `track_index`, `drum_rack_index`, `pad_range` |
| `eval` | Evaluate Python expression in Live context | `expr` |
| `exec` | Execute Python statement in Live context | `stmt` |

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

### Audio Analyzer

Built-in audio analysis powered by [librosa](https://librosa.org/):

- **BPM Detection** — `librosa.beat.beat_track` for tempo extraction
- **Key Detection** — Krumhansl-Schmuckler algorithm for all 24 keys
- **Pitch Detection** — `pyin` monophonic pitch detection for one-shot samples (kicks, snares, etc.)
- **Sample Type Classification** — Auto-classify by duration: One-Shot (<2s), Short Loop (2-5s), Medium Loop (5-15s), Long Loop (>15s)
- **Camelot Wheel** — Harmonic compatibility matching for DJ-style key mixing
- **Batch Analysis** — Analyze entire folders, sort by pitch or key, filter by sample type
- **Smart Folders** — Auto-generate symlinks of compatible samples visible in Ableton's browser
- **Auto-Warp** — Detect BPM/key and auto-apply warp settings in Ableton

**CLI usage:**
```bash
# Analyze a single file
python audio_analyzer.py kick.wav

# Detect pitch of a one-shot
python audio_analyzer.py snare.wav --pitch-only

# Analyze all files in a folder (sorted by pitch)
python audio_analyzer.py ./Kicks/ --folder --mode pitch

# Find samples compatible with Fm (Camelot Wheel)
python audio_analyzer.py ./Kicks/ --compatible Fm
```

**Python API:**
```python
from audio_analyzer import AudioAnalyzer

# Single file
result = AudioAnalyzer.analyze("loop.wav")
# {"bpm": 128.5, "key": "Fm", "beat_count": 32, ...}

# One-shot pitch (includes duration + sample type)
pitch = AudioAnalyzer.detect_pitch("kick.wav")
# {"pitch": "C1", "frequency": 32.7, "is_atonal": False, "duration_seconds": 0.45, "sample_type": "oneshot", "sample_type_label": "One-Shot"}

# Filter folder by sample type (only one-shots)
results = AudioAnalyzer.analyze_folder("./Kicks", mode="pitch")
oneshots = [r for r in results if r.get("sample_type") == "oneshot"]

# Find compatible samples
matches = AudioAnalyzer.find_compatible_samples("./Kicks", "Fm")
# {"compatible_count": 142, "compatible": [...]}
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

3. Restart your MCP client. All 31 commands are now available as tools!

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
| `create_audio_track` | オーディオトラック作成 |
| `import_audio_clip` | オーディオファイルをトラックにインポート |
| `get_clip_info` | クリップ詳細取得（名前、タイプ、ループ、ワープ） |
| `set_clip_properties` | クリップ名・色・ループ・ピッチ・ゲイン設定 |
| `duplicate_clip` | クリップを別スロットに複製 |
| `delete_clip` | クリップ削除 |
| `set_clip_warp` | ワープON/OFF・ワープモード設定 |
| `analyze_and_warp` | BPM/キー検出結果で自動ワープ設定 |
| `analyze_audio_file` | オーディオファイルのBPM・キー・ビート解析 |
| `detect_pitch` | ワンショットサンプルのピッチ検出 |
| `analyze_folder` | フォルダ一括解析（ピッチ順ソート） |
| `find_compatible_samples` | Camelot Wheelでキー互換サンプル検索 |
| `create_smart_folder` | Abletonブラウザに互換サンプルのスマートフォルダ作成 |
| `create_drum_rack` | MIDIトラックにDrum Rack作成 |
| `load_sample_to_pad` | Drum Rackパッドにサンプルをロード |
| `inspect_drum_rack` | Drum Rackパッド構造の検査（デバッグ用） |
| `eval` | LiveコンテキストでPython式を評価 |
| `exec` | LiveコンテキストでPython文を実行 |

### オーディオ解析

[librosa](https://librosa.org/)による内蔵オーディオ解析：

- **BPM検出** — `librosa.beat.beat_track`でテンポ抽出
- **キー検出** — Krumhansl-Schmucklerアルゴリズムで全24調を判定
- **ピッチ検出** — `pyin`でワンショット（キック・スネア等）の基本音高を検出
- **サンプル分類** — 長さで自動分類: One-Shot（2秒未満）, Short Loop（2〜5秒）, Medium Loop（5〜15秒）, Long Loop（15秒超）
- **Camelot Wheel** — DJスタイルのキーマッチング
- **一括解析** — フォルダ全体を解析、ピッチ順でソート、サンプルタイプでフィルタ可能
- **スマートフォルダ** — 互換サンプルのシンボリックリンクを自動生成、Abletonブラウザから直接閲覧可能
- **自動ワープ** — BPM/キー検出→Abletonにワープ自動適用

**CLI使用例:**
```bash
python audio_analyzer.py kick.wav                  # 単一ファイル解析
python audio_analyzer.py snare.wav --pitch-only    # ピッチ検出のみ
python audio_analyzer.py ./Kicks/ --folder --mode pitch  # フォルダ一括（ピッチ順）
python audio_analyzer.py ./Kicks/ --compatible Fm  # Fmと互換するサンプル検索
```

### MCPサーバー（Claude Desktop / Cursor等）

LiveAgentは**MCPサーバー**を内蔵しており、AIエージェントからAbletonを直接操作できます。

**セットアップ:**

1. 依存パッケージをインストール：
```bash
cd live-agent-remote
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" librosa
```

2. MCPクライアントの設定ファイルに追加：

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

3. MCPクライアントを再起動。全31コマンドがツールとして利用可能！

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
| `create_audio_track` | 创建音频轨道 |
| `import_audio_clip` | 导入音频文件到轨道 |
| `get_clip_info` | 获取剪辑详情（名称、类型、循环、Warp） |
| `set_clip_properties` | 设置剪辑名称、颜色、循环、音高、增益 |
| `duplicate_clip` | 复制剪辑到其他位置 |
| `delete_clip` | 删除剪辑 |
| `set_clip_warp` | 设置Warp开关和模式 |
| `analyze_and_warp` | 使用BPM/调性检测结果自动设置Warp |
| `analyze_audio_file` | 分析音频文件的BPM、调性、节拍 |
| `detect_pitch` | 检测单次采样（Kick/Snare等）的音高 |
| `analyze_folder` | 批量分析文件夹，按音高排序 |
| `find_compatible_samples` | 使用Camelot Wheel搜索调性兼容的采样 |
| `create_smart_folder` | 在Ableton浏览器中创建兼容采样的智能文件夹 |
| `create_drum_rack` | 在MIDI轨道上创建Drum Rack |
| `load_sample_to_pad` | 将采样加载到Drum Rack打击垫 |
| `inspect_drum_rack` | 检查Drum Rack打击垫结构（调试用） |
| `eval` | 在Live上下文中评估Python表达式 |
| `exec` | 在Live上下文中执行Python语句 |

### 音频分析

基于 [librosa](https://librosa.org/) 的内置音频分析：

- **BPM检测** — `librosa.beat.beat_track` 节拍提取
- **调性检测** — Krumhansl-Schmuckler算法，支持全部24个调
- **音高检测** — `pyin` 单音检测，适用于Kick/Snare等单次采样
- **采样分类** — 按时长自动分类: One-Shot（<2秒）、Short Loop（2-5秒）、Medium Loop（5-15秒）、Long Loop（>15秒）
- **Camelot Wheel** — DJ风格的调性兼容匹配
- **批量分析** — 分析整个文件夹，按音高排序，可按采样类型筛选
- **智能文件夹** — 自动生成兼容采样的符号链接，可在Ableton浏览器中直接查看
- **自动Warp** — 检测BPM/调性后自动应用Warp设置

**CLI使用：**
```bash
python audio_analyzer.py kick.wav                  # 分析单个文件
python audio_analyzer.py snare.wav --pitch-only    # 仅检测音高
python audio_analyzer.py ./Kicks/ --folder --mode pitch  # 批量分析（按音高排序）
python audio_analyzer.py ./Kicks/ --compatible Fm  # 搜索与Fm兼容的采样
```

### MCP服务器（Claude Desktop / Cursor等）

LiveAgent内置 **MCP服务器**，支持AI代理直接控制Ableton。

**安装：**

1. 安装依赖：
```bash
cd live-agent-remote
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" librosa
```

2. 添加到MCP客户端配置：

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ableton-live": {
      "command": "/path/to/live-agent-remote/.venv/bin/python3",
      "args": ["/path/to/live-agent-remote/mcp_server.py"]
    }
  }
}
```

3. 重启MCP客户端，全部31个命令即可作为工具使用！

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

### 명령 목록

| 명령 | 설명 |
|---|---|
| `ping` | 연결 확인 |
| `get_live_state` | 템포, 트랙, 씬, 재생 상태 가져오기 |
| `list_tracks` | 모든 트랙 나열 |
| `create_midi_track` | MIDI 트랙 생성 |
| `create_session_clip` | 세션 클립 생성 |
| `write_midi_notes` | MIDI 노트 쓰기 |
| `read_clip_notes` | 노트 읽기 |
| `clear_clip_notes` | 노트 전체 삭제 |
| `list_devices` | 디바이스 나열 |
| `set_parameter_value` | 파라미터 값 설정 |
| `write_clip_automation` | 오토메이션 쓰기 |
| `load_device` | 플러그인 로드 |
| `list_browser_devices` | 사용 가능한 플러그인 검색 |
| `create_audio_track` | 오디오 트랙 생성 |
| `import_audio_clip` | 오디오 파일을 트랙에 임포트 |
| `get_clip_info` | 클립 상세 정보 (이름, 유형, 루프, 워프) |
| `set_clip_properties` | 클립 이름, 색상, 루프, 피치, 게인 설정 |
| `duplicate_clip` | 클립을 다른 슬롯에 복제 |
| `delete_clip` | 클립 삭제 |
| `set_clip_warp` | 워프 ON/OFF 및 모드 설정 |
| `analyze_and_warp` | BPM/키 분석 결과로 자동 워프 설정 |
| `analyze_audio_file` | 오디오 파일의 BPM, 키, 비트 분석 |
| `detect_pitch` | 원샷 샘플의 피치 감지 |
| `analyze_folder` | 폴더 일괄 분석 (피치순 정렬) |
| `find_compatible_samples` | Camelot Wheel로 키 호환 샘플 검색 |
| `create_smart_folder` | Ableton 브라우저에 호환 샘플 스마트 폴더 생성 |
| `create_drum_rack` | MIDI 트랙에 Drum Rack 생성 |
| `load_sample_to_pad` | Drum Rack 패드에 샘플 로드 |
| `inspect_drum_rack` | Drum Rack 패드 구조 검사 (디버그용) |
| `eval` | Live 컨텍스트에서 Python 표현식 평가 |
| `exec` | Live 컨텍스트에서 Python 문 실행 |

### 오디오 분석

[librosa](https://librosa.org/) 기반 내장 오디오 분석:

- **BPM 감지** — `librosa.beat.beat_track` 템포 추출
- **키 감지** — Krumhansl-Schmuckler 알고리즘으로 24개 키 판정
- **피치 감지** — `pyin`으로 원샷 (킥, 스네어 등)의 기본 음높이 감지
- **샘플 분류** — 길이별 자동 분류: One-Shot (<2초), Short Loop (2-5초), Medium Loop (5-15초), Long Loop (>15초)
- **Camelot Wheel** — DJ 스타일 키 매칭
- **일괄 분석** — 폴더 전체 분석, 피치순 정렬, 샘플 타입 필터 가능
- **스마트 폴더** — 호환 샘플의 심볼릭 링크 자동 생성, Ableton 브라우저에서 직접 탐색 가능
- **자동 워프** — BPM/키 감지 후 Ableton에 워프 자동 적용

### MCP 서버 (Claude Desktop / Cursor 등)

LiveAgent에 **MCP 서버**가 내장되어 있어 AI 에이전트에서 Ableton을 직접 제어할 수 있습니다.

**설정:**

```bash
cd live-agent-remote
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" librosa
```

**Claude Desktop** 설정에 추가 후 재시작하면 31개 명령을 도구로 사용할 수 있습니다!

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

### Comandos

| Comando | Descripción |
|---|---|
| `ping` | Verificar conexión |
| `get_live_state` | Obtener tempo, pistas, escenas, estado de reproducción |
| `list_tracks` | Listar todas las pistas |
| `create_midi_track` | Crear pista MIDI |
| `create_session_clip` | Crear clip en vista de sesión |
| `write_midi_notes` | Escribir notas MIDI |
| `read_clip_notes` | Leer notas del clip |
| `clear_clip_notes` | Eliminar todas las notas |
| `list_devices` | Listar dispositivos |
| `set_parameter_value` | Establecer valor de parámetro |
| `write_clip_automation` | Escribir automatización |
| `load_device` | Cargar plugin en pista |
| `list_browser_devices` | Buscar/listar plugins disponibles |
| `create_audio_track` | Crear pista de audio |
| `import_audio_clip` | Importar archivo de audio a pista |
| `get_clip_info` | Detalles del clip (nombre, tipo, loop, warp) |
| `set_clip_properties` | Nombre, color, loop, pitch, ganancia del clip |
| `duplicate_clip` | Duplicar clip en otro slot |
| `delete_clip` | Eliminar clip |
| `set_clip_warp` | Activar/desactivar Warp y modo |
| `analyze_and_warp` | Auto-warp con BPM/tonalidad detectados |
| `analyze_audio_file` | Analizar BPM, tonalidad, beats de archivo |
| `detect_pitch` | Detectar pitch de muestra one-shot |
| `analyze_folder` | Análisis por lotes, ordenar por pitch |
| `find_compatible_samples` | Buscar muestras compatibles (Camelot Wheel) |
| `create_smart_folder` | Carpeta inteligente de muestras compatibles en el navegador de Ableton |
| `create_drum_rack` | Crear Drum Rack en pista MIDI |
| `load_sample_to_pad` | Cargar sample en pad de Drum Rack |
| `inspect_drum_rack` | Inspeccionar estructura de pads del Drum Rack (depuración) |
| `eval` | Evaluar expresión Python en contexto de Live |
| `exec` | Ejecutar sentencia Python en contexto de Live |

### Analizador de Audio

Análisis de audio integrado con [librosa](https://librosa.org/):

- **Detección de BPM** — Extracción de tempo
- **Detección de tonalidad** — Algoritmo Krumhansl-Schmuckler, 24 tonalidades
- **Detección de pitch** — Para muestras one-shot (kicks, snares)
- **Clasificación de muestras** — Clasificación automática por duración: One-Shot (<2s), Short Loop (2-5s), Medium Loop (5-15s), Long Loop (>15s)
- **Camelot Wheel** — Coincidencia armónica estilo DJ
- **Análisis por lotes** — Analizar carpetas enteras, ordenar por pitch, filtrar por tipo de muestra
- **Carpetas inteligentes** — Generación automática de symlinks de muestras compatibles, visibles en el navegador de Ableton
- **Auto-Warp** — Detectar BPM/tonalidad y aplicar Warp automáticamente

### Servidor MCP (Claude Desktop / Cursor etc.)

LiveAgent incluye un **servidor MCP** que permite a agentes de IA controlar Ableton directamente.

**Configuración:**

```bash
cd live-agent-remote
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" librosa
```

¡Agrega a la configuración de tu cliente MCP y reinicia para usar los 31 comandos como herramientas!

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

### Commandes

| Commande | Description |
|---|---|
| `ping` | Vérifier la connexion |
| `get_live_state` | Tempo, pistes, scènes, état de lecture |
| `list_tracks` | Lister toutes les pistes |
| `create_midi_track` | Créer une piste MIDI |
| `create_session_clip` | Créer un clip en vue session |
| `write_midi_notes` | Écrire des notes MIDI |
| `read_clip_notes` | Lire les notes du clip |
| `clear_clip_notes` | Supprimer toutes les notes |
| `list_devices` | Lister les appareils |
| `set_parameter_value` | Définir la valeur d'un paramètre |
| `write_clip_automation` | Écrire l'automation |
| `load_device` | Charger un plugin sur une piste |
| `list_browser_devices` | Rechercher/lister les plugins disponibles |
| `create_audio_track` | Créer une piste audio |
| `import_audio_clip` | Importer un fichier audio dans une piste |
| `get_clip_info` | Détails du clip (nom, type, boucle, warp) |
| `set_clip_properties` | Nom, couleur, boucle, pitch, gain du clip |
| `duplicate_clip` | Dupliquer le clip vers un autre emplacement |
| `delete_clip` | Supprimer le clip |
| `set_clip_warp` | Activer/désactiver le Warp et le mode |
| `analyze_and_warp` | Auto-warp avec BPM/tonalité détectés |
| `analyze_audio_file` | Analyser le BPM, la tonalité et les beats |
| `detect_pitch` | Détecter le pitch d'un sample one-shot |
| `analyze_folder` | Analyse par lot, trier par pitch |
| `find_compatible_samples` | Rechercher des samples compatibles (Camelot Wheel) |
| `create_smart_folder` | Dossier intelligent de samples compatibles dans le navigateur Ableton |
| `create_drum_rack` | Créer un Drum Rack sur une piste MIDI |
| `load_sample_to_pad` | Charger un sample sur un pad du Drum Rack |
| `inspect_drum_rack` | Inspecter la structure des pads du Drum Rack (débogage) |
| `eval` | Évaluer une expression Python dans le contexte Live |
| `exec` | Exécuter une instruction Python dans le contexte Live |

### Analyseur Audio

Analyse audio intégrée avec [librosa](https://librosa.org/) :

- **Détection BPM** — Extraction du tempo
- **Détection de tonalité** — Algorithme Krumhansl-Schmuckler, 24 tonalités
- **Détection de pitch** — Pour les samples one-shot (kicks, snares)
- **Classification des samples** — Classification automatique par durée : One-Shot (<2s), Short Loop (2-5s), Medium Loop (5-15s), Long Loop (>15s)
- **Camelot Wheel** — Correspondance harmonique style DJ
- **Analyse par lot** — Analyser des dossiers entiers, trier par pitch, filtrer par type de sample
- **Dossiers intelligents** — Génération automatique de symlinks de samples compatibles, visibles dans le navigateur Ableton
- **Auto-Warp** — Détecter BPM/tonalité et appliquer le Warp automatiquement

### Serveur MCP (Claude Desktop / Cursor etc.)

LiveAgent inclut un **serveur MCP** permettant aux agents IA de contrôler Ableton directement.

**Configuration :**

```bash
cd live-agent-remote
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" librosa
```

Ajoutez à la configuration de votre client MCP et redémarrez pour utiliser les 31 commandes comme outils !

---

## License

<div align="center">

Made with 💙 by Yuuka & Shota

</div>

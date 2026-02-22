# 本地文本转语音（完全离线，隐私保护）

不依赖任何第三方服务，使用 Windows 内置 TTS 引擎，文本不会上传到任何服务器。

## 前提条件

- Windows 系统（已内置 PowerShell 和中文语音包）
- 无需安装 Python / Node.js / 任何额外软件

## 查看可用语音

```powershell
powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
```

中文语音通常是 `Microsoft Huihui Desktop`（女声）。

## 转换单个文件

把要朗读的文字粘贴进 `$text`，运行以下命令，生成 `output.wav`：

```powershell
powershell -Command "
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Huihui Desktop')
$synth.SetOutputToWaveFile('d:\Git\stock_mindmap\output.wav')
$text = '在这里粘贴你的文字内容'
$synth.Speak($text)
$synth.Dispose()
"
```

## 转换 Markdown 文件（去掉格式符号）

用 PowerShell 脚本读取 `.md` 文件，自动清理 `#`、`-`、`*` 等 Markdown 符号后转换：

```powershell
powershell -Command "
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Huihui Desktop')
$synth.SetOutputToWaveFile('d:\Git\stock_mindmap\output.wav')

# 读取 md 文件并清理 Markdown 格式
$raw = Get-Content 'd:\Git\stock_mindmap\notes\china\A股80%交易量都是散户.md' -Encoding UTF8 -Raw
$text = $raw -replace '#+\s*', '' -replace '\*+', '' -replace '-\s+', '' -replace '\[.*?\]\(.*?\)', ''

$synth.Speak($text)
$synth.Dispose()
Write-Host '完成，输出到 output.wav'
"
```

## 播放生成的音频

```powershell
start output.wav
```

## 局限性

- Huihui 是传统 TTS，音质不如微信读书的神经网络语音自然
- 如果想要更自然的语音且可以接受内容发到微软服务器，可以安装 Python 后使用 `edge-tts`：
  ```bash
  pip install edge-tts
  edge-tts --voice zh-CN-XiaoxiaoNeural --text "你好" --write-media output.mp3
  ```

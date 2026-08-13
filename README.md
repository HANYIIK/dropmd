# DropMD

把本地文件拖进桌面应用，DropMD 会通过 Microsoft MarkItDown 在原文件目录生成同名 `.md` 文件。转换完全在本机完成，不需要安装 Python，也不会上传文件。

## 支持格式

Word（`.docx`）、PDF、PowerPoint（`.pptx`）、Excel（`.xlsx` / `.xls`）、Outlook（`.msg`）、HTML、CSV、JSON、XML、TXT、EPUB、IPYNB 和 ZIP。

## 本地开发

推荐使用 Python 3.12：

```bash
cd /Users/bello/Projects/dropmd
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m dropmd
```

运行测试：

```bash
pytest
```

## 构建 macOS 安装包

```bash
cd /Users/bello/Projects/dropmd
source .venv/bin/activate
bash scripts/build_macos.sh
```

产物位于 `release/DropMD-macOS-arm64.dmg`（Apple 芯片）或 `release/DropMD-macOS-x86_64.dmg`（Intel）。准备公开发布时，应使用 Apple Developer ID 对 `.app` 签名并公证，避免其他 Mac 显示“无法验证开发者”。

## 构建 Windows 安装包

在 Windows 安装 Python 3.12 和 Inno Setup 6，然后运行：

```powershell
cd C:\path\to\dropmd
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1
```

产物位于 `release/DropMD-Windows-Setup.exe`。面向公众分发时，建议使用代码签名证书为安装包签名，减少 SmartScreen 警告。

## 自动构建双平台安装包

项目包含 GitHub Actions。推送到 GitHub 后，在 Actions 页面手动运行 `Build installers` 即可下载 Apple 芯片 Mac、Intel Mac 和 Windows 三个安装包；推送 `v1.0.0` 这类标签时还会自动创建 GitHub Release。

```bash
git tag v1.1.0
git push origin v1.1.0
```

## 说明

DropMD 使用 MarkItDown 的 Python API，不会调用外部 `markitdown` 命令。安装包会包含 Python 运行时、Qt 和转换依赖，因此用户无需另行配置环境。

转换完成后，可在转换记录中点击“复制 Markdown”，将生成文件的完整内容直接复制到剪贴板。标题栏右侧支持浅色/深色主题切换，并会记住上次选择。

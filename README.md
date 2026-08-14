# DropMD

把本地文件拖进桌面应用，DropMD 会在原文件目录生成同名 `.md` 文件。转换完全在本机完成，不需要安装 Python，也不会上传文件。

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
git tag v1.4.0
git push origin v1.4.0
```

## 说明

DropMD 内置了基于 Microsoft MarkItDown 0.1.7 修改的转换源码，不会调用外部 `markitdown` 命令，也不再依赖用户安装 MarkItDown。XLSX 转换会展开合并单元格表达的层级、保留文本编号与工作表结构，并提示源文件中的重复编号；安装包包含 Python 运行时、Qt 和全部转换依赖。

默认外观跟随系统，也可在标题栏右侧固定为浅色或深色。转换完成后可复制 Markdown、打开文件、在文件夹中显示或复制文件路径；还可选择在单个文件转换完成后自动复制。

macOS 安装包带有标准拖拽安装界面，请将 `DropMD.app` 拖到 `Applications`。应用包包含产品分类、版本与说明元数据，安装到“应用程序”目录后可通过 Spotlight 搜索 `DropMD`。

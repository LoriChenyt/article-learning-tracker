# 常见问题与故障排查

本文汇总下载、测试、HAR 导出、CSV 生成和自定义分类过程中常见的问题。排查时不需要公开原始 HAR。

## 快速检查

在项目根目录运行：

```powershell
python --version
python -m unittest discover -s tests -v
python src/article_learning_tracker.py --help
```

正常状态包括：

- Python 版本为 3.10 或更高
- 9 项自动测试全部显示 `ok`
- 最后显示 `Ran 9 tests` 和 `OK`
- 帮助信息包含 `--input`、`--output` 和 `--rules`

## 找不到 `tests` 文件夹

常见错误：

```text
ImportError: Start directory is not importable: '.\tests'
```

或者：

```text
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

这通常表示终端位于“下载”目录，而不是解压后的项目根目录。

正确目录中应包含：

```text
src
tests
config
docs
README.md
```

PowerShell 可使用：

```powershell
Set-Location "$env:USERPROFILE\Downloads\article-learning-tracker-main"
Get-ChildItem
```

CMD 可使用：

```cmd
cd /d "%USERPROFILE%\Downloads\article-learning-tracker-main"
dir
```

如果目录不存在，可能尚未解压 ZIP，或者浏览器把新下载的文件命名为 `article-learning-tracker-main (1)`。实际文件夹名称应以本机显示为准。

## 测试数量不是9项

最新版应运行9项测试。如果仍然显示6项，通常表示使用了旧 ZIP 或旧的解压目录。

处理步骤：

1. 从 GitHub 重新下载 ZIP。
2. 解压到新的空目录。
3. 确认终端进入新目录。
4. 再次运行测试。

也可以检查程序是否包含 Base64 支持：

```powershell
Select-String -Path src/article_learning_tracker.py -Pattern "b64decode"
```

能够找到匹配内容表示程序包含 Base64 JSON 解码功能。

## 提示缺少 `--input` 和 `--output`

常见错误：

```text
error: the following arguments are required: --input, --output
```

这表示只运行了程序名称，没有提供输入和输出路径。完整的单行命令示例：

```powershell
python src/article_learning_tracker.py --input "C:\path\to\articles.har" --rules config/classification.example.json --output output/articles.csv
```

CMD 不使用 PowerShell 的反引号换行符，最稳妥的方式是把完整命令写在同一行。

## 找不到 HAR 文件

PowerShell 检查方式：

```powershell
Test-Path "C:\path\to\articles.har"
```

CMD 检查方式：

```cmd
dir "C:\path\to\articles.har"
```

路径中包含空格时必须保留双引号。浏览器重复下载时，文件名可能自动增加 `(1)`、`(2)` 等后缀。

## 生成0篇文章

可能原因包括：

- 输入的是单篇文章页面，而不是会加载文章列表的合集页面
- HAR 没有保存响应正文
- 打开 Network 之前，文章列表已经加载完成
- 页面没有实际滚动，分页请求没有触发
- 目标网站使用的响应字段不是 `article_list`

建议重新采集时先打开开发者工具的 Network 面板，启用 `Preserve log`，清空旧记录，刷新页面，再完整加载合集并导出 HAR。

## 文章数量偏少或出现缺号

程序结束时会显示唯一文章数量、编号范围和缺号。出现缺号时优先检查：

1. 是否使用最新版程序；旧版本不支持 Base64 JSON，可能漏掉完整分页。
2. Network 中分页请求是否全部成功。
3. 自动滚动是否过快，导致页面尚未加载完成就继续滚动。
4. HAR 是否在最后一个请求完成前导出。
5. 页面排序方式是否在采集过程中发生变化。

自动滚动结束后，适合额外等待数秒，再导出 HAR。连续编号只能证明已记录范围内没有断层；是否覆盖合集全部文章，还应与页面显示的总数对照。

## 结果仍然是629篇

某些 HAR 会把 JSON 响应保存为 Base64。旧版程序会忽略这些响应，从而得到629篇并报告两段缺号。最新版支持 Base64 JSON；同一份测试 HAR 应得到659篇、编号 `1–659`、缺号为0。

如果结果仍为629篇，应确认：

- 自动测试是否为9项
- `src/article_learning_tracker.py` 中是否存在 `b64decode`
- 当前终端是否位于最新解压目录

## Console 出现 Mixed Content

典型信息表示 HTTPS 页面引用了 HTTP 图片，浏览器随后自动把图片请求升级为 HTTPS。这通常是网页自身的警告，不是自动滚动脚本错误，也通常不会影响分页或 HAR 导出。

自动滚动是否正常应根据以下现象判断：

- 页面持续向下移动
- Console 持续显示滚动轮次
- Network 中的分页请求持续增加
- 脚本最后正常提示停止

## 中文输出显示乱码

如果终端中的中文乱码，但 CSV 用 Excel 打开后正常，通常只是终端编码问题，不影响数据内容。

CMD 可以先运行：

```cmd
chcp 65001
```

然后重新执行程序。生成的 CSV 使用带 BOM 的 UTF-8 编码，以提高 Excel 兼容性。

## 分类结果不符合主题

示例规则只是演示。分类内容由 `--rules` 指定的 JSON 文件决定，具体格式见 [`classification.md`](classification.md)。

常见配置错误包括：

- JSON 缺少逗号或括号
- `rules` 不是数组
- `keywords` 为空
- `category`、`difficulty` 或 `priority` 为空

配置错误时程序会显示 `分类配置无效`，并停止生成 CSV，避免静默产生错误分类。

## CSV 没有自动打开

程序只负责生成文件，不会默认启动 Excel。PowerShell 可以运行：

```powershell
Invoke-Item output/articles.csv
```

CMD 可以运行：

```cmd
start "" "output\articles.csv"
```

## 隐私和安全

HAR 可能包含账号标识、临时令牌、请求网址和响应内容。即使浏览器导出的是 sanitized HAR，也不代表文件适合公开。

以下内容不应提交到 GitHub Issue、Pull Request 或代码仓库：

- 原始 HAR
- Cookie 或 Authorization 请求头
- 含会话参数的完整网址
- 真实文章目录和个人学习笔记

报告问题时，只需提供：

- Python 版本
- 操作系统
- 执行的命令（路径可替换为占位符）
- 完整错误信息
- 生成数量、编号范围和缺号数量

能够复现结构问题时，应使用虚构的最小 JSON 示例代替真实 HAR。

# Article Learning Tracker

将用户自行取得的网页文章索引整理为可点击、可分类、可跟踪学习进度的本地 CSV 清单。

项目只处理用户本机文件，不提供任何特定网站、账号或作者的数据，不下载文章正文，也不会上传浏览器会话信息。

## 功能

- 从一个或多个 HAR 文件中发现文章列表
- 仅保留标题、发布日期、公开链接和原始顺序等必要字段
- 根据文章身份或规范化链接去重
- 删除 URL 中常见的登录和会话参数
- 生成 Excel 可直接打开的 UTF-8 CSV 学习清单
- 输出收录数量、编号范围和缺号检查结果
- 提供自动测试，验证去重和脱敏行为

## 安全边界

原始 HAR 可能包含 Cookie、请求头、账号标识和临时令牌。请始终在本地处理，不要把 HAR 提交到 GitHub。

本仓库的 `.gitignore` 默认排除：

- `*.har`
- `private/` 和 `data/`
- `output/`
- `*.xlsx`

程序不会把原始请求 URL、Cookie 或请求头写入输出文件。

## 快速开始

需要 Python 3.10 或更高版本，不需要安装第三方依赖。

```powershell
python src/article_learning_tracker.py `
  --input "C:\path\to\first.har" "C:\path\to\second.har" `
  --output "output\articles.csv"
```

生成的 CSV 包含以下字段：

```text
学习状态,建议学习顺序,原始编号,文章标题,发布日期,建议分类,难度,优先级,学习日期,需要复习,学习笔记,原文链接
```

用 Excel 打开后，可以点击原文链接，把学习状态改为“学习中”或“已完成”，并填写学习日期和笔记。

仓库中的 [`examples/sample_articles.csv`](examples/sample_articles.csv) 使用完全虚构的数据展示输出格式。

## 运行测试

```powershell
python -m unittest discover -s tests -v
```

测试使用程序临时生成的虚构数据，不包含真实 HAR 或真实文章信息。

## 项目流程

```text
本地 HAR
   ↓
识别文章列表
   ↓
字段白名单
   ↓
URL 会话参数清理
   ↓
去重和编号检查
   ↓
本地 CSV 学习清单
```

更详细的采集、验证和发布边界见 [`docs/workflow.md`](docs/workflow.md)。

## 隐私与内容说明

- 请只处理你有权访问的数据。
- 不要公开原始 HAR、Cookie、请求头或会话参数。
- 建议公开代码和虚构示例，把真实文章目录与个人笔记保留在本地。
- 文章内容和标题的相关权利归原作者或发布者所有。本项目只提供本地数据处理方法。

## License

代码使用 MIT License 发布。

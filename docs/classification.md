# 自定义分类规则

复制 `config/classification.example.json`，按目标主题修改后，通过 `--rules` 使用。

```powershell
Copy-Item config/classification.example.json classification.json
notepad classification.json
python src/article_learning_tracker.py `
  --input "C:\path\to\articles.har" `
  --rules classification.json `
  --output "output\articles.csv"
```

每条规则包含四项：

- `category`：写入 CSV 的建议分类
- `difficulty`：例如“入门”“中级”“进阶”
- `priority`：例如“高”“中”“低”
- `keywords`：只要标题包含其中一个关键词，就采用这条规则

规则按文件中的先后顺序匹配。如果一个标题同时命中多条规则，以排在前面的规则为准。没有命中的文章使用 `default` 中的值。

配置文件只定义分类方式，不应包含 Cookie、会话令牌或私人笔记。

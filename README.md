# AI 早报每日推送

每天早上 8 点（北京时间），从 [AI News Radar](https://learnprompt.github.io/ai-news-radar/) 提取 AI 相关度最高的 5 条新闻，通过飞书机器人推送卡片消息。

## 架构

```
GitHub Actions (UTC 00:00 = 北京时间 08:00)
  → 拉取 latest-24h.json
  → 按 ai_score 降序取 Top 5
  → POST 飞书机器人 API → 飞书私聊
```

## 配置

### 1. 飞书机器人

在 [飞书开发者后台](https://open.feishu.cn/app) 创建企业自建应用，添加权限 `im:message:send_as_bot` 并发布。

### 2. 环境变量 / GitHub Secrets

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `FEISHU_UNION_ID` | 接收人的 union_id（**注意：不能用 open_id，open_id 是应用级隔离的，跨应用会报 `open_id cross app` 错误**） |

### 3. 获取接收人的 union_id

通过飞书通讯录 API 或已授权的 lark-cli 工具获取：

```bash
lark-cli contact +get-user --as user
# 输出中的 union_id 字段即为所需值
```

## 本地运行

```bash
pip install -r requirements.txt

# Windows
set FEISHU_APP_ID=xxx
set FEISHU_APP_SECRET=xxx
set FEISHU_UNION_ID=on_xxx
python push.py

# Linux/macOS
FEISHU_APP_ID=xxx FEISHU_APP_SECRET=xxx FEISHU_UNION_ID=on_xxx python push.py
```

## 手动触发

GitHub Actions 页面 → "AI 早报每日推送" → Run workflow。

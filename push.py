"""
AI 早报推送脚本
1. 从 ai-news-radar 获取最近 24 小时 AI 新闻
2. 按 ai_score 降序取 Top 5
3. 格式化为飞书卡片消息并推送到指定用户
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

# ─── 配置 ────────────────────────────────────────────
DATA_URL = "https://learnprompt.github.io/ai-news-radar/data/latest-24h.json"
FEISHU_TOKEN_URL = (
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
)
FEISHU_MSG_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

# 标签 → 中文映射
LABEL_MAP = {
    "agent_workflow": "Agent 工作流",
    "ai_general": "AI 综合",
    "model_release": "模型发布",
    "developer_tool": "开发者工具",
    "ai_product": "AI 产品",
    "ai_ethics": "AI 伦理",
    "robotics": "机器人",
    "ai_research": "AI 研究",
    "ai_application": "AI 应用",
}

# ─── 飞书 API ────────────────────────────────────────


def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token"""
    resp = requests.post(
        FEISHU_TOKEN_URL,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def send_card_message(token: str, open_id: str, card: dict) -> dict:
    """发送飞书卡片消息"""
    payload = {
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    resp = requests.post(
        FEISHU_MSG_URL,
        params={"receive_id_type": "open_id"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    # 打印完整响应用于调试
    body = resp.json()
    print(f"[DEBUG] 飞书返回: {json.dumps(body, ensure_ascii=False)}")
    if resp.status_code != 200 or body.get("code") != 0:
        raise RuntimeError(f"飞书 API 错误 (HTTP {resp.status_code}, code={body.get('code')}): {body.get('msg', '未知错误')}")
    return body


# ─── 数据获取 ─────────────────────────────────────────


def fetch_top_news() -> list[dict]:
    """拉取最新 AI 新闻，返回 ai_score 最高的 5 条"""
    resp = requests.get(DATA_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    if not items:
        print("⚠ 数据源暂无新闻条目")
        return []

    # 过滤 AI 相关并按 ai_score 降序
    ai_items = [item for item in items if item.get("ai_is_related")]
    ai_items.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    return ai_items[:5]


# ─── 卡片构建 ─────────────────────────────────────────


def build_card(news_list: list[dict]) -> dict:
    """构建飞书交互卡片 JSON"""
    beijing_now = datetime.now(timezone.utc) + timedelta(hours=8)
    date_str = beijing_now.strftime("%Y-%m-%d")

    # 创建消息项
    elements = []
    for i, item in enumerate(news_list, 1):
        title = item.get("title", "无标题")
        source = item.get("source", "未知来源")
        url = item.get("url", "")
        score = item.get("ai_score", 0)
        label_key = item.get("ai_label", "")
        label_cn = LABEL_MAP.get(label_key, label_key or "综合")

        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{i}. [{title}]({url})**\n{source}  ·  {label_cn}  ·  AI 评分 **{score:.2f}**",
                },
            }
        )
        if i < len(news_list):
            elements.append({"tag": "hr"})

    # 页脚
    elements.append({"tag": "hr"})
    elements.append(
        {
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": "📡 数据来源：AI News Radar (learnprompt.github.io/ai-news-radar)",
                }
            ],
        }
    )

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"🔥 AI 早报 | {date_str}"},
            "template": "blue",
        },
        "elements": elements,
    }
    return card


# ─── 主流程 ──────────────────────────────────────────


def main():
    # 校验环境变量
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    open_id = os.environ.get("FEISHU_OPEN_ID")

    if not all([app_id, app_secret, open_id]):
        print("❌ 缺少环境变量：FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_OPEN_ID")
        sys.exit(1)

    print("📡 正在获取 AI 新闻数据 …")
    try:
        top5 = fetch_top_news()
    except Exception as e:
        print(f"❌ 获取新闻失败: {e}")
        sys.exit(1)

    if not top5:
        print("⚠ 没有 AI 相关新闻，跳过推送")
        return

    print(f"✅ 获取到 {len(top5)} 条 AI 新闻，开始构建卡片 …")
    card = build_card(top5)

    print("🔑 正在获取飞书 token …")
    try:
        token = get_tenant_token(app_id, app_secret)
    except Exception as e:
        print(f"❌ 获取 token 失败: {e}")
        sys.exit(1)

    print("📨 正在发送卡片消息 …")
    try:
        result = send_card_message(token, open_id, card)
    except Exception as e:
        print(f"❌ 发送消息失败: {e}")
        sys.exit(1)

    code = result.get("code", -1)
    if code == 0:
        print("✅ 推送成功！")
    else:
        print(f"❌ 推送失败，飞书返回: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()

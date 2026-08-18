"""
Bluesky 自動投稿ボット（完全無料・放置運用）
  queue.json から「まだ投稿していない」文章を1本取り出して投稿し、
  ポインタ(next)を1つ進めて保存する。GitHub Actions がこれを定期実行する。

環境変数（GitHub Secrets で設定）:
  BLUESKY_HANDLE        ... 例: yourname.bsky.social
  BLUESKY_APP_PASSWORD  ... Bluesky設定 → App Passwords で発行（本体パスワードではない）
"""

import json
import os

from atproto import Client

QUEUE_PATH = "queue.json"
BLUESKY_LIMIT = 300  # Blueskyの本文上限（書記素）


def load_queue():
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_queue(q):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def main():
    q = load_queue()
    posts = q.get("posts", [])
    nxt = q.get("next", 0)

    # キューを使い切っていたら、投稿せず正常終了（補充を促す）
    if nxt >= len(posts):
        print("キューが空です。generate_prompt.md でまとめて生成し、"
              "queue.json の posts を更新して next を 0 に戻してください。")
        return

    text = posts[nxt].strip()[:BLUESKY_LIMIT]

    client = Client()
    client.login(os.environ["BLUESKY_HANDLE"], os.environ["BLUESKY_APP_PASSWORD"])
    client.send_post(text=text)
    print(f"投稿しました (#{nxt}):\n{text}\n")

    # ポインタを進めて保存（この差分を Actions が commit する）
    q["next"] = nxt + 1
    save_queue(q)

    remaining = len(posts) - q["next"]
    print(f"残り {remaining} 件")
    if remaining <= 5:
        print("⚠️ 残りが少なくなっています。そろそろネタを補充してください。")


if __name__ == "__main__":
    main()

"""
Bluesky 自動投稿ボット（画像つき対応版・完全無料）
  queue.json から次の1本を取り出して投稿し、ポインタ(next)を進める。

queue.json の各要素は、次の2つの書き方どちらでもOK:
  1) 文字列だけ         → テキストのみ投稿
       "毎週の出勤表、手作業で…"
  2) オブジェクト        → 画像つき投稿
       { "text": "本文…", "image": "tsuki1.png", "alt": "出勤表の見本" }
     - image は images/ フォルダに置いたファイル名
     - alt は画像の説明（省略可・入れると親切）

環境変数（GitHub Secrets）:
  BLUESKY_HANDLE / BLUESKY_APP_PASSWORD
"""

import io
import json
import os

from atproto import Client

try:
    from PIL import Image
except ImportError:
    Image = None

QUEUE_PATH = "queue.json"
IMAGE_DIR = "images"
BLUESKY_LIMIT = 300          # 本文の上限（書記素）
MAX_IMAGE_BYTES = 900_000    # Blueskyの画像上限(約1MB)に余裕を持たせた値


def load_queue():
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_queue(q):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def read_image(filename):
    """images/ の画像を読み、大きすぎたら自動で縮小して返す。"""
    path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"画像 '{path}' が見つかりません。images/ にファイルがあるか、"
            f"queue.json のファイル名が正しいか確認してください。"
        )
    with open(path, "rb") as f:
        data = f.read()

    if len(data) <= MAX_IMAGE_BYTES:
        return data

    # 1MB超は縮小（Pillowが必要）
    if Image is None:
        raise RuntimeError(
            f"'{filename}' が大きすぎます（1MB超）。画像を小さくするか、"
            f"requirements.txt の pillow を有効にしてください。"
        )
    img = Image.open(io.BytesIO(data)).convert("RGB")
    for _ in range(12):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        if buf.tell() <= MAX_IMAGE_BYTES:
            return buf.getvalue()
        w, h = img.size
        img = img.resize((max(1, int(w * 0.85)), max(1, int(h * 0.85))))
    return buf.getvalue()


def main():
    q = load_queue()
    posts = q.get("posts", [])
    nxt = q.get("next", 0)

    if nxt >= len(posts):
        print("キューが空です。queue.json を更新して next を 0 に戻してください。")
        return

    item = posts[nxt]

    # 文字列 / オブジェクト どちらの書き方にも対応
    if isinstance(item, str):
        text, image_name, alt = item, None, ""
    else:
        text = item.get("text", "")
        image_name = item.get("image") or None
        alt = item.get("alt", "")

    text = text.strip()[:BLUESKY_LIMIT]

    client = Client()
    client.login(os.environ["BLUESKY_HANDLE"], os.environ["BLUESKY_APP_PASSWORD"])

    if image_name:
        image_data = read_image(image_name)
        client.send_image(text=text, image=image_data, image_alt=(alt or text[:100]))
        print(f"画像つきで投稿しました (#{nxt}) 画像={image_name}\n{text}\n")
    else:
        client.send_post(text=text)
        print(f"テキストのみ投稿しました (#{nxt})\n{text}\n")

    q["next"] = nxt + 1
    save_queue(q)

    remaining = len(posts) - q["next"]
    print(f"残り {remaining} 件")
    if remaining <= 5:
        print("⚠️ 残りが少なくなっています。そろそろ補充を。")


if __name__ == "__main__":
    main()

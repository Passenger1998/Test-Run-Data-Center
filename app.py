from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from pathlib import Path
from datetime import datetime
import os
import re

app = Flask(__name__)
app.secret_key = "change-this"  # 随便一个字符串，用于 flash 消息

# 路径配置（相对项目根目录）
IMAGES_ROOT = Path("images")
NOTES_DIR = Path("notes")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

TEMPLATE = """---
id: {id}
file_name: {file_name}
path: {rel_path}
date: {date}
source:
  type: ""
  url: ""
  author: ""
  title: ""
{tags_block}
media_type: "{media_type}"
style_tags: []
subject_tags: []
composition_tags: []
color_tags: []
notes: ""
---

{body}
"""


def extract_date_from_filename(filename: str) -> str:
    """
    从类似 20251203_test1.jpg 中提取日期，返回 YYYY-MM-DD 字符串
    """
    match = re.match(r"(\d{8})", filename)
    if match:
        try:
            d = datetime.strptime(match.group(1), "%Y%m%d")
            return d.date().isoformat()
        except ValueError:
            return ""
    return ""


def list_images():
    """
    扫描 images/ 下所有图片，返回列表
    """
    images = []
    if not IMAGES_ROOT.exists():
        return images

    for path in IMAGES_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            rel_path = path.as_posix()  # 相对项目根目录
            rel_under_images = path.relative_to(IMAGES_ROOT).as_posix()  # 用于图片访问
            stem = path.stem
            date = extract_date_from_filename(path.name)
            md_path = NOTES_DIR / f"{stem}.md"
            has_md = md_path.exists()
            images.append({
                "file_name": path.name,
                "rel_path": rel_path,
                "rel_under_images": rel_under_images,
                "stem": stem,
                "date": date,
                "has_md": has_md,
            })

    images.sort(key=lambda x: x["rel_path"])
    return images


@app.route("/")
def index():
    images = list_images()
    return render_template("index.html", images=images)


@app.route("/edit")
def edit():
    """
    编辑/生成单张图片的描述文件
    """
    rel_path = request.args.get("image")
    if not rel_path:
        return redirect(url_for("index"))

    p = Path(rel_path)
    default_id = p.stem
    default_date = extract_date_from_filename(p.name)

    return render_template(
        "edit.html",
        rel_path=rel_path,
        file_name=p.name,
        default_id=default_id,
        default_date=default_date
    )


@app.route("/save", methods=["POST"])
def save():
    rel_path = request.form["rel_path"]
    file_name = request.form["file_name"]

    id_val = (request.form.get("id") or "").strip() or Path(file_name).stem
    date_val = (request.form.get("date") or "").strip()
    media_type = (request.form.get("media_type") or "").strip()
    tags_str = (request.form.get("tags") or "").strip()
    body = request.form.get("body") or ""

    # 处理日期字段
    if date_val:
        date_yaml = f"\"{date_val}\""
    else:
        date_yaml = '""'

    # 处理 tags 字段（逗号分隔）
    tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
    if tags_list:
        tags_block = "tags:\n" + "\n".join(f"  - {t}" for t in tags_list)
    else:
        tags_block = "tags: []"

    content = TEMPLATE.format(
        id=id_val,
        file_name=file_name,
        rel_path=rel_path,
        date=date_yaml,
        tags_block=tags_block,
        media_type=media_type,
        body=body
    )

    NOTES_DIR.mkdir(exist_ok=True)
    stem = Path(file_name).stem
    md_path = NOTES_DIR / f"{stem}.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    flash(f"已生成描述文件：{md_path.as_posix()}")
    return redirect(url_for("index"))


@app.route("/img/<path:filename>")
def serve_image(filename):
    """
    用于在网页中显示 images/ 下的图片
    """
    return send_from_directory(IMAGES_ROOT, filename)


if __name__ == "__main__":
    import webbrowser
    from threading import Timer

    def open_browser():
        # 在默认浏览器打开你的网页
        webbrowser.open("http://127.0.0.1:5000")

    # 延迟 1 秒打开浏览器，确保 Flask 已经启动
    Timer(1, open_browser).start()

    # 建议关闭 debug=True，否则 Flask 会启动两个进程导致重复打开浏览器
    app.run(debug=False)

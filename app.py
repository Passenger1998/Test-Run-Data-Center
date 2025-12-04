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
media_applicaton_form: "{media_applicaton_form}"
style_tags: []
subject_tags: []
composition_tags: []
color_tags: []
notes: ""
---

{body}
"""


def extract_date_from_filename(filename: str) -> str:
    """从文件名中提取日期（YYYYMMDD 开头 → YYYY-MM-DD）"""
    match = re.match(r"(\d{8})", filename)
    if match:
        try:
            d = datetime.strptime(match.group(1), "%Y%m%d")
            return d.date().isoformat()
        except ValueError:
            return ""
    return ""


def list_images():
    """扫描 images/ 目录，列出所有图片及其元信息"""
    images = []
    if not IMAGES_ROOT.exists():
        return images

    for path in IMAGES_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            rel_path = path.as_posix()
            rel_under_images = path.relative_to(IMAGES_ROOT).as_posix()
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
        default_date=default_date,
    )


@app.route("/save", methods=["POST"])
def save():
    rel_path = request.form["rel_path"]
    file_name = request.form["file_name"]

    id_val = (request.form.get("id") or "").strip() or Path(file_name).stem
    date_val = (request.form.get("date") or "").strip()
    media_applicaton_form = (request.form.get("media_applicaton_form") or "").strip()
    tags_str = (request.form.get("tags") or "").strip()
    body = request.form.get("body") or ""

    # date 字段写入 YAML：有值时加引号，没有时写空字符串
    if date_val:
        date_yaml = f"\"{date_val}\""
    else:
        date_yaml = '""'

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
        media_applicaton_form=media_applicaton_form,
        body=body,
    )

    NOTES_DIR.mkdir(exist_ok=True)
    stem = Path(file_name).stem
    md_path = NOTES_DIR / f"{stem}.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    flash(f"已生成描述文件：{md_path.as_posix()}")
    return redirect(url_for("index"))


def shutdown_server():
    """关闭 Werkzeug 提供的开发服务器"""
    func = request.environ.get("werkzeug.server.shutdown")
    if func is None:
        # 不是在 werkzeug 的开发服务器环境中运行时抛错
        raise RuntimeError("Not running with the Werkzeug Server")
    func()


@app.route("/shutdown", methods=["POST"])
def shutdown():
    """处理来自网页的关闭请求：停止服务并尝试关闭当前页面"""
    shutdown_server()
    # 返回简单页面，尝试自动关闭当前窗口，失败则提示手动关闭
    return """
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <title>正在关闭</title>
      <script>
        // 尝试关闭当前窗口
        window.close();
        // 如果浏览器阻止自动关闭，则稍后给出提示
        setTimeout(function() {
          document.body.innerHTML = '<p>服务器已关闭，如页面未自动关闭，请手动关闭此标签页。</p>';
        }, 500);
      </script>
    </head>
    <body>
      <p>正在关闭服务器...</p>
    </body>
    </html>
    """


@app.route("/img/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_ROOT, filename)


if __name__ == "__main__":
    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    # 1 秒后自动打开浏览器
    Timer(1, open_browser).start()

    # 使用 debug=False，避免重载器导致的重复进程，便于正常关闭
    app.run(debug=False)

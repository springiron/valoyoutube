from flask import Flask, request, jsonify, render_template, send_file
import sqlite3
import os
from export_excel import export_to_excel

app = Flask(__name__)

# DB初期化
def init_db():
    conn = sqlite3.connect("database/videos.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos 
                 (id INTEGER PRIMARY KEY, url TEXT, memo TEXT, time TEXT)''')  # timeカラム追加
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/save", methods=["POST"])
def save_video():
    """動画のURL、停止時間、メモを保存"""
    data = request.json
    url = data.get("url")
    memo = data.get("memo", "")
    time = data.get("time", "")  # 停止時間を受け取る

    conn = sqlite3.connect("database/videos.db")
    c = conn.cursor()
    c.execute("INSERT INTO videos (url, memo, time) VALUES (?, ?, ?)", (url, memo, time))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/list", methods=["GET"])
def list_videos():
    """保存された動画リストを取得"""
    conn = sqlite3.connect("database/videos.db")
    c = conn.cursor()
    c.execute("SELECT id, url, memo, time FROM videos")
    videos = [{"id": row[0], "url": row[1], "memo": row[2], "time": row[3]} for row in c.fetchall()]
    conn.close()
    
    return jsonify(videos)

@app.route("/export_excel", methods=["GET"])
def download_excel():
    """Excel ファイルを生成 & ダウンロード"""
    file_path = export_to_excel()
    
    # ファイルが存在するか確認
    if not os.path.exists(file_path):
        return "Excel ファイルが見つかりません", 500

    return send_file(file_path, as_attachment=True, download_name="video_memo.xlsx")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

from flask import Flask, request, jsonify, render_template, send_file
import sqlite3
import os
from export_excel import export_to_excel
import pandas as pd

app = Flask(__name__)

# DB初期化 & データをクリアする関数
def init_db():
    conn = sqlite3.connect("database/videos.db")
    c = conn.cursor()
    
    # テーブルを作成（存在しない場合）
    c.execute('''CREATE TABLE IF NOT EXISTS videos 
                 (id INTEGER PRIMARY KEY, url TEXT, memo TEXT, time TEXT)''')
    
    # 既存データを削除（リセット）
    c.execute("DELETE FROM videos")
    
    conn.commit()
    conn.close()

@app.route("/")
def index():
    """サイトにアクセスしたらDBを初期化"""
    init_db()  # 🔹 DBを初期化
    return render_template("index.html")


@app.route("/save", methods=["POST"])
def save_video():
    """動画のURL、停止時間、メモを保存"""
    data = request.json
    url = data.get("url")
    memo = data.get("memo", "").replace("\n", "<br>")  # 🔹 改行を HTML `<br>` に変換
    time = data.get("time", "")

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

# Excel エクスポート API
@app.route("/export_excel", methods=["GET"])
def export_excel():
    conn = sqlite3.connect("database/videos.db")
    df = pd.read_sql_query("SELECT time, memo, url FROM videos", conn)
    conn.close()

    # 🔹 `<br>` を `\n` に置換
    df["memo"] = df["memo"].str.replace("<br>", "\n", regex=False)

    file_path = "exports/video_memo.xlsx"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Memos", index=False)

        # 🔹 Excel の書式設定（折り返して全体を表示）
        workbook = writer.book
        worksheet = writer.sheets["Memos"]
        wrap_format = workbook.add_format({"text_wrap": True})  # 🔹 セル内改行を適用

        worksheet.set_column("A:A", 15)  # 秒数の列の幅
        worksheet.set_column("B:B", 40, wrap_format)  # メモの列の幅（折り返し適用）
        worksheet.set_column("C:C", 30)  # URLの列の幅

    return send_file(file_path, as_attachment=True, download_name="video_memo.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# メモを更新する API
@app.route("/update_memo", methods=["POST"])
def update_memo():
    data = request.json
    memo_id = data.get("id")
    new_memo = data.get("memo")

    if not memo_id or new_memo is None:
        return jsonify({"status": "error", "message": "無効なデータ"})

    conn = sqlite3.connect("database/videos.db")
    c = conn.cursor()
    c.execute("UPDATE videos SET memo = ? WHERE id = ?", (new_memo, memo_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

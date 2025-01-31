from flask import Flask, request, jsonify, render_template, send_file, session
import sqlite3
import os
import pandas as pd
import uuid
import threading
import time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 🔹 セッション管理用のキー
SESSION_LIFETIME = 24 * 60  # 🔹 セッション有効期間（秒） 例: 5分
SESSIONS_DIR = "tmp/sessions"  # 🔹 セッションDBが保存されるディレクトリ

# 🔹 ユーザーごとのDBを作成・リセット
def get_db(reset=False):
    
    session_id = session.get("session_id")
    print(f"Session ID: {session_id}")
    
    if not session_id:
        session_id = str(uuid.uuid4())  # 🔹 ランダムなIDを作成
        session["session_id"] = session_id
        session["last_activity"] = time.time()  # 🔹 セッション開始時間を記録
        print("session df", session)

    
    db_path = f"tmp/sessions/{session_id}.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)

    # 🔹 初回またはリセット時にテーブルを作成
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                memo TEXT,
                url TEXT
            )
        """)
        if reset:
            conn.execute("DELETE FROM videos")  # 🔹 データをクリア

    return conn, db_path

@app.route("/")
def index():
    """サイトにアクセスしたらデータをクリア（リセット）"""
    session.pop("session_id", None)  # 🔹 リロード時にセッションをリセット
    get_db(reset=True)  # 🔹 各ユーザー専用のデータベースを作成し、初期化
    return render_template("index.html")

@app.route("/save", methods=["POST"])
def save_video():
    """動画のURL、停止時間、メモを保存"""
    data = request.json
    url = data.get("url")
    memo = data.get("memo", "").replace("\n", "<br>")  # 🔹 改行を HTML `<br>` に変換
    time_data = data.get("time", "")

    conn, _ = get_db()
    with conn:
        conn.execute("INSERT INTO videos (url, memo, time) VALUES (?, ?, ?)", (url, memo, time_data))

    session["last_activity"] = time.time()  # 🔹 作業があったらセッションを更新
    return jsonify({"status": "success"})

@app.route("/list", methods=["GET"])
def list_videos():
    """保存された動画リストを取得"""
    conn, _ = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, memo, time FROM videos")
    videos = [{"id": row[0], "url": row[1], "memo": row[2], "time": row[3]} for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(videos)

@app.route("/export_excel", methods=["GET"])
def export_excel():
    """Excelにエクスポート"""
    conn, _ = get_db()
    df = pd.read_sql_query("SELECT id, memo, url FROM videos", conn)
    conn.close()

    # 🔹 `<br>` を `\n` に置換
    df["memo"] = df["memo"].str.replace("<br>", "\n", regex=False)

    file_path = f"tmp/sessions/{session.get('session_id')}_video_memo.xlsx"
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

    return send_file(file_path, as_attachment=True, download_name="適当に名前を付けて保存してね.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/update_memo", methods=["POST"])
def update_memo():
    """メモを更新"""
    data = request.json
    memo_id = data.get("id")
    new_memo = data.get("memo")

    if not memo_id or new_memo is None:
        return jsonify({"status": "error", "message": "無効なデータ"})

    conn, _ = get_db()
    with conn:
        conn.execute("UPDATE videos SET memo = ? WHERE id = ?", (new_memo, memo_id))

    session["last_activity"] = time.time()  # 🔹 作業があったらセッションを更新
    return jsonify({"status": "success"})

def delete_user_db(session_id):
    """ `tmp/sessions/` 内の特定のセッションのDBとExcelファイルを削除 """
    time.sleep(30)  # 🔹 一定時間（5分）待つ

    db_path = os.path.join(SESSIONS_DIR, f"{session_id}.db")
    excel_path = os.path.join(SESSIONS_DIR, f"{session_id}_video_memo.xlsx")

    for file_path in [db_path, excel_path]:
        if os.path.exists(file_path):
            for _ in range(3):  # 🔹 最大3回リトライ
                try:
                    # 🔹 まず、DBを開いている可能性があるので接続を閉じる
                    try:
                        conn = sqlite3.connect(file_path)
                        conn.close()
                    except sqlite3.Error:
                        pass  # 🔹 DBが開けなかった場合はスキップ

                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                    break  # 🔹 成功したらループを抜ける

                except PermissionError:
                    print(f"File in use, retrying delete: {file_path}")
                    time.sleep(2)  # 🔹 2秒待って再試行

    print(f"Session {session_id} database deleted.")



@app.route("/close_session", methods=["POST"])
def close_session():
    """ ユーザーがページを閉じたときに呼び出される """
    print("セッション終了")
    session_id = session.get("session_id")
    # 🔹 バックグラウンドで `delete_all_dbs()` を実行
    thread = threading.Thread(target=delete_user_db,args=(session_id,))
    thread.start()

    return "", 204  # 🔹 レスポンスなし（204 No Content）

if __name__ == "__main__":
    app.run(debug=True)

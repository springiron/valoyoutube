import pandas as pd
import sqlite3
import os

# エクスポート用フォルダ作成（なければ作成）
EXPORT_FOLDER = "exports"
os.makedirs(EXPORT_FOLDER, exist_ok=True)

def export_to_excel():
    """SQLite のデータを取得し、Excel ファイルに保存"""
    conn = sqlite3.connect("database/videos.db")
    query = "SELECT id, url, memo, time FROM videos"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # ファイルの保存先
    file_path = os.path.join(EXPORT_FOLDER, "video_memo.xlsx")

    # Excel ファイルとして保存
    df.to_excel(file_path, index=False, engine='openpyxl')

    return file_path  # ファイルパスを返す

from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)

# DB初期化
def init_db():
    conn = sqlite3.connect("videos.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos 
                 (id INTEGER PRIMARY KEY, url TEXT, memo TEXT)''')
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/save", methods=["POST"])
def save_video():
    data = request.json
    url = data.get("url")
    memo = data.get("memo", "")

    conn = sqlite3.connect("videos.db")
    c = conn.cursor()
    c.execute("INSERT INTO videos (url, memo) VALUES (?, ?)", (url, memo))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/list", methods=["GET"])
def list_videos():
    conn = sqlite3.connect("videos.db")
    c = conn.cursor()
    c.execute("SELECT id, url, memo FROM videos")
    videos = [{"id": row[0], "url": row[1], "memo": row[2]} for row in c.fetchall()]
    conn.close()
    
    return jsonify(videos)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

let player;
let currentVideoId = "";

// メインページで YouTube 埋め込み
function loadVideo() {
    const urlInput = document.getElementById("videoUrlInput").value.trim();
    const videoId = extractVideoId(urlInput);

    if (!videoId) {
        alert("正しいYouTubeのURLを入力してください");
        return;
    }

    currentVideoId = videoId;

    if (player) {
        player.loadVideoById(videoId);
    } else {
        player = new YT.Player('player', {
            height: '500',
            width: '800',
            videoId: videoId,
            playerVars: {
                rel: 0,
                modestbranding: 1,
                playsinline: 1
            },
            events: {
                'onStateChange': onPlayerStateChange  // 動画の状態変更を監視
            }
        });
    }
}

// YouTube 動画の状態が変更されたときの処理
function onPlayerStateChange(event) {
    if (event.data === YT.PlayerState.PAUSED) {
        const time = player ? Math.floor(player.getCurrentTime()) : 0;
        console.log("動画が停止:", time, "秒");

        // 🔹 localStorage に停止時間を保存
        localStorage.setItem("latestVideoTime", JSON.stringify({ videoId: currentVideoId, time: time }));
    }
}

// メモを保存（動画が埋め込まれていない場合、ポップアップ表示）
function saveCurrentTime() {
    let latestData = JSON.parse(localStorage.getItem("latestVideoTime")) || {};
    
    if (!latestData.videoId) {
        alert("動画を再生して停止してください");
        return;
    }

    // 🔹 動画が埋め込まれていない場合、ポップアップ表示
    if (!player || !currentVideoId) {
        const userResponse = confirm("動画が埋め込まれていません。埋め込みますか？");
        if (userResponse) {
            document.getElementById("videoUrlInput").value = `https://www.youtube.com/watch?v=${latestData.videoId}`;
            loadVideo();  // 🔹 自動で埋め込み実行
        }
        return;  // メモの保存を中断
    }

    const formattedTime = formatTime(latestData.time);
    const videoUrl = `https://www.youtube.com/watch?v=${latestData.videoId}&t=${latestData.time}s`;
    const memo = document.getElementById("memoInput").value.trim() || "なし";

    fetch("/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: videoUrl, memo: memo, time: formattedTime })
    }).then(() => {
        document.getElementById("memoInput").value = "";
        loadVideos();
    });
}

// メモリストを取得し、編集モードの切り替えができるようにする
function loadVideos() {
    fetch("/list")
        .then(res => res.json())
        .then(videos => {
            const tableBody = document.querySelector("#videoTable tbody");
            tableBody.innerHTML = "";
            videos.forEach(video => {
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td><a href="${video.url}" target="_blank">${video.time}</a></td>
                    <td id="memo-container-${video.id}">
                        <span class="memo-text" id="memo-${video.id}">${video.memo.replace(/\n/g, " ")}</span>
                    </td>
                    <td>
                        <button class="memo-action-btn edit-btn" onclick="toggleEdit(${video.id})" id="edit-save-btn-${video.id}">
                            編集
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        });
}

// メモの編集モードを切り替え（編集 ⇔ 保存）
function toggleEdit(id) {
    const memoContainer = document.getElementById(`memo-container-${id}`);
    const memoText = document.getElementById(`memo-${id}`);
    const editSaveBtn = document.getElementById(`edit-save-btn-${id}`);

    if (!memoContainer.querySelector("textarea")) {
        // 🔹 編集モードにする（span → textarea）
        const textarea = document.createElement("textarea");
        textarea.id = `textarea-${id}`;
        textarea.className = "memo-input";
        textarea.value = memoText.innerText;
        memoContainer.replaceChild(textarea, memoText);

        // 🔹 ボタンを「保存」に変更
        editSaveBtn.textContent = "保存";
        editSaveBtn.setAttribute("onclick", `updateMemo(${id})`);
    }
}

// メモの更新を実行
function updateMemo(id) {
    const memoContainer = document.getElementById(`memo-container-${id}`);
    const textarea = document.getElementById(`textarea-${id}`);
    const newMemo = textarea.value.trim();

    fetch("/update_memo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id, memo: newMemo })
    }).then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            // 🔹 更新後、textarea を span に戻す
            const span = document.createElement("span");
            span.id = `memo-${id}`;
            span.className = "memo-text";
            span.textContent = newMemo.replace(/\n/g, "\n"); // 改行をスペースに変換
            memoContainer.replaceChild(span, textarea);

            // 🔹 ボタンを「編集」に戻す
            const editSaveBtn = document.getElementById(`edit-save-btn-${id}`);
            editSaveBtn.textContent = "編集";
            editSaveBtn.setAttribute("onclick", `toggleEdit(${id})`);
        } else {
            alert("更新に失敗しました");
        }
    }).catch(error => console.error("エラー:", error));
}


// 🔹 Excel にエクスポートする関数
function exportExcel() {
    console.log("Excelエクスポート処理を開始");

    fetch("/export_excel")
        .then(response => {
            if (!response.ok) {
                throw new Error("Excel エクスポートに失敗しました");
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "video_memo.xlsx";  // 🔹 ダウンロードファイル名
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            console.log("Excelファイルのダウンロードが完了しました");
        })
        .catch(error => {
            console.error("エラー:", error);
            alert("Excelエクスポートに失敗しました");
        });
}

// URLから動画IDを取得
function extractVideoId(url) {
    const regex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

// 秒数を「X分Y秒」にフォーマット
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}分${remainingSeconds}秒`;
}

// 🔹 localStorage の監視
window.addEventListener("storage", (event) => {
    if (event.key === "latestVideoTime") {
        console.log("別タブで停止された情報を取得:", event.newValue);
    }
});

// 初回ロード時に最新のデータを取得
document.addEventListener("DOMContentLoaded", () => {
    loadVideos();
});


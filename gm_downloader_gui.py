import os
import sys
import subprocess
import configparser
import requests
import shutil
import time
import winreg
import threading
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QIcon

app = Flask(__name__)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
STEAMCMD_EXE = os.path.join(BASE_DIR, "steamcmd.exe")
INI_FILE = os.path.join(BASE_DIR, "set.ini")

download_status = {"progress": 0, "status": "Ожидание..."}

def get_gmod_path():
    if os.path.exists(INI_FILE):
        config = configparser.ConfigParser()
        config.read(INI_FILE, encoding='utf-8')
        if 'SETTINGS' in config and 'AddonsPath' in config['SETTINGS']:
            return config['SETTINGS']['AddonsPath'].replace('"', '').strip()
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path = winreg.QueryValueEx(hkey, "SteamPath")[0]
        winreg.CloseKey(hkey)
        path = os.path.join(steam_path, "steamapps", "common", "GarrysMod", "garrysmod", "addons")
        if os.path.exists(path): return path
    except: pass
    return r"C:\Program Files (x86)\Garrys Mod\garrysmod\addons"

def process_download(wid, name):
    global download_status
    download_status = {"progress": 10, "status": "Запуск SteamCMD..."}
    target_path = get_gmod_path()
    gmad_path = os.path.join(os.path.dirname(os.path.dirname(target_path)), "bin", "gmad.exe")
    
    cmd = [STEAMCMD_EXE, "+login", "anonymous", "+workshop_download_item", "4000", str(wid), "+quit"]
    try:
        # Запуск в тихом режиме
        subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        down_dir = os.path.join(BASE_DIR, "steamapps", "workshop", "content", "4000", str(wid))
        
        found = False
        for i in range(15):
            if os.path.exists(down_dir) and os.listdir(down_dir):
                found = True
                break
            time.sleep(1)

        if found:
            download_status = {"progress": 80, "status": "Распаковка..."}
            files = os.listdir(down_dir)
            src = os.path.join(down_dir, files[0])
            safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
            
            if os.path.exists(gmad_path):
                out_dir = os.path.join(target_path, safe_name)
                if not os.path.exists(out_dir): os.makedirs(out_dir)
                subprocess.run([gmad_path, "extract", "-file", src, "-out", out_dir], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                download_status = {"progress": 100, "status": "Успешно установлено!"}
            else:
                shutil.copy2(src, os.path.join(target_path, f"{safe_name}.gma"))
                download_status = {"progress": 100, "status": "Скопировано .gma"}
        else:
            download_status = {"progress": 0, "status": "Файл не найден"}
    except:
        download_status = {"progress": 0, "status": "Ошибка!"}

@app.route('/')
def index(): return HTML_TEMPLATE

@app.route('/get_info')
def api_get_info():
    aid = request.args.get('id')
    try:
        r = requests.get(f"https://steamcommunity.com/sharedfiles/filedetails/?id={aid}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        stats = soup.find_all("div", class_="detailsStatRight")
        return jsonify({
            "title": soup.find("div", class_="workshopItemTitle").get_text(strip=True),
            "preview": soup.find("img", id="previewImageMain")['src'],
            "size": stats[0].get_text(strip=True) if len(stats) > 0 else "0 MB"
        })
    except: return jsonify({"error": True})

@app.route('/start_download')
def api_start_download():
    aid, title = request.args.get('id'), request.args.get('title')
    threading.Thread(target=process_download, args=(aid, title), daemon=True).start()
    return jsonify({"success": True})

@app.route('/get_progress')
def api_get_progress(): return jsonify(download_status)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Fredoka+One&display=swap" rel="stylesheet">
    <style>
        body { background: #0f1720; color: white; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; margin: 0; }
        .main_title { font-family: 'Fredoka One', cursive; font-size: 54px; color: #5399d8; margin-bottom: 25px; text-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .container { width: 90%; max-width: 800px; background: #1b2838; border-radius: 25px; padding: 25px; box-shadow: 0 15px 40px rgba(0,0,0,0.6); }
        input { width: 100%; background: #121921; border: 2px solid #252f3d; color: #fff; padding: 15px; border-radius: 15px; text-align: center; font-size: 20px; margin-bottom: 25px; outline: none; box-sizing: border-box; }
        #addon_card { display: none; background: #007bff; border-radius: 22px; padding: 20px; position: relative; min-height: 180px; }
        .preview { width: 170px; height: 170px; border-radius: 15px; float: left; margin-right: 20px; object-fit: cover; }
        .info_area { margin-right: 170px; }
        .info_area h2 { font-family: 'Fredoka One', cursive; margin: 0 0 10px 0; font-size: 26px; }
        .btn_install { position: absolute; right: 20px; top: 20px; background: white; color: black; border: none; padding: 12px 25px; border-radius: 15px; font-family: 'Fredoka One', cursive; font-size: 20px; cursor: pointer; }
        .progress_bg { width: 160px; background: rgba(0,0,0,0.3); height: 10px; border-radius: 5px; margin-top: 10px; display: none; overflow: hidden; position: absolute; right: 20px; top: 75px; }
        .progress_bar { width: 0%; height: 100%; background: #adff2f; transition: 0.4s; }
        .status_label { position: absolute; right: 20px; top: 90px; font-size: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="main_title">gm_downloader</div>
    <div class="container">
        <input type="text" id="sid" placeholder="Вставь ID аддона здесь..." oninput="update()">
        <div id="addon_card">
            <img id="p_img" class="preview" src="">
            <button id="dl_btn" class="btn_install" onclick="start()">Install!</button>
            <div id="p_bg" class="progress_bg"><div id="p_bar" class="progress_bar"></div></div>
            <div id="s_lbl" class="status_label"></div>
            <div class="info_area">
                <h2 id="p_title"></h2>
                <p id="p_size"></p>
            </div>
        </div>
    </div>
    <script>
        let curT = "";
        function update() {
            let id = document.getElementById('sid').value.trim();
            if(id.length > 7) {
                fetch('/get_info?id='+id).then(r=>r.json()).then(data=>{
                    if(!data.error){
                        curT = data.title;
                        document.getElementById('addon_card').style.display='block';
                        document.getElementById('p_img').src=data.preview;
                        document.getElementById('p_title').innerText=data.title;
                        document.getElementById('p_size').innerText="Размер: "+data.size;
                    }
                });
            }
        }
        function start() {
            document.getElementById('dl_btn').disabled=true;
            document.getElementById('p_bg').style.display='block';
            fetch(`/start_download?id=${document.getElementById('sid').value}&title=${encodeURIComponent(curT)}`);
            setInterval(()=>{
                fetch('/get_progress').then(r=>r.json()).then(s=>{
                    document.getElementById('p_bar').style.width=s.progress+'%';
                    document.getElementById('s_lbl').innerText=s.status;
                    if(s.progress>=100) document.getElementById('dl_btn').innerText="Готово!";
                });
            }, 1000);
        }
    </script>
</body>
</html>
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM_Downloader")
        self.setFixedSize(900, 550)
        self.setWindowIcon(QIcon("ico.ico"))
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("http://127.0.0.1:5888"))
        self.setCentralWidget(self.browser)

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(port=5888, debug=False, use_reloader=False), daemon=True).start()
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(qt_app.exec())

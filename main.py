import os
import sys
import subprocess
import configparser
import requests
import shutil
import time
import winreg
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel

console = Console(force_terminal=True)

# ОПРЕДЕЛЕНИЕ ПАПКИ (Где лежит сам EXE или скрипт)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STEAMCMD_EXE = os.path.join(BASE_DIR, "steamcmd.exe")
INI_FILE = os.path.join(BASE_DIR, "set.ini")

system_logs = ["Система готова. Двигатель: SteamCMD (Стабильный)"]

LOGO_ART = r"""[light_blue]
  _____                     _____                     _                 _           
 / ____|                   |  __ \                   | |               | |          
| |  __ _ __ ___           | |  | | _____       ___ __ | | ___   __ _  __| | ___ _ __ 
| | |_ | '_ ` _ \          | |  | |/ _ \ \ /\ / / '_ \| |/ _ \ / _` |/ _` |/ _ \ '__|
| |__| | | | | | |          | |__| | (_) \ V  V /| | | | | (_) | (_| | (_| |  __/ |   
 \_____|_| |_| |_|          |_____/ \___/ \_/\_/ |_| |_|_|\___/ \__,_|\__,_|\___|_|   
                      ______                                                           
                     |______|[/light_blue]
"""

def get_gmod_path():
    """Ищет папку addons в реестре или конфиге"""
    if os.path.exists(INI_FILE):
        config = configparser.ConfigParser()
        config.read(INI_FILE, encoding='utf-8')
        if 'SETTINGS' in config and 'AddonsPath' in config['SETTINGS']:
            return config['SETTINGS']['AddonsPath'].replace('"', '').strip()
    
    # Авто-поиск через реестр Steam
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path = winreg.QueryValueEx(hkey, "SteamPath")[0]
        winreg.CloseKey(hkey)
        path = os.path.join(steam_path, "steamapps", "common", "GarrysMod", "garrysmod", "addons")
        if os.path.exists(path): return path
    except: pass
    
    return r"C:\Program Files (x86)\Garrys Mod\garrysmod\addons"

def get_addon_name(wid):
    """Получает название аддона из Steam Workshop"""
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={wid}"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find("div", class_="workshopItemTitle")
        return title.get_text(strip=True) if title else f"Addon_{wid}"
    except: return f"Addon_{wid}"

def draw_screen(status, path):
    """Рисует интерфейс в консоли"""
    console.clear()
    console.print(Panel(LOGO_ART, border_style="blue", padding=(1, 2)))
    logs_display = "\n".join(system_logs[-6:])
    console.print(Panel(f"[white]{logs_display}[/white]", title="Логи", border_style="bright_black"))
    console.print(Panel(f"Путь: {path} | Статус: [bold]{status}[/bold]", border_style="cyan"))

def main():
    if not os.path.exists(STEAMCMD_EXE):
        console.print(f"[red]ОШИБКА: steamcmd.exe не найден в {BASE_DIR}[/red]")
        input("Нажмите Enter для выхода...")
        return

    target_path = get_gmod_path() # Путь к addons
    gmad_path = os.path.join(os.path.dirname(os.path.dirname(target_path)), "bin", "gmad.exe")

    while True:
        draw_screen("ОЖИДАНИЕ", target_path)
        wid = console.input("\n[bold]Введите ID аддона[/bold] (или 'exit'): ").strip()
        if wid.lower() == 'exit': break
        if not wid.isdigit(): continue
        
        name = get_addon_name(wid)
        draw_screen("ПОДТВЕРЖДЕНИЕ", target_path)
        ans = console.input(f"Скачать [bold yellow]{name}[/bold yellow]? (y/n): ")
        
        if ans.lower() == 'y':
            system_logs.append(f"Запуск загрузки ID {wid}...")
            draw_screen("ЗАГРУЗКА", target_path)
            
            cmd = [STEAMCMD_EXE, "+login", "anonymous", "+workshop_download_item", "4000", wid, "+quit"]
            try:
                subprocess.run(cmd, check=True)
                
                # Ищем папку steamapps строго там, где лежит steamcmd.exe
                down_dir = os.path.join(os.path.dirname(STEAMCMD_EXE), "steamapps", "workshop", "content", "4000", wid)
                
                found = False
                system_logs.append("Ожидание записи файла на диск...")
                for i in range(10): # Ждем до 10 секунд
                    if os.path.exists(down_dir) and os.listdir(down_dir):
                        found = True
                        break
                    time.sleep(1)
                    system_logs.append(f"Ждем... ({i+1}/10)")
                    draw_screen("ПРОВЕРКА", target_path)

                if found:
                    files = os.listdir(down_dir)
                    src = os.path.join(down_dir, files[0])
                    safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')]).strip()
                    
                    if os.path.exists(gmad_path):
                        out_dir = os.path.join(target_path, safe_name)
                        if not os.path.exists(out_dir): os.makedirs(out_dir)
                        subprocess.run([gmad_path, "extract", "-file", src, "-out", out_dir], check=True)
                        system_logs.append(f"[green]Успех![/green] {safe_name} распакован.")
                    else:
                        dst = os.path.join(target_path, f"{safe_name}.gma")
                        shutil.copy2(src, dst)
                        system_logs.append(f"[green]Успех![/green] Файл {safe_name}.gma скопирован.")
                else:
                    system_logs.append(f"[red]Ошибка:[/red] Путь {down_dir} пуст!")
            except Exception as e:
                system_logs.append(f"[red]Ошибка:[/red] {str(e)}")
        else:
            system_logs.append("Отмена.")

if __name__ == "__main__":
    main()
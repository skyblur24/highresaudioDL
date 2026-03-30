#!/usr/bin/env python3

# Standard
import os
import re
import sys
import json
import time
import platform
import traceback

# Third party
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

# ==========================================
# 🔧 RUTA DE DESCARGA    👇🏼👇🏼👇🏼👇🏼👇🏼
# ==========================================
BASE_DOWNLOAD_PATH = "/content/drive/MyDrive/HRA/"
# ==========================================

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0"
})

def getOs():
    return platform.system() == 'Windows'

def osCommands(x):
    if getOs():
        if x == "p":
            os.system('pause >nul')
        elif x == "c":
            os.system('cls')
        elif x == "t":
            os.system('title HRA-DL (Optimized)')
    else:
        if x == "p":
            os.system("read -rsp $''")
        elif x == "c":
            os.system('clear')
        elif x == "t":
            sys.stdout.write("\x1b]2;HRA-DL (Optimized)\x07")

def login(email, pwd):
    r = session.get(
        f'https://streaming.highresaudio.com:8182/vault3/user/login?password={pwd}&username={email}'
    )
    if r.status_code == 200 and "has_subscription" in r.json():
        print("Signed in successfully.\n")
        return r.text
    else:
        print("Login failed or no subscription.")
        osCommands('p')
        sys.exit()

def fetchAlbumId(url):
    soup = BeautifulSoup(session.get(url).text, "html.parser")
    return soup.find(attrs={"data-id": True})['data-id']

def fetchMetadata(albumId, userData):
    r = session.get(
        f'https://streaming.highresaudio.com:8182/vault3/vault/album/?album_id={albumId}&userData={userData}'
    )
    if r.status_code != 200:
        print("Failed to fetch metadata.")
        osCommands('p')
        sys.exit()
    return r.json()

def dirSetup(path):
    os.makedirs(path, exist_ok=True)
    return path

def fileSetup(fname):
    if os.path.isfile(fname):
        os.remove(fname)

# ==========================================
# 🔥 FETCH TRACK CON SISTEMA ANTI-CONGELAMIENTO
# ==========================================
def fetchTrack(albumId, fname, spec, trackNum, trackTitle, trackTotal, url):

    max_retries = 6
    timeout_seconds = 8
    attempt = 0

    while attempt < max_retries:

        try:
            session.headers.update({
                "range": "bytes=0-",
                "referer": f"https://stream-app.highresaudio.com/album/{albumId}"
            })

            print(f"Downloading {trackNum}/{trackTotal}: {trackTitle} - {spec} (Attempt {attempt+1})")

            r = session.get(url, stream=True, timeout=15)
            size = int(r.headers.get('content-length', 0))

            downloaded = 0
            last_progress_time = time.time()

            with open(fname, 'wb') as f:
                with tqdm(total=size, unit='B', unit_scale=True, unit_divisor=1024) as bar:

                    for chunk in r.iter_content(128 * 1024):

                        if chunk:
                            f.write(chunk)
                            chunk_size = len(chunk)
                            downloaded += chunk_size
                            bar.update(chunk_size)
                            last_progress_time = time.time()

                        # Detectar congelamiento
                        if time.time() - last_progress_time > timeout_seconds:
                            raise Exception("Download stalled")

            return  # Descarga exitosa

        except Exception:
            attempt += 1
            print(f"\n⚠ Download interrupted. Retrying... ({attempt}/{max_retries})\n")
            time.sleep(2)

    print(f"\n❌ Failed after {max_retries} attempts.\n")

def fetchFile(url, dest):
    fileSetup(dest)
    r = session.get(url, stream=True)
    size = int(r.headers.get('content-length', 0))

    with open(dest, 'wb') as f:
        with tqdm(total=size, unit='B', unit_scale=True, unit_divisor=1024) as bar:
            for chunk in r.iter_content(128 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

def sanitizeFname(fname):
    if getOs():
        return re.sub(r'[\\/:*?"><|]', '-', fname)
    else:
        return re.sub('/', '-', fname)

def main(userData):
    url = input("Input HIGHRESAUDIO Store URL: ").strip()

    if not url:
        osCommands('c')
        return

    if not re.match(r"https?://(?:www\.)?highresaudio\.com/", url):
        print("Invalid URL.")
        time.sleep(1)
        osCommands('c')
        return

    osCommands('c')

    albumId = fetchAlbumId(url)
    metadata = fetchMetadata(albumId, userData)

    artist = metadata['data']['results']['artist']
    title = metadata['data']['results']['title']

    tracks = metadata['data']['results']['tracks']

    # ==========================================
    # 🔎 DETECTAR FRECUENCIAS DE MUESTREO
    # ==========================================
    sample_rates = set()

    for t in tracks:
        try:
            rate = float(t['format'])
            sample_rates.add(rate)
        except:
            pass

    sample_rates = sorted(sample_rates)

    formatted_rates = []
    for r in sample_rates:
        if r % 1 == 0:
            formatted_rates.append(f"{r:.1f}kHz")
        else:
            formatted_rates.append(f"{r}kHz")

    rate_string = " & ".join(formatted_rates)
    quality_tag = f"[HIGHRESAUDIO HRA 24bits/{rate_string}]"

    albumFolder = f"{artist} - {title} {quality_tag}"

    # ==========================================
    # 📘 Detectar Booklet antes de crear carpeta
    # ==========================================
    hasBooklet = "booklet" in metadata['data']['results']
    if hasBooklet:
        albumFolder = f"{albumFolder} + Digital Booklet"

    print(f"{albumFolder}\n")

    albumPath = dirSetup(
        os.path.join(BASE_DOWNLOAD_PATH, sanitizeFname(albumFolder))
    )

    # ==========================================
    # 🎨 COVER DOWNLOAD
    # ==========================================
    cover_data = metadata['data']['results'].get("cover")

    if cover_data:

        if "master" in cover_data and "file_url" in cover_data["master"]:
            print("Downloading MASTER Cover...")
            cover_url = "https://" + cover_data["master"]["file_url"]
            fetchFile(cover_url, os.path.join(albumPath, "folder.jpg"))

        if "preview" in cover_data and "file_url" in cover_data["preview"]:
            print("Downloading Small Cover (350x350)...")
            small_cover_url = "https://" + cover_data["preview"]["file_url"]
            fetchFile(small_cover_url, os.path.join(albumPath, "small_folder.jpg"))

    tracks = metadata['data']['results']['tracks']
    totalTracks = str(len(tracks)).zfill(2)

    for track in tracks:
        trackNum = str(track['trackNumber']).zfill(2)
        trackTitle = sanitizeFname(track['title'])

        tempFile = os.path.join(albumPath, f"{trackNum}.flac")
        finalFile = os.path.join(albumPath, f"{trackNum}. {trackTitle}.flac")

        fileSetup(tempFile)
        fileSetup(finalFile)

        fetchTrack(
            albumId,
            tempFile,
            f"{track['format']} kHz FLAC",
            trackNum,
            track['title'],
            totalTracks,
            track['url']
        )

        if os.path.exists(tempFile):
            os.rename(tempFile, finalFile)

    # ==========================================
    # 📘 BOOKLET DOWNLOAD
    # ==========================================
    if hasBooklet:
        print("Downloading Booklet...")
        fetchFile(
            f"https://{metadata['data']['results']['booklet']}",
            os.path.join(albumPath, "booklet.pdf")
        )

    print("\nAlbum completed.")
    time.sleep(1)
    osCommands('c')

if __name__ == '__main__':
    osCommands('t')

    with open("config.json") as f:
        config = json.load(f)

    userData = login(config["email"], config["password"])

    try:
        while True:
            main(userData)
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
    except:
        traceback.print_exc()
        input("\nAn exception has occurred. Press enter to exit.")
        sys.exit()
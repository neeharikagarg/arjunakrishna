
from pathlib import Path
import json
import re
import shutil
from datetime import datetime

import yt_dlp


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLAtNrs_fIyrw"

VIDEOS_DIR = PROJECT_DIR / "videos"
PLAYLIST_FILE = PROJECT_DIR / "playlist.md"

TARGET_LANGUAGES = {
    "en": "raw_en.vtt",
    "hi": "raw_hi.vtt",
}

# Set True to prefer manually uploaded subtitles over auto captions.
PREFER_MANUAL_SUBTITLES = True


# ============================================================
# GENERAL HELPERS
# ============================================================

def log(message):
    print(f"[{datetime.now():%H:%M:%S}] {message}")


def get_video_id(entry):
    return entry.get("id")


def get_video_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def get_language_group(language_code):
    """
    Convert language codes such as en-US or hi-IN
    into their base language.
    """
    code = language_code.lower().replace("_", "-")

    if code == "en" or code.startswith("en-"):
        return "en"

    if code == "hi" or code.startswith("hi-"):
        return "hi"

    return None


def get_language_rank(language_code, preferred):
    """
    Prefer exact en/hi over regional variants.
    """
    code = language_code.lower().replace("_", "-")

    if code == preferred:
        return 0

    return 1


def save_json(path, data):
    temp_path = path.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def make_video_folder(title, video_id, upload_date):
    """Create a readable folder named YYYY-MM-DD - Video Title."""
    if upload_date and re.fullmatch(r"\d{8}", str(upload_date)):
        formatted_date = (
            f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        )
    else:
        formatted_date = "Date-Unknown"

    safe_title = re.sub(r'[<>:"/\\|?*]', "", title or "")
    safe_title = re.sub(r"\s+", " ", safe_title).strip().rstrip(". ")
    if not safe_title:
        safe_title = video_id

    folder_name = f"{formatted_date} - {safe_title}"
    folder = VIDEOS_DIR / folder_name

    # If this exact folder belongs to another video, make the ID suffix unique.
    if folder.exists():
        metadata_file = folder / "metadata.json"
        existing_id = None

        if metadata_file.exists():
            try:
                existing_id = json.loads(
                    metadata_file.read_text(encoding="utf-8")
                ).get("id")
            except (OSError, json.JSONDecodeError):
                pass

        if existing_id != video_id:
            folder = VIDEOS_DIR / f"{folder_name} [{video_id}]"

    # Migrate an older ID-named folder when one exists.
    old_folder = VIDEOS_DIR / video_id
    if old_folder.exists() and old_folder != folder:
        if not folder.exists():
            old_folder.rename(folder)
        else:
            # Preserve files already downloaded in the old folder.
            for old_file in old_folder.iterdir():
                new_file = folder / old_file.name
                if old_file.is_file() and not new_file.exists():
                    shutil.move(str(old_file), str(new_file))
            try:
                old_folder.rmdir()
            except OSError:
                pass

    return folder


# ============================================================
# PLAYLIST CATALOGUE
# ============================================================

def initialise_playlist_file():
    """
    Create playlist.md only if it does not exist.
    Never erase an existing catalogue.
    """
    if not PLAYLIST_FILE.exists():
        PLAYLIST_FILE.write_text(
            "# Arjuna Krishna Teachings – Playlist\n\n"
            f"Playlist: {PLAYLIST_URL}\n\n",
            encoding="utf-8",
        )


def add_to_playlist_catalogue(metadata):
    """
    Append a video only if its ID is not already present.
    """
    initialise_playlist_file()

    content = PLAYLIST_FILE.read_text(encoding="utf-8")

    video_id = metadata["id"]

    if video_id in content:
        return

    title = metadata.get("title", "Untitled")
    upload_date = metadata.get("upload_date", "Unknown date")
    url = metadata.get("webpage_url", get_video_url(video_id))

    entry = (
        f"## {title}\n\n"
        f"- Video ID: `{video_id}`\n"
        f"- Upload date: {upload_date}\n"
        f"- URL: {url}\n\n"
    )

    with PLAYLIST_FILE.open("a", encoding="utf-8") as file:
        file.write(entry)


# ============================================================
# FETCH PLAYLIST
# ============================================================

def fetch_playlist():
    log("Fetching playlist information...")

    options = {
        "extract_flat": True,
        "quiet": True,
        "ignoreerrors": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        playlist = ydl.extract_info(
            PLAYLIST_URL,
            download=False,
        )

    if not playlist:
        raise RuntimeError("Unable to fetch playlist.")

    entries = playlist.get("entries") or []

    log(f"Playlist: {playlist.get('title', 'Unknown')}")
    log(f"Videos found: {len(entries)}")

    return entries


# ============================================================
# FETCH VIDEO METADATA
# ============================================================

def fetch_video_metadata(video_url):
    options = {
        "quiet": True,
        "ignoreerrors": True,
        "skip_download": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(
            video_url,
            download=False,
        )


def get_available_languages(metadata, subtitle_type):
    """
    Return available English/Hindi language codes.

    subtitle_type can be:
        subtitles
        automatic_captions
    """
    available = metadata.get(subtitle_type) or {}

    selected = []

    for language_code in available:
        if get_language_group(language_code):
            selected.append(language_code)

    return selected


# ============================================================
# DOWNLOAD SUBTITLES
# ============================================================

def download_subtitle_type(
    video_id,
    video_url,
    languages,
    destination,
    subtitle_type,
):
    """
    Download either manually uploaded or automatic subtitles.

    Downloads subtitles only. No video or audio is downloaded.
    """
    if not languages:
        return

    destination.mkdir(parents=True, exist_ok=True)

    options = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,

        "writesubtitles": subtitle_type == "manual",
        "writeautomaticsub": subtitle_type == "automatic",

        "subtitleslangs": languages,
        "subtitlesformat": "vtt/best",

        "outtmpl": str(destination / "%(id)s.%(ext)s"),
        "overwrites": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([video_url])

    except Exception as error:
        log(
            f"Subtitle download issue "
            f"({subtitle_type}) for {video_id}: {error}"
        )


def find_downloaded_subtitles(folder, video_id):
    """
    Identify downloaded VTT files and their language codes.
    """
    results = []

    if not folder.exists():
        return results

    for path in folder.rglob("*.vtt"):
        stem = path.stem

        if not stem.startswith(video_id + "."):
            continue

        language_code = stem[len(video_id) + 1:]

        # yt-dlp can use -orig for one of the subtitle types.
        language_code = re.sub(
            r"-orig$",
            "",
            language_code,
            flags=re.IGNORECASE,
        )

        group = get_language_group(language_code)

        if group:
            results.append({
                "path": path,
                "language": language_code,
                "group": group,
            })

    return results


def select_best_subtitle(files, language):
    matching = [
        item for item in files
        if item["group"] == language
    ]

    if not matching:
        return None

    matching.sort(
        key=lambda item: get_language_rank(
            item["language"],
            language,
        )
    )

    return matching[0]["path"]


def download_missing_transcripts(video_id, video_url, metadata, video_dir):
    """
    Download missing English/Hindi transcripts.

    Existing raw_en.vtt and raw_hi.vtt files are never overwritten.
    Manual subtitles are preferred when available.
    """

    missing = []

    for language, filename in TARGET_LANGUAGES.items():
        target = video_dir / filename

        if not target.exists() or target.stat().st_size == 0:
            missing.append(language)

    if not missing:
        log("English and Hindi transcripts already exist. Skipping.")
        return

    manual_languages = get_available_languages(
        metadata,
        "subtitles",
    )

    automatic_languages = get_available_languages(
        metadata,
        "automatic_captions",
    )

    # Only request languages that are actually available.
    manual_languages = [
        code for code in manual_languages
        if get_language_group(code) in missing
    ]

    automatic_languages = [
        code for code in automatic_languages
        if get_language_group(code) in missing
    ]

    manual_dir = video_dir / "_temp_manual"
    automatic_dir = video_dir / "_temp_automatic"

    try:
        download_subtitle_type(
            video_id,
            video_url,
            manual_languages,
            manual_dir,
            "manual",
        )

        download_subtitle_type(
            video_id,
            video_url,
            automatic_languages,
            automatic_dir,
            "automatic",
        )

        manual_files = find_downloaded_subtitles(
            manual_dir,
            video_id,
        )

        automatic_files = find_downloaded_subtitles(
            automatic_dir,
            video_id,
        )

        for language, filename in TARGET_LANGUAGES.items():

            target = video_dir / filename

            # Never replace an existing transcript.
            if target.exists() and target.stat().st_size > 0:
                continue

            manual_file = select_best_subtitle(
                manual_files,
                language,
            )

            automatic_file = select_best_subtitle(
                automatic_files,
                language,
            )

            if PREFER_MANUAL_SUBTITLES:
                selected = manual_file or automatic_file
            else:
                selected = automatic_file or manual_file

            if selected:
                shutil.copy2(selected, target)

                source = (
                    "manual"
                    if selected == manual_file
                    else "automatic"
                )

                log(
                    f"Downloaded {language.upper()} "
                    f"({source}): {filename}"
                )

            else:
                log(
                    f"No {language.upper()} transcript "
                    f"available for {video_id}"
                )

    finally:
        # Temporary downloads are not needed after copying.
        shutil.rmtree(manual_dir, ignore_errors=True)
        shutil.rmtree(automatic_dir, ignore_errors=True)


# ============================================================
# PROCESS EACH VIDEO
# ============================================================

def process_video(entry, index, total):

    video_id = get_video_id(entry)

    if not video_id:
        log(f"Skipping entry {index}: no video ID.")
        return

    video_url = get_video_url(video_id)

    log("=" * 65)
    log(f"Processing {index}/{total}: {video_id}")

    try:
        metadata = fetch_video_metadata(video_url)

        if not metadata:
            log(f"Could not access video: {video_id}")
            return

        title = metadata.get("title", "Untitled")
        upload_date = metadata.get("upload_date")

        video_dir = make_video_folder(
            title,
            video_id,
            upload_date,
        )
        video_dir.mkdir(parents=True, exist_ok=True)

        # Keep only useful video metadata.
        saved_metadata = {
            "id": video_id,
            "title": title,
            "webpage_url": metadata.get(
                "webpage_url",
                video_url,
            ),
            "upload_date": upload_date,
            "duration": metadata.get("duration"),
            "description": metadata.get("description"),
            "language": metadata.get("language"),
            "transcripts": {},
            "last_checked": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        download_missing_transcripts(
            video_id,
            video_url,
            metadata,
            video_dir,
        )

        for language, filename in TARGET_LANGUAGES.items():
            transcript_path = video_dir / filename

            saved_metadata["transcripts"][language] = {
                "file": filename,
                "available": (
                    transcript_path.exists()
                    and transcript_path.stat().st_size > 0
                ),
            }

        metadata_path = video_dir / "metadata.json"
        save_json(metadata_path, saved_metadata)

        add_to_playlist_catalogue(saved_metadata)

        log(f"Completed: {title}")

    except Exception as error:
        log(f"ERROR processing {video_id}: {error}")


# ============================================================
# MAIN
# ============================================================

def main():

    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    initialise_playlist_file()

    # Process in the order returned by YouTube; your latest-first playlist order is preserved.
    entries = fetch_playlist()

    total = len(entries)

    if total == 0:
        log("No videos found.")
        return

    for index, entry in enumerate(entries, start=1):

        if not entry:
            continue

        process_video(entry, index, total)

    log("=" * 65)
    log("PLAYLIST TRANSCRIPT COLLECTION COMPLETED")
    log(f"Videos checked: {total}")
    log(f"Transcript folder: {VIDEOS_DIR}")
    log(f"Playlist catalogue: {PLAYLIST_FILE}")


if __name__ == "__main__":
    main()

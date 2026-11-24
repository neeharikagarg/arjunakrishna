
from pathlib import Path
from dataclasses import dataclass
import json
import re
import html
import sys

import yt_dlp
from fpdf import FPDF


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
VIDEOS_DIR = PROJECT_DIR / "videos"

OUTPUT_DIR = PROJECT_DIR / "collections" / "Arjuna_References"
OUTPUT_PDF = OUTPUT_DIR / "3_Janaka_References.pdf"

FONT_PATH = PROJECT_DIR / "fonts" / "Nirmala.ttf"

PLAYLIST_URL = (
    "https://www.youtube.com/playlist?list=PLAtNrs_fIyrw"
)

BEFORE_SECONDS = 45
AFTER_SECONDS = 75

# Search terms: candidate extraction only.
# Search terms: candidate extraction only.
# Direct Arjuna references
# Search terms: candidate extraction only.

# ENGLISH_PATTERN = re.compile(
#     r"\b(?:arjun|arjuna|arjoon|arjune|arjunaa|krishna|krishan|krishana|krushna|krsna|yogeshwar|yogeshwara|vasudeva|govinda|madhava|gopal)(?:'s)?\b",
#     re.IGNORECASE
# )

# HINDI_PATTERN = re.compile(
#     r"अर्जुन(?:ा|जी)?|कृष्ण|किशन|योगेश्वर|वासुदेव|गोविंद|गोविन्द|माधव|गोपाल"
# )

# Search terms: candidate extraction only.

ENGLISH_PATTERN = re.compile(
    r"\b(?:"
    # Action and non-doership
    r"without doing anything|"
    r"without doing|"
    r"everything gets done|"
    r"everything is done|"
    r"things get done|"
    r"you are not the doer|"
    r"not the doer|"
    r"non.doer|"
    r"doership|"
    r"without being the doer|"
    r"action without action|"
    r"spontaneous action|"

    # Action and its fruits
    r"fruit[s]? of (?:your )?action[s]?|"
    r"fruits of (?:your )?work|"
    r"result[s]? of (?:your )?action[s]?|"
    r"expect(?:ing|ation)? (?:the )?result[s]?|"
    r"without expectation[s]?|"
    r"without attachment|"
    r"non.attachment|"
    r"detachment|"
    r"selfless action|"
    r"desire for (?:the )?result[s]?|"
    r"karma yoga|"
    r"nishkama karma|"

    # Offering and surrender
    r"offer(?:ing|ed)? (?:your )?action[s]?|"
    r"surrender(?:ing)? (?:the )?result[s]?|"
    r"dedicat(?:e|ed|ing) (?:your )?work|"
    r"work as an offering|"

    # Self-realisation and inner freedom
    r"self.realized|"
    r"self.realised|"
    r"realized soul|"
    r"realised soul|"
    r"witness state|"
    r"state of witness|"
    r"inner freedom|"
    r"living in the world|"
    r"worldly life|"
    r"not attached to the world|"
    r"without withdrawing|"
    r"without renouncing|"
    r"janaka|"
    r"videha|"
    r"arjuna|"
    r"krishna|"
    r"yogeshwara|"
    r"yogeshwar"
    r")\b",
    re.IGNORECASE
)


HINDI_PATTERN = re.compile(
    r"अर्जुन(?:ा|जी)?|"
    r"कृष्ण|किशन|योगेश्वर|वासुदेव|गोविंद|गोविन्द|माधव|गोपाल|"
    r"जनक|विदेह|मिथिला नरेश|राजर्षि जनक|"
    r"बिना कुछ किए|"
    r"सब कुछ अपने आप|"
    r"अपने आप होता है|"
    r"निष्काम कर्म|"
    r"कर्मफल|"
    r"फल की इच्छा|"
    r"फल की अपेक्षा|"
    r"कर्म का फल|"
    r"फल की आशा|"
    r"आत्मसाक्षात्कार|"
    r"संसार में रहते हुए|"
    r"साक्षी भाव|"
    r"निर्लिप्त|"
    r"अकर्ता|"
    r"कर्तापन|"
    r"वैराग्य|"
    r"संन्यास"
)

TIMESTAMP_PATTERN = re.compile(
    r"(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{3})"
    r"\s*-->\s*"
    r"(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{3})"
)


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Cue:
    start: float
    end: float
    text: str


@dataclass
class Passage:
    start: float
    end: float
    cues: list


@dataclass
class Video:
    video_id: str
    title: str
    year: str
    url: str
    folder: Path
    metadata: dict


# ============================================================
# TIME HELPERS
# ============================================================

def timestamp_to_seconds(hours, minutes, seconds, milliseconds):

    hours = int(hours or 0)
    minutes = int(minutes)
    seconds = int(seconds)
    milliseconds = int(milliseconds)

    return (
        hours * 3600
        + minutes * 60
        + seconds
        + milliseconds / 1000
    )


def seconds_to_timestamp(value):

    value = max(0, int(value))

    hours = value // 3600
    minutes = (value % 3600) // 60
    seconds = value % 60

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


# ============================================================
# METADATA DISCOVERY
# ============================================================

def discover_local_videos():
    """
    Discover videos using metadata.json.
    Folder names do not need to match YouTube IDs.
    """

    videos = {}

    if not VIDEOS_DIR.exists():
        print(f"ERROR: Videos folder not found: {VIDEOS_DIR}")
        return videos

    folders = sorted(
        [p for p in VIDEOS_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.name.lower()
    )

    print(f"\nScanning {len(folders)} video folders...")

    for folder in folders:

        metadata_file = folder / "metadata.json"

        if not metadata_file.exists():
            print(f"SKIP: No metadata.json: {folder.name}")
            continue

        try:
            metadata = json.loads(
                metadata_file.read_text(encoding="utf-8")
            )

            video_id = metadata.get("id")

            if not video_id:
                print(f"SKIP: No video ID: {folder.name}")
                continue

            title = metadata.get("title", folder.name)

            upload_date = str(
                metadata.get("upload_date", "")
            )

            year = (
                upload_date[:4]
                if len(upload_date) >= 4
                else "Year unknown"
            )

            url = metadata.get(
                "webpage_url",
                f"https://www.youtube.com/watch?v={video_id}"
            )

            videos[video_id] = Video(
                video_id=video_id,
                title=title,
                year=year,
                url=url,
                folder=folder,
                metadata=metadata
            )

            print(f"FOUND: {title}")

        except Exception as exc:
            print(f"SKIP: Could not read {folder.name}: {exc}")

    return videos


# ============================================================
# PLAYLIST ORDER
# ============================================================

def get_playlist_order():

    print("\nReading YouTube playlist order...")

    options = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                PLAYLIST_URL,
                download=False
            )

        entries = info.get("entries", [])

        ordered_ids = [
            entry.get("id")
            for entry in entries
            if entry and entry.get("id")
        ]

        print(f"Playlist videos found: {len(ordered_ids)}")

        return ordered_ids

    except Exception as exc:
        print(f"WARNING: Playlist retrieval failed: {exc}")
        return []


def order_videos(local_videos, playlist_ids):

    ordered = []
    used = set()

    for video_id in playlist_ids:

        video = local_videos.get(video_id)

        if video and video_id not in used:
            ordered.append(video)
            used.add(video_id)

    # Add local videos missing from playlist results.
    remaining = [
        video
        for video_id, video in local_videos.items()
        if video_id not in used
    ]

    remaining.sort(
        key=lambda video: (
            video.year,
            video.folder.name.lower()
        )
    )

    ordered.extend(remaining)

    return ordered


# ============================================================
# VTT PARSING
# ============================================================

def clean_subtitle_text(text):

    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("\ufeff", "")

    return text.strip()


def parse_vtt(vtt_file):

    cues = []

    if not vtt_file or not vtt_file.exists():
        return cues

    content = vtt_file.read_text(
        encoding="utf-8-sig",
        errors="replace"
    )

    blocks = re.split(r"\n\s*\n", content)

    for block in blocks:

        lines = block.strip().splitlines()

        for index, line in enumerate(lines):

            match = TIMESTAMP_PATTERN.search(line)

            if not match:
                continue

            groups = match.groups()

            start = timestamp_to_seconds(
                groups[0],
                groups[1],
                groups[2],
                groups[3]
            )

            end = timestamp_to_seconds(
                groups[4],
                groups[5],
                groups[6],
                groups[7]
            )

            text_lines = lines[index + 1:]

            cleaned_lines = [
                clean_subtitle_text(line)
                for line in text_lines
            ]

            text = " ".join(
                line
                for line in cleaned_lines
                if line
            )

            if text:
                cues.append(
                    Cue(
                        start=start,
                        end=end,
                        text=text
                    )
                )

            break

    cues.sort(key=lambda cue: cue.start)

    return cues


# ============================================================
# TRANSCRIPT FILE DISCOVERY
# ============================================================

def get_transcript_file(video, language):

    transcript_info = (
        video.metadata.get("transcripts", {})
        .get(language, {})
    )

    filename = transcript_info.get("file")

    if filename:
        candidate = video.folder / filename

        if candidate.exists():
            return candidate

    fallback = video.folder / f"raw_{language}.vtt"

    if fallback.exists():
        return fallback

    return None


# ============================================================
# MATCHING AND CONTEXT EXTRACTION
# ============================================================

def find_passages(cues, language):

    if not cues:
        return []

    pattern = (
        ENGLISH_PATTERN
        if language == "en"
        else HINDI_PATTERN
    )

    matched_indices = [
        index
        for index, cue in enumerate(cues)
        if pattern.search(cue.text)
    ]

    if not matched_indices:
        return []

    windows = []

    for index in matched_indices:

        match_cue = cues[index]

        window_start = max(
            0,
            match_cue.start - BEFORE_SECONDS
        )

        window_end = match_cue.end + AFTER_SECONDS

        selected = [
            cue
            for cue in cues
            if cue.end >= window_start
            and cue.start <= window_end
        ]

        if selected:
            windows.append(
                Passage(
                    start=selected[0].start,
                    end=selected[-1].end,
                    cues=selected
                )
            )

    # Merge overlapping or nearby passages.
    merged = []

    for passage in windows:

        if not merged:
            merged.append(passage)
            continue

        previous = merged[-1]

        if passage.start <= previous.end + 5:

            previous.end = max(
                previous.end,
                passage.end
            )

            existing = {
                (cue.start, cue.end, cue.text)
                for cue in previous.cues
            }

            for cue in passage.cues:

                key = (
                    cue.start,
                    cue.end,
                    cue.text
                )

                if key not in existing:
                    previous.cues.append(cue)
                    existing.add(key)

            previous.cues.sort(
                key=lambda cue: cue.start
            )

        else:
            merged.append(passage)

    return merged


# ============================================================
# PARAGRAPH FORMATTING
# ============================================================

def format_passage_paragraphs(passage):

    paragraphs = []

    current_lines = []
    current_start = None
    previous_end = None

    for cue in passage.cues:

        if (
            previous_end is not None
            and cue.start - previous_end > 2.0
            and current_lines
        ):

            paragraphs.append(
                (
                    current_start,
                    previous_end,
                    " ".join(current_lines)
                )
            )

            current_lines = []
            current_start = None

        if current_start is None:
            current_start = cue.start

        current_lines.append(cue.text)
        previous_end = cue.end

    if current_lines:
        paragraphs.append(
            (
                current_start,
                previous_end,
                " ".join(current_lines)
            )
        )

    return paragraphs


# ============================================================
# PDF GENERATION
# ============================================================

class ArjunaPDF(FPDF):

    def header(self):

        if self.page_no() > 1:

            self.set_font(
                "Transcript",
                size=9
            )

            self.set_text_color(120, 120, 120)

            self.set_x(self.l_margin)

            self.cell(
                0,
                7,
                "Arjuna References",
                align="R"
            )

            self.ln(8)

            self.set_text_color(0, 0, 0)

    def footer(self):

        self.set_y(-15)

        self.set_font(
            "Transcript",
            size=8
        )

        self.set_text_color(120, 120, 120)

        self.set_x(self.l_margin)

        self.cell(
            0,
            10,
            f"Page {self.page_no()}",
            align="C"
        )

        self.set_text_color(0, 0, 0)


# ============================================================
# FONT REGISTRATION
# ============================================================

def add_pdf_font(pdf):

    if not FONT_PATH.exists():

        raise FileNotFoundError(
            f"Hindi font not found: {FONT_PATH}\n"
            "Extract Nirmala.ttc into fonts/Nirmala.ttf first."
        )

    try:

        pdf.add_font(
            "Transcript",
            fname=str(FONT_PATH)
        )

        pdf.add_font(
            "Transcript",
            style="B",
            fname=str(FONT_PATH)
        )

        pdf.set_text_shaping(
            use_shaping_engine=True
        )

    except Exception as exc:

        raise RuntimeError(
            f"Could not load Hindi font: {FONT_PATH}\n"
            "Check fpdf2 and uharfbuzz installation."
        ) from exc


# ============================================================
# SAFE PDF TEXT OUTPUT
# ============================================================

def safe_multi_cell(pdf, text, height=6, align="L"):
    """
    Always reset the cursor to the left margin and
    use the full available page width.

    This prevents FPDF's horizontal-space error.
    """

    pdf.set_x(pdf.l_margin)

    available_width = (
        pdf.w - pdf.l_margin - pdf.r_margin
    )

    pdf.multi_cell(
        available_width,
        height,
        str(text),
        align=align
    )


# ============================================================
# PDF CONTENT
# ============================================================

def create_pdf(videos):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pdf = ArjunaPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=18
    )

    pdf.set_margins(
        18, 18, 18
    )

    add_pdf_font(pdf)

    pdf.add_page()

    # --------------------------------------------------------
    # COVER PAGE
    # --------------------------------------------------------

    pdf.set_font(
        "Transcript",
        style="B",
        size=23
    )

    pdf.ln(35)

    safe_multi_cell(
        pdf,
        "Arjuna References",
        height=14,
        align="C"
    )

    pdf.ln(8)

    pdf.set_font(
        "Transcript",
        size=13
    )

    safe_multi_cell(
        pdf,
        "Mother's Teaching",
        height=9,
        align="C"
    )

    pdf.ln(12)

    pdf.set_font(
        "Transcript",
        size=10
    )

    safe_multi_cell(
        pdf,
        "Transcript passages from the supplied video collection.",
        height=7,
        align="C"
    )

    pdf.add_page()

    # --------------------------------------------------------
    # PROCESS VIDEOS
    # --------------------------------------------------------

    total_passages = 0
    total_videos = 0

    for video in videos:

        video_sections = []

        for language in ("en", "hi"):

            vtt_file = get_transcript_file(
                video,
                language
            )

            if not vtt_file:
                continue

            cues = parse_vtt(vtt_file)

            passages = find_passages(
                cues,
                language
            )

            if passages:
                video_sections.append(
                    (language, passages)
                )

        if not video_sections:

            print(f"NO MATCH: {video.title}")
            continue

        total_videos += 1

        for language, passages in video_sections:

            for passage in passages:

                total_passages += 1

                pdf.ln(5)

                # Video title
                pdf.set_font(
                    "Transcript",
                    style="B",
                    size=13
                )

                safe_multi_cell(
                    pdf,
                    video.title,
                    height=8
                )

                # Video information
                pdf.set_font(
                    "Transcript",
                    size=9
                )

                safe_multi_cell(
                    pdf,
                    f"Upload year: {video.year}"
                )

                language_name = (
                    "English"
                    if language == "en"
                    else "Hindi"
                )

                safe_multi_cell(
                    pdf,
                    f"Language: {language_name}"
                )

                timestamp_range = (
                    f"{seconds_to_timestamp(passage.start)}"
                    f" - "
                    f"{seconds_to_timestamp(passage.end)}"
                )

                safe_multi_cell(
                    pdf,
                    f"Timestamp: {timestamp_range}"
                )

                # Clickable YouTube link
                pdf.set_text_color(0, 0, 150)

                pdf.set_font(
                    "Transcript",
                    size=9
                )

                pdf.set_x(pdf.l_margin)

                pdf.write(
                    6,
                    "Watch video",
                    link=video.url
                )

                pdf.set_text_color(0, 0, 0)

                pdf.ln(8)

                # Section heading
                pdf.set_font(
                    "Transcript",
                    style="B",
                    size=12
                )

                safe_multi_cell(
                    pdf,
                    "Mother's Teaching",
                    height=7
                )

                pdf.ln(2)

                paragraphs = format_passage_paragraphs(
                    passage
                )

                for start, end, text in paragraphs:

                    timestamp = (
                        f"[{seconds_to_timestamp(start)}]"
                    )

                    # Paragraph timestamp
                    pdf.set_font(
                        "Transcript",
                        style="B",
                        size=9
                    )

                    safe_multi_cell(
                        pdf,
                        timestamp
                    )

                    # Original transcript wording
                    pdf.set_font(
                        "Transcript",
                        size=10
                    )

                    safe_multi_cell(
                        pdf,
                        text
                    )

                    pdf.ln(2)

            pdf.ln(5)

        print(f"PROCESSED: {video.title}")

    # --------------------------------------------------------
    # SAVE PDF
    # --------------------------------------------------------

    if total_passages == 0:

        print("\nNo Arjuna references found.")
        return

    pdf.output(
        str(OUTPUT_PDF)
    )

    print("\n========================================")
    print("COMPLETED")
    print("========================================")

    print(
        f"Videos with matches: {total_videos}"
    )

    print(
        f"Passages extracted: {total_passages}"
    )

    print(
        f"PDF: {OUTPUT_PDF}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("ARJUNA REFERENCES")
    print("=================")

    local_videos = discover_local_videos()

    if not local_videos:

        print("\nNo valid video metadata found.")
        return

    playlist_ids = get_playlist_order()

    videos = order_videos(
        local_videos,
        playlist_ids
    )

    print(
        f"\nVideos ready for processing: {len(videos)}"
    )

    create_pdf(videos)


if __name__ == "__main__":

    try:
        main()

    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


import subprocess
from pathlib import Path

#INPUT = Path("Karma_Correct_Original.mp4")
INPUT = Path("Karma_Becomes_Akarma_Final.mp4")
OUTPUT= Path("Karma_Becomes_Akarma_Final_Restored.mp4")

if not INPUT.exists():
    raise FileNotFoundError(f"Missing source video: {INPUT}")

# Check original aspect ratio before choosing output dimensions.
probe = subprocess.run(
    [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        str(INPUT)
    ],
    capture_output=True,
    text=True,
    check=True
)

width, height = map(int, probe.stdout.strip().split("x"))

# Preserve original proportions; upscale to 1080 pixels wide.
output_width = 1080
output_height = round(height * output_width / width)
output_height += output_height % 2


video_filter = (
    "hqdn3d=1.0:1.0:2:2,"
    "deblock=filter=weak:block=8,"
    "cas=0.7,"
    "unsharp=7:7:0.65:5:5:0.25,"
    "eq=contrast=1.06:brightness=0.004:"
    "saturation=1.10:gamma=1.02,"
    f"scale={output_width}:{output_height}:flags=lanczos,"
    "setsar=1"
)



command = [
    "ffmpeg", "-y",
    "-i", str(INPUT),
    "-map", "0:v:0",
    "-map", "0:a:0?",
    "-vf", video_filter,
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "17",
    "-pix_fmt", "yuv420p",
    "-c:a", "copy",
    "-movflags", "+faststart",
    str(OUTPUT)
]

print("Restoring the correct archival clip...")
print(f"Source resolution: {width} x {height}")
print(f"Output resolution: {output_width} x {output_height}")
print("Audio: original stream copied unchanged")

subprocess.run(command, check=True)

print("\nRestoration complete!")
print(f"Output: {OUTPUT.resolve()}")

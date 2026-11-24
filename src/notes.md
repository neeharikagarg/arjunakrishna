
Step 1 — Download the correct section
In your existing PowerShell terminal, run:
(22:26-23:14)  https://www.youtube.com/watch?v=8VLxwa1ZevI


python -m yt_dlp --download-sections "*00:22:26-00:23:14" --force-keyframes-at-cuts -f "bv*+ba/b" --merge-output-format mp4 "https://www.youtube.com/watch?v=8VLxwa1ZevI" -o "Karma_Correct_Original.%(ext)s"


Step 2. python src\restore_karma_clip.py
"""
The app's name, in ONE place. Renaming the app = change APP_NAME here.
Used by: the page title and header (app.py), the footer (strings.py "footer" via app.py),
the slide footer (slides.py), the notes PDF footer (transcript_export.py) and download
file names.
"""
import re

APP_NAME = "AcademicVid"

# Download file names, e.g. "academicvid_lesson.mp4". Safe characters only.
FILE_PREFIX = re.sub(r"[^a-z0-9]+", "_", APP_NAME.lower()).strip("_") or "lesson"

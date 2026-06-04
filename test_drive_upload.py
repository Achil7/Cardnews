from pathlib import Path
from config import PROJECT_ROOT
from src.uploader.drive import upload_post_to_drive

test_dir = PROJECT_ROOT / "data" / "output" / "test_upload" / "post_1"
test_dir.mkdir(parents=True, exist_ok=True)

(test_dir / "test_slide.txt").write_text("Google Drive upload test", encoding="utf-8")
print(f"Test file created: {test_dir}")

url = upload_post_to_drive(test_dir)
print(f"Result: {url}")

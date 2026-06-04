from src.notifier.telegram import send_telegram_notification

result = send_telegram_notification(
    date="2026-06-04",
    total=2,
    success=2,
    failed=0,
    drive_url="https://drive.google.com/drive/folders/1XgQdvvn-_669nkPGraOkKR1yxknKcQbt",
)
print(f"Sent: {result}")

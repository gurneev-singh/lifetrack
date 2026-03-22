from core.config import APP_CATEGORIES

def classify_window(window_title: str, app_name: str) -> str:
    if not window_title and not app_name:
        return "unknown"
    combined = f"{window_title} {app_name}".lower()
    for keyword, category in APP_CATEGORIES.items():
        if keyword in combined:
            return category
    return "unknown"

def classify_url(url: str) -> str:
    if not url:
        return "unknown"
    for keyword, category in APP_CATEGORIES.items():
        if keyword in url.lower():
            return category
    return "unknown"

def get_app_name_from_window(window_title: str) -> str:
    if not window_title:
        return "Unknown"
    for sep in [" - ", " | ", " - "]:
        if sep in window_title:
            parts = window_title.split(sep)
            return parts[-1].strip()
    return window_title[:30]

import re
import json
import os

def strip_markdown(text):
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("/", " or ").replace("#", "").replace("*", "")
    text = re.sub(r"_+", " ", text)
    text = text.replace("&", " and ").replace("~", "").replace("|", "").replace("\\", "")
    text = re.sub(r"  +", " ", text)
    return text.strip()

def load_interviews():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "interviews.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["interviews"]

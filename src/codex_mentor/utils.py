"""Các hàm tiện ích thuần Python, xử lý chuỗi, định dạng diff và tệp tin."""
from __future__ import annotations

import difflib
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

FENCE = "`" * 3
_FENCE_RE = re.compile(r"`{3}[^\n`]*\n(.*?)`{3}", re.DOTALL)
MAX_FILE_BYTES = 250_000

LANGUAGES: Dict[str, Tuple[str, str]] = {
    "python": ("Python", ".py"),
    "javascript": ("JavaScript", ".js"),
    "typescript": ("TypeScript", ".ts"),
    "java": ("Java", ".java"),
    "go": ("Go", ".go"),
    "rust": ("Rust", ".rs"),
    "csharp": ("C#", ".cs"),
    "cpp": ("C++", ".cpp"),
    "c": ("C", ".c"),
    "php": ("PHP", ".php"),
    "ruby": ("Ruby", ".rb"),
    "kotlin": ("Kotlin", ".kt"),
    "swift": ("Swift", ".swift"),
    "sql": ("SQL", ".sql"),
}

EXT_TO_KEY = {ext: key for key, (_, ext) in LANGUAGES.items()}
EXT_TO_KEY.update({
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "c",
    ".cs": "csharp",
})

ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "c#": "csharp",
    "cs": "csharp",
    "c++": "cpp",
    "golang": "go",
    "rb": "ruby",
    "kt": "kotlin",
}


class CLIError(Exception):
    """Lỗi nghiệp vụ hiển thị thân thiện trên terminal, không in Traceback của CLI."""
    pass


def read_source(path: Path) -> str:
    """Đọc tệp tin với các kiểm tra an toàn."""
    if not path.exists():
        raise CLIError(f"Không tìm thấy tệp: {path}")
    if not path.is_file():
        raise CLIError(f"Đường dẫn không phải là một tệp hợp lệ: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise CLIError(f"Tệp quá lớn (> {MAX_FILE_BYTES / 1000} KB). Vui lòng chọn tệp nhỏ hơn hoặc lọc dòng.")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise CLIError(f"Tệp {path} không đúng định dạng UTF-8.")


def detect_language(path: Path) -> str:
    """Nhận diện tên ngôn ngữ lập trình dựa trên phần mở rộng tệp."""
    key = EXT_TO_KEY.get(path.suffix.lower())
    return LANGUAGES[key][0] if key else "Unknown"


def normalize_target_lang(name: str) -> Optional[Tuple[str, str, str]]:
    """Chuẩn hóa ngôn ngữ đích, trả về (key, display_name, extension)."""
    clean_name = name.strip().lower()
    key = ALIASES.get(clean_name, clean_name)
    if key in LANGUAGES:
        disp_name, ext = LANGUAGES[key]
        return key, disp_name, ext
    return None


def add_line_numbers(code: str, start: int = 1) -> str:
    """Đánh số dòng cho mã nguồn."""
    lines = code.splitlines()
    total_lines = start + max(len(lines) - 1, 0)
    width = len(str(total_lines))
    return "\n".join(f"{i:>{width}} | {line}" for i, line in enumerate(lines, start=start))


def parse_line_range(text: str) -> Tuple[int, int]:
    """Phân tích chuỗi khoảng dòng (ví dụ: '10-30' hoặc '15')."""
    match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", text or "")
    if not match:
        raise CLIError("Cú pháp --lines không hợp lệ. Ví dụ đúng: --lines 10-25 hoặc --lines 15")
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else start
    if start < 1 or end < start:
        raise CLIError("Khoảng dòng không hợp lệ: số dòng phải >= 1 và dòng bắt đầu <= dòng kết thúc.")
    return start, end


def extract_json(raw_text: str) -> dict:
    """Trích xuất JSON Object an toàn ngay cả khi mô hình bọc trong markdown code fence."""
    cleaned = raw_text.strip()
    candidates: List[str] = [cleaned]

    fenced = _FENCE_RE.search(cleaned)
    if fenced:
        candidates.append(fenced.group(1).strip())

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        candidates.append(cleaned[start:end + 1])

    for cand in candidates:
        try:
            val = json.loads(cand)
            if isinstance(val, dict):
                return val
        except json.JSONDecodeError:
            continue

    raise ValueError("Phản hồi từ OpenAI không chứa JSON Object hợp lệ.")


def split_code_and_notes(text: str) -> Tuple[str, str]:
    """Tách khối code và phần ghi chú phía sau nếu có."""
    match = _FENCE_RE.search(text)
    if not match:
        return text.strip("\n"), ""
    return match.group(1).rstrip("\n"), text[match.end():].strip()


def make_diff(original: str, revised: str, filename: str) -> str:
    """Tạo unified diff tiêu chuẩn so sánh bản gốc và bản sửa."""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        revised.splitlines(keepends=True),
        fromfile=f"a/{filename} (Bản gốc)",
        tofile=f"b/{filename} (Đã sửa bởi Codex Mentor)",
        lineterm="",
    )
    return "".join(diff)


def backup_and_write(path: Path, new_code: str) -> Path:
    """Sao lưu tệp gốc thành .bak trước khi ghi đè bản sửa lỗi."""
    backup_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup_path)
    clean_code = new_code if new_code.endswith("\n") else new_code + "\n"
    path.write_text(clean_code, encoding="utf-8")
    return backup_path

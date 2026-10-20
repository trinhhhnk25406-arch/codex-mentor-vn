import pytest
from codex_mentor.utils import (
    CLIError,
    add_line_numbers,
    extract_json,
    make_diff,
    normalize_target_lang,
    parse_line_range,
    split_code_and_notes,
)


def test_extract_json_valid():
    assert extract_json('{"status": "ok", "code": 200}') == {"status": "ok", "code": 200}


def test_extract_json_markdown_wrapped():
    raw = "Phản hồi từ AI:\n```json\n{\"fixed\": true}\n```\nKết thúc."
    assert extract_json(raw) == {"fixed": True}


def test_extract_json_invalid():
    with pytest.raises(ValueError):
        extract_json("Văn bản này hoàn toàn không có JSON hợp lệ.")


def test_split_code_and_notes():
    text = "```python\nprint('hello')\n```\n## Lưu ý\nNhớ cài thư viện."
    code, notes = split_code_and_notes(text)
    assert code == "print('hello')"
    assert notes.startswith("## Lưu ý")


def test_make_diff():
    old = "x = 1\ny = 2\n"
    new = "x = 1\ny = 3\n"
    diff = make_diff(old, new, "test.py")
    assert "-y = 2" in diff
    assert "+y = 3" in diff


def test_parse_line_range():
    assert parse_line_range("10-25") == (10, 25)
    assert parse_line_range("15") == (15, 15)
    with pytest.raises(CLIError):
        parse_line_range("30-10")
    with pytest.raises(CLIError):
        parse_line_range("abc")


def test_add_line_numbers():
    code = "line1\nline2"
    numbered = add_line_numbers(code, start=1)
    assert "1 | line1" in numbered
    assert "2 | line2" in numbered


def test_normalize_target_lang():
    assert normalize_target_lang("ts") == ("typescript", "TypeScript", ".ts")
    assert normalize_target_lang("Golang") == ("go", "Go", ".go")
    assert normalize_target_lang("unknown_lang") is None

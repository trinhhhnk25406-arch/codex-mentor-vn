"""System Prompts và hàm xây dựng Prompt ngữ cảnh chuẩn tiếng Việt."""
from __future__ import annotations

from typing import List
from .utils import FENCE

SYSTEM_BASE = (
    "Bạn là Codex Mentor VN — Kỹ sư Phần mềm Cao cấp kiêm Cố vấn Lập trình tận tâm. "
    "Mục tiêu của bạn là giúp lập trình viên và sinh viên Việt Nam hiểu sâu bản chất code, "
    "sửa lỗi triệt để và viết mã nguồn chuẩn Idiomatic.\n"
    "Quy tắc cốt lõi:\n"
    "1. Luôn phản hồi bằng tiếng Việt tự nhiên, chuẩn mực.\n"
    "2. Giữ nguyên thuật ngữ kỹ thuật tiếng Anh cốt lõi (ví dụ: Deadlock, Mutability, Indexing, "
    "Traceback, Type Hinting...) nhưng luôn kèm giải thích ngắn gọn.\n"
    "3. Không sinh mã nguồn giả (pseudo-code) hay bỏ dở bằng dấu '...'. Mã nguồn sinh ra phải chạy được ngay."
)

LEVEL_HINTS = {
    "newbie": "Người mới học lập trình hoàn toàn: giải thích cặn kẽ từng bước, dùng ẩn dụ đời thường dễ nhớ.",
    "intermediate": "Sinh viên CNTT / Junior Developer: tập trung cấu trúc dữ liệu, luồng điều khiển và Clean Code.",
    "advanced": "Kỹ sư phần mềm: phân tích sâu kiến trúc, hiệu năng, quản lý bộ nhớ và độ phức tạp Big-O.",
}


def build_explain_prompt(filename: str, language: str, code_with_lines: str, level: str) -> str:
    return f"""Hãy phân tích và giải thích đoạn mã nguồn ({language}) dưới đây.
Đối tượng độc giả: {LEVEL_HINTS.get(level, level)}
Tên tệp: {filename}

Mã nguồn (kèm số dòng):
{FENCE}
{code_with_lines}
{FENCE}

Trình bày theo định dạng Markdown chuẩn gồm 4 phần rõ ràng:
## 🎯 1. Mục Đích & Hoạt Động Tổng Quan
## 🔍 2. Phân Tích Chi Tiết Từng Cụm Dòng
(Trích dẫn chính xác số dòng, ví dụ: "Dòng 3-5: ...")
## 📊 3. Đánh Giá Độ Phức Tạp Thuật Toán (Big-O)
- Thời gian (Time Complexity): ...
- Không gian bộ nhớ (Space Complexity): ...
## 💡 4. Khuyến Nghị Tối Ưu & Lưu Ý Biên (Edge Cases)
"""


def build_fix_prompt(filename: str, language: str, code: str, error_text: str, history: List[dict]) -> str:
    history_str = ""
    if history:
        items = []
        for h in history:
            items.append(f"- Lần thử {h['attempt']}: Bản sửa vẫn sinh lỗi -> {h['error'][-300:]}")
        history_str = "\nCác lần sửa trước ĐÃ THẤT BẠI, hãy tránh lặp lại cùng sai lầm:\n" + "\n".join(items)

    return f"""Chẩn đoán nguyên nhân gốc rễ và sửa lỗi cho tệp mã nguồn sau:
Tệp: {filename} | Ngôn ngữ: {language}

MÃ NGUỒN HIỆN TẠI:
{FENCE}
{code}
{FENCE}

THÔNG TIN LỖI / TRACEBACK:
{FENCE}
{error_text}
{FENCE}
{history_str}

BẮT BUỘC trả về DUY NHẤT một JSON Object hợp lệ (không kèm markdown ngoài) theo cấu trúc sau:
{{
  "error_type": "Tên loại lỗi (ví dụ: ZeroDivisionError, IndexError)",
  "root_cause_vi": "Giải thích nguyên nhân cốt lõi tại sao phát sinh lỗi này",
  "fix_explanation_vi": "Giải thích ngắn gọn cách đã khắc phục",
  "fixed_code": "Toàn bộ mã nguồn hoàn chỉnh sau khi sửa, KHÔNG đánh số dòng, chạy được ngay",
  "changes_summary": ["Mô tả thay đổi 1", "Mô tả thay đổi 2"],
  "prevention_tip": "Lời khuyên thực tế giúp tránh gặp lại lỗi này"
}}
"""


def build_convert_prompt(filename: str, source_lang: str, target_lang: str, code: str) -> str:
    return f"""Chuyển đổi mã nguồn từ {source_lang} sang {target_lang}.
Tệp gốc: {filename}

Yêu cầu nghiêm ngặt:
1. Viết mã nguồn theo đúng chuẩn Idiomatic và Best Practices của {target_lang}.
2. Giữ nguyên thuật toán, bổ sung xử lý lỗi an toàn.
3. Đặt toàn bộ mã nguồn chuyển đổi trong DUY NHẤT một khối code markdown.
4. Phía sau khối code, viết mục '## 📌 Ghi Chú Chuyển Đổi' bằng tiếng Việt nêu rõ các khác biệt cú pháp hoặc thư viện.

MÃ NGUỒN GỐC ({source_lang}):
{FENCE}
{code}
{FENCE}
"""


def build_test_prompt(filename: str, language: str, code: str, framework: str) -> str:
    return f"""Hãy tạo bộ Unit Test hoàn chỉnh cho tệp {filename} ({language}) sử dụng framework: {framework}.
Yêu cầu bao phủ:
1. Happy Paths (kịch bản chuẩn hoạt động đúng).
2. Edge Cases (giá trị rỗng, số 0, số âm, giá trị cực đại, kiểu dữ liệu bất thường).
3. Exception Handling (kiểm tra các trường hợp bắt buộc ném ngoại lệ).

Trả về DUY NHẤT một JSON Object theo cấu trúc sau:
{{
  "framework": "{framework}",
  "scenarios": ["Kịch bản test 1", "Kịch bản test 2", "Kịch bản test 3"],
  "test_code": "Toàn bộ mã nguồn tệp test hoàn chỉnh có thể chạy được ngay",
  "run_command": "Câu lệnh terminal để chạy bộ test này"
}}

MÃ NGUỒN CẦN TEST:
{FENCE}
{code}
{FENCE}
"""

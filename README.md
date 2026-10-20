# 🧑‍💻 Codex Mentor VN — Trợ Lý AI Phân Tích, Tự Sửa Lỗi & Chuyển Đổi Code

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![OpenAI](https://img.shields.io/badge/Powered%20by-OpenAI%20API%20(GPT--4o%20%2F%20o3--mini)-412991?style=flat&logo=openai&logoColor=white)](https://openai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Clean Architecture](https://img.shields.io/badge/Architecture-Clean%20%26%20Modular-brightgreen)](#)

> **Codex Mentor VN** là công cụ dòng lệnh (CLI) mã nguồn mở đóng vai trò như một **Senior Software Engineer & Cố vấn Lập trình kỹ thuật** bằng tiếng Việt. Dự án được thiết kế chuyên biệt để giúp sinh viên Công nghệ Thông tin và lập trình viên vượt qua hai rào cản lớn nhất: **thông báo lỗi tiếng Anh mơ hồ** và **sự lúng túng khi debug những ca lỗi phức tạp**.

---

## 💡 Điểm Nhấn Kỹ Thuật (Engineering Highlights)

Thay vì chỉ gọi OpenAI API để "đoán" bản vá mã nguồn một cách thụ động, Codex Mentor VN xây dựng cơ chế **Closed-Loop Agentic Self-Healing**:

```text
[Tệp nguồn bị lỗi]
       │
       ▼
 [1. Tự chạy tệp] ──(Lỗi Runtime)──► [2. Trích xuất Traceback thực tế]
                                                     │
                                                     ▼
 [5. Hiển thị Diff &] ◄──(Chạy thành công)── [4. Chạy kiểm chứng] ◄── [3. AI đề xuất bản vá]
 [Lưu dự phòng .bak ]                              │                          ▲
                                            (Vẫn còn lỗi)                     │
                                                   └──── Đệ quy gửi lỗi mới ──┘
                                                          (Thử tối đa 5 lần)
```

1. **Vòng lặp tự động sửa lỗi & kiểm chứng (Self-Correction Loop)**: Tự động chạy tệp trong tiến trình con (subprocess), bắt Traceback thực tế, gửi tới OpenAI và **thực thi kiểm chứng bản vá trong môi trường sandbox tạm thời**. Nếu bản sửa vẫn còn lỗi, công cụ sẽ ghi nhận lịch sử và tiếp tục yêu cầu AI sửa lại cho đến khi chương trình chạy thành công.
2. **Kiến trúc module chuẩn mực (`src/` layout)**: Tách bạch rõ rệt giữa CLI Controller, API Client, Sandbox Runner và Tiện ích xử lý chuỗi.
3. **An toàn dữ liệu tuyệt đối**: Không bao giờ ghi đè file bừa bãi. Luôn hiển thị bảng so sánh **Unified Diff**, tạo bản sao lưu `.bak` tự động và yêu cầu người dùng xác nhận tương tác.
4. **Bộ kiểm thử tự động (Unit Test Suite)**: Tích hợp đầy đủ các bài test qua `pytest` kiểm tra logic runner và sandbox mà không tiêu tốn token API.

---

## ✨ Các Tính Năng Cốt Lõi

| Lệnh | Tính năng | Mô tả chi tiết |
| :--- | :--- | :--- |
| `explain` | **Giải thích code & Big-O** | Phân tích chức năng theo 3 cấp độ (`newbie`, `intermediate`, `advanced`), trích dẫn cụm dòng chính xác, tính toán độ phức tạp thuật toán Big-O (Time & Space) và hỗ trợ Streaming thời gian thực. |
| `fix` | **Tự động bắt lỗi & Vá code** | Chạy file để bắt lỗi runtime, phân tích nguyên nhân gốc rễ (Root Cause Analysis), chạy lặp kiểm chứng và tạo bản vá Diff trực quan. |
| `convert` | **Chuyển đổi đa ngôn ngữ** | Chuyển đổi mã nguồn giữa Python, TypeScript, JavaScript, Go, Rust, Java, C++, C#... theo đúng chuẩn **Idiomatic** của ngôn ngữ đích kèm tài liệu lưu ý kỹ thuật. |
| `test` | **Tự động sinh Unit Test** | Phân tích luồng nghiệp vụ để sinh bộ test tự động (`pytest`, `unittest`, `jest`), bao phủ đầy đủ Happy Paths, Edge Cases và Exception Handling. |

---

## ⚙️ Hướng Dẫn Cài Đặt (Installation)

### 1. Yêu cầu tiên quyết
- **Python**: Phiên bản 3.9 trở lên.
- **OpenAI API Key**: Đăng ký tại [OpenAI Platform](https://platform.openai.com/api-keys).

### 2. Cài đặt từ mã nguồn
```bash
# 1. Clone kho lưu trữ
git clone https://github.com/<your-username>/codex-mentor-vn.git
cd codex-mentor-vn

# 2. Khởi tạo môi trường ảo
python -m venv .venv

# Kích hoạt trên macOS/Linux:
source .venv/bin/activate
# Kích hoạt trên Windows:
.venv\Scripts\activate

# 3. Cài đặt gói ở chế độ Editable kèm thư viện dev
pip install -e ".[dev]"
```

### 3. Cấu hình biến môi trường
Sao chép tệp mẫu `.env.example` thành `.env` và điền OpenAI API Key:
```bash
cp .env.example .env     # Trên Windows: copy .env.example .env
```
Nội dung `.env`:
```ini
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
CODEX_MODEL=gpt-4o
```

---

## 💻 Hướng Dẫn Sử Dụng (Usage)

Kiểm tra cài đặt:
```bash
codex-mentor --help
```

### 1. Giải thích mã nguồn (`explain`)
```bash
# Giải thích trực quan dễ hiểu cho người mới học
codex-mentor explain examples/bug_index_error.py --level newbie

# Giải thích đoạn code từ dòng 10 đến 35 cho kỹ sư chuyên sâu
codex-mentor explain src/codex_mentor/runner.py --lines 10-35 --level advanced
```

### 2. Tự động sửa lỗi có kiểm chứng (`fix`)
```bash
# Tự chạy tệp, bắt Traceback, sửa và kiểm chứng tự động
codex-mentor fix examples/bug_zero_division.py

# Tự động ghi đè bản vá (bản gốc lưu thành .bak), cho phép thử tối đa 4 lần
codex-mentor fix examples/bug_type_error.py -y --max-attempts 4

# Truyền thông báo lỗi thủ công (với lỗi logic hoặc ngôn ngữ khác Python)
codex-mentor fix main.js --error "TypeError: Cannot read properties of undefined"
```

### 3. Chuyển đổi ngôn ngữ chuẩn Idiomatic (`convert`)
```bash
# Chuyển đổi mã nguồn Python sang TypeScript
codex-mentor convert examples/bug_index_error.py --to TypeScript

# Chuyển đổi sang Go và xuất ra file mới
codex-mentor convert logic.py --to Go -o logic.go --force
```

### 4. Tự động sinh Unit Test (`test`)
```bash
# Tự động sinh test case pytest cho tệp mã nguồn
codex-mentor test src/codex_mentor/utils.py -o tests/test_utils_generated.py
```

---

## 🧪 Kiểm Thử Tự Động (Automated Testing)

Toàn bộ test suite được viết bằng `pytest`, có thể chạy độc lập ngoại tuyến mà không yêu cầu kết nối API:
```bash
pytest
```

---

## 📄 Giấy Phép (License)
Dự án được phân phối dưới giấy phép **MIT License** — hoàn toàn tự do sử dụng và đóng góp cho cộng đồng lập trình Việt Nam.

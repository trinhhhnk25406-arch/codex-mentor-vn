from codex_mentor.runner import run_candidate_source, run_python_file


def test_run_python_file_success(tmp_path):
    f = tmp_path / "valid.py"
    f.write_text("print('Xin chao')", encoding="utf-8")
    res = run_python_file(f)
    assert res.ok
    assert "Xin chao" in res.stdout


def test_run_python_file_error(tmp_path):
    f = tmp_path / "bug.py"
    f.write_text("print(10 / 0)", encoding="utf-8")
    res = run_python_file(f)
    assert not res.ok
    assert "ZeroDivisionError" in res.error_text


def test_run_python_file_timeout(tmp_path):
    f = tmp_path / "loop.py"
    f.write_text("while True: pass", encoding="utf-8")
    res = run_python_file(f, timeout=1)
    assert res.timed_out
    assert not res.ok


def test_run_candidate_source_sandbox(tmp_path):
    original = tmp_path / "target.py"
    original.write_text("print('Goc')", encoding="utf-8")

    candidate_code = "print('Bản sửa thử nghiệm')"
    res = run_candidate_source(candidate_code, original)
    assert res.ok
    assert "Bản sửa thử nghiệm" in res.stdout
    # Đảm bảo file gốc không bị chạm tới và file tạm đã được dọn sạch
    assert original.read_text(encoding="utf-8") == "print('Goc')"
    assert not list(tmp_path.glob(".*codex_tmp.py"))

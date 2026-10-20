"""Giao diện dòng lệnh chính (CLI Controller) sử dụng Rich và Argparse."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

import openai
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from . import __version__
from .client import CodexClient, DEFAULT_MODEL
from .prompts import (
    LEVEL_HINTS,
    build_convert_prompt,
    build_explain_prompt,
    build_fix_prompt,
    build_test_prompt,
)
from .runner import run_candidate_source, run_python_file
from .utils import (
    CLIError,
    add_line_numbers,
    backup_and_write,
    detect_language,
    make_diff,
    normalize_target_lang,
    parse_line_range,
    read_source,
    split_code_and_notes,
)

console = Console()
err_console = Console(stderr=True)


def cmd_explain(args: argparse.Namespace, client: CodexClient) -> int:
    path = Path(args.file)
    code = read_source(path)
    lang = detect_language(path)

    start_line = 1
    if args.lines:
        first, last = parse_line_range(args.lines)
        lines = code.splitlines()
        if first > len(lines):
            raise CLIError(f"Tệp chỉ có {len(lines)} dòng, không tồn tại dòng bắt đầu {first}.")
        code = "\n".join(lines[first - 1:last])
        start_line = first

    numbered = add_line_numbers(code, start=start_line)
    prompt = build_explain_prompt(path.name, lang, numbered, args.level)

    console.print(
        Panel.fit(
            f"📖 [bold]{path.name}[/bold] | Ngôn ngữ: [cyan]{lang}[/cyan] | Cấp độ: [green]{args.level.upper()}[/green] | Model: [yellow]{client.model}[/yellow]",
            border_style="cyan",
        )
    )

    buffer = ""
    with Live(Markdown(""), console=console, refresh_per_second=8, vertical_overflow="visible") as live:
        for chunk in client.stream_text(prompt):
            buffer += chunk
            live.update(Markdown(buffer))

    return 0


def cmd_fix(args: argparse.Namespace, client: CodexClient) -> int:
    path = Path(args.file)
    original_code = read_source(path)
    lang = detect_language(path)
    is_python = path.suffix.lower() == ".py"
    max_attempts = max(1, min(args.max_attempts, 5))

    console.print(
        Panel.fit(
            f"🛠️ [bold]{path.name}[/bold] | Ngôn ngữ: [cyan]{lang}[/cyan] | Model: [yellow]{client.model}[/yellow]",
            border_style="yellow",
        )
    )

    error_trace = ""
    auto_captured = False

    if args.error_file:
        error_trace = read_source(Path(args.error_file))
    elif args.error:
        error_trace = args.error
    elif is_python:
        with console.status("[bold blue]Đang chạy thử tệp để bắt Traceback thực tế...[/bold blue]"):
            res = run_python_file(path, timeout=args.timeout)
            if res.ok:
                console.print("[green]✔ Tệp thực thi thành công (Exit Code 0). Không phát hiện lỗi Runtime.[/green]")
                console.print("[dim]Nếu là lỗi logic, vui lòng truyền thông báo qua cờ: --error \"mô tả lỗi\"[/dim]")
                return 0
            error_trace = res.error_text
            auto_captured = True
            console.print(Panel(error_trace, title="💥 Traceback Bắt Được", border_style="red"))
    else:
        raise CLIError("Với ngôn ngữ khác Python, vui lòng cung cấp lỗi qua cờ --error hoặc --error-file.")

    can_verify = is_python and auto_captured and not args.no_verify
    current_code = original_code
    history: List[dict] = []
    final_solution = None
    is_verified = False

    for attempt in range(1, max_attempts + 1):
        if can_verify:
            console.rule(f"[bold yellow]Vòng lặp tự động sửa & kiểm chứng ({attempt}/{max_attempts})[/bold yellow]")

        with console.status(f"[bold cyan]AI đang phân tích và tạo bản vá (Lần {attempt})...[/bold cyan]"):
            prompt = build_fix_prompt(path.name, lang, current_code, error_trace, history)
            data = client.ask_json(prompt, temperature=0.1)

        candidate_code = data.get("fixed_code", "").strip()
        if not candidate_code:
            raise CLIError("Mô hình không trả về khối mã nguồn 'fixed_code'. Vui lòng thử lại.")

        final_solution = (candidate_code, data)

        if not can_verify:
            break

        with console.status("[bold green]Đang kiểm chứng bản vá trong sandbox cô lập...[/bold green]"):
            test_run = run_candidate_source(candidate_code, path, timeout=args.timeout)

        if test_run.ok:
            console.print("✅ [bold green]Bản vá đã chạy thử thành công trong sandbox (Exit Code 0)![/bold green]")
            is_verified = True
            break
        else:
            console.print(f"❌ [red]Bản vá lần {attempt} vẫn gặp lỗi:[/red] {test_run.error_text[:200]}...")
            history.append({
                "attempt": attempt,
                "error": test_run.error_text,
            })
            error_trace = test_run.error_text
            current_code = candidate_code

    if not final_solution:
        console.print("[red]Không thể tìm được phương án sửa lỗi khả thi.[/red]")
        return 1

    fixed_code, meta = final_solution

    # Hiển thị giải thích lỗi
    blocks = [
        f"**Loại lỗi:** `{meta.get('error_type', 'Lỗi chưa phân loại')}`",
        f"**Nguyên nhân:** {meta.get('root_cause_vi', '')}",
        f"**Cách khắc phục:** {meta.get('fix_explanation_vi', '')}",
    ]
    summary = meta.get("changes_summary") or []
    if summary:
        blocks.append("**Các thay đổi cụ thể:**\n" + "\n".join(f"- {s}" for s in summary))
    if meta.get("prevention_tip"):
        blocks.append(f"💡 **Bài học kinh nghiệm:** {meta['prevention_tip']}")

    console.print(Panel(Markdown("\n\n".join(blocks)), title="🧑‍🏫 Phân Tích Kỹ Thuật", border_style="green"))

    diff = make_diff(original_code, fixed_code, path.name)
    if not diff:
        console.print("[yellow]Không có sự thay đổi nào trong mã nguồn.[/yellow]")
        return 0

    console.print(Panel(Syntax(diff, "diff", line_numbers=False), title="📝 So Sánh Unified Diff", border_style="cyan"))

    if can_verify and not is_verified:
        console.print("[bold red]⚠️ Cảnh báo: Đã hết số lần thử nhưng bản vá chưa vượt qua kiểm chứng runtime![/bold red]")

    should_apply = args.yes or Confirm.ask(
        "\n[bold]Bạn có muốn áp dụng bản vá vào tệp gốc? (Tệp gốc sẽ được lưu thành .bak)[/bold]",
        default=False,
    )

    if should_apply:
        backup = backup_and_write(path, fixed_code)
        console.print(f"🎉 [bold green]Đã cập nhật tệp:[/bold green] {path}")
        console.print(f"📦 [dim]Bản sao lưu đã được lưu tại: {backup}[/dim]")
    else:
        console.print("[dim]Đã hủy thao tác. Tệp gốc được giữ nguyên.[/dim]")

    return 0


def cmd_convert(args: argparse.Namespace, client: CodexClient) -> int:
    path = Path(args.file)
    code = read_source(path)
    source_lang = detect_language(path)

    target_info = normalize_target_lang(args.to)
    if not target_info:
        raise CLIError(f"Ngôn ngữ đích '{args.to}' chưa được hỗ trợ.")

    target_key, target_name, ext = target_info
    out_path = Path(args.output) if args.output else path.with_suffix(ext)

    if out_path.exists() and not args.force:
        raise CLIError(f"Tệp đích {out_path} đã tồn tại. Sử dụng cờ --force để ghi đè.")

    prompt = build_convert_prompt(path.name, source_lang, target_name, code)
    with console.status(f"[bold cyan]Đang chuyển đổi {source_lang} ➔ {target_name}...[/bold cyan]"):
        raw_res = client.ask_text(prompt, temperature=0.1)

    converted_code, notes = split_code_and_notes(raw_res)
    out_path.write_text(converted_code if converted_code.endswith("\n") else converted_code + "\n", encoding="utf-8")

    console.print(Panel(Syntax(converted_code, target_key, line_numbers=True), title=f"🚀 Mã Nguồn Đích: {out_path.name}", border_style="green"))
    if notes:
        console.print(Panel(Markdown(notes), title="📌 Lưu Ý Chuyển Đổi", border_style="cyan"))

    console.print(f"✅ [green]Đã lưu tệp tại:[/green] [bold]{out_path}[/bold]")
    return 0


def cmd_test(args: argparse.Namespace, client: CodexClient) -> int:
    path = Path(args.file)
    code = read_source(path)
    lang = detect_language(path)
    framework = args.framework or ("pytest" if lang == "Python" else "standard unit testing")

    prompt = build_test_prompt(path.name, lang, code, framework)
    with console.status(f"[bold cyan]Đang tự động thiết kế bộ Unit Test ({framework})...[/bold cyan]"):
        data = client.ask_json(prompt, temperature=0.2)

    scenarios = data.get("scenarios") or []
    test_code = data.get("test_code", "").strip()
    cmd = data.get("run_command", "")

    if scenarios:
        scenario_md = "**Các kịch bản kiểm thử được bao phủ:**\n" + "\n".join(f"- {s}" for s in scenarios)
        console.print(Panel(Markdown(scenario_md), title="🧪 Phân Tích Ca Kiểm Thử", border_style="yellow"))

    console.print(Panel(Syntax(test_code, "python" if "py" in path.suffix else "text", line_numbers=True), title="📄 Mã Nguồn Unit Test", border_style="green"))

    out_file = Path(args.output) if args.output else path.with_name(f"test_{path.stem}.py")
    out_file.write_text(test_code + "\n", encoding="utf-8")
    console.print(f"✅ [green]Đã lưu tệp Unit Test tại:[/green] [bold]{out_file}[/bold]")

    if cmd:
        console.print(f"▶️ [bold cyan]Câu lệnh chạy test:[/bold cyan] `{cmd}`")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-mentor",
        description="Codex Mentor VN — Trợ lý AI Phân tích, Sửa lỗi và Chuyển đổi mã nguồn bằng Tiếng Việt.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"OpenAI Model (mặc định: {DEFAULT_MODEL})")
    parser.add_argument("--api-key", default=None, help="OpenAI API Key (mặc định đọc từ biến OPENAI_API_KEY)")

    sub = parser.add_subparsers(dest="command", required=True, metavar="<lệnh>")

    # explain
    p_exp = sub.add_parser("explain", help="Giải thích mã nguồn theo ngữ cảnh và phân tích độ phức tạp Big-O")
    p_exp.add_argument("file", help="Đường dẫn tới tệp mã nguồn cần giải thích")
    p_exp.add_argument("--lines", help="Chỉ định khoảng dòng cần giải thích (ví dụ: 10-35 hoặc 15)")
    p_exp.add_argument("--level", choices=sorted(LEVEL_HINTS.keys()), default="newbie", help="Cấp độ người học (newbie, intermediate, advanced)")
    p_exp.set_defaults(func=cmd_explain)

    # fix
    p_fix = sub.add_parser("fix", help="Tự động chạy thử, chẩn đoán nguyên nhân gốc rễ và tự sửa lỗi lặp có kiểm chứng")
    p_fix.add_argument("file", help="Đường dẫn tới tệp mã nguồn bị lỗi")
    p_fix.add_argument("--error", help="Mô tả lỗi hoặc Traceback thủ công")
    p_fix.add_argument("--error-file", help="Đọc thông tin lỗi từ tệp log")
    p_fix.add_argument("--timeout", type=int, default=10, help="Thời gian tối đa khi chạy thử (giây, mặc định 10s)")
    p_fix.add_argument("--max-attempts", type=int, default=3, help="Số lần thử nghiệm sửa & chạy lại tối đa (1-5)")
    p_fix.add_argument("--no-verify", action="store_true", help="Tắt tính năng chạy thử kiểm chứng trong sandbox")
    p_fix.add_argument("-y", "--yes", action="store_true", help="Tự động áp dụng bản vá không cần hỏi xác nhận")
    p_fix.set_defaults(func=cmd_fix)

    # convert
    p_conv = sub.add_parser("convert", help="Chuyển đổi mã nguồn sang ngôn ngữ lập trình khác theo chuẩn Idiomatic")
    p_conv.add_argument("file", help="Tệp mã nguồn gốc cần chuyển đổi")
    p_conv.add_argument("--to", required=True, help="Ngôn ngữ lập trình đích (ví dụ: TypeScript, Go, Rust, Java, C++)")
    p_conv.add_argument("-o", "--output", help="Đường dẫn lưu tệp mã nguồn mới")
    p_conv.add_argument("--force", action="store_true", help="Ghi đè nếu tệp đích đã tồn tại")
    p_conv.set_defaults(func=cmd_convert)

    # test
    p_test = sub.add_parser("test", help="Tự động sinh bộ kiểm thử Unit Test bao phủ Edge Cases")
    p_test.add_argument("file", help="Tệp mã nguồn cần viết Unit Test")
    p_test.add_argument("--framework", help="Framework kiểm thử (mặc định: pytest cho Python)")
    p_test.add_argument("-o", "--output", help="Đường dẫn lưu tệp Unit Test")
    p_test.set_defaults(func=cmd_test)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        client = CodexClient(model=args.model, api_key=args.api_key)
        return args.func(args, client) or 0
    except KeyboardInterrupt:
        err_console.print("\n[yellow]Đã hủy thao tác.[/yellow]")
        return 130
    except CLIError as exc:
        err_console.print(f"[bold red]Lỗi CLI:[/bold red] {exc}")
        return 1
    except openai.AuthenticationError:
        err_console.print("[bold red]Lỗi Xác Thực:[/bold red] API Key không hợp lệ. Vui lòng kiểm tra lại OPENAI_API_KEY.")
        return 2
    except openai.RateLimitError:
        err_console.print("[bold red]Lỗi Hạn Mức:[/bold red] Đã vượt giới hạn tốc độ (Rate Limit) hoặc hết quota API.")
        return 2
    except openai.APIConnectionError:
        err_console.print("[bold red]Lỗi Mạng:[/bold red] Không thể kết nối tới máy chủ OpenAI.")
        return 2
    except openai.APIError as exc:
        err_console.print(f"[bold red]Lỗi OpenAI API:[/bold red] {exc}")
        return 2

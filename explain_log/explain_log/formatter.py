import json
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich import box

try:
    console = Console(legacy_windows=False, force_terminal=True)
except Exception:
    console = Console()

# ── COLORS ─────────────────────────────────────────────

SEVERITY_COLORS = {
    "critical": "bold red",
    "warn": "yellow",
    "info": "green"
}


# ── MAIN ENTRY ─────────────────────────────────────────

def render(result: dict, fmt: str = "terminal", save_path: str = None):
    try:
        if fmt == "json":
            print_json(result)
            return

        if fmt == "markdown":
            save_markdown(result, save_path)
            return

        print_terminal(result)

    except Exception as e:
        handle_error(e)


# ── TERMINAL UI (🔥 MAIN DESIGN) ───────────────────────

def print_terminal(result: dict):
    from rich.table import Table
    from rich.spinner import Spinner
    from rich.live import Live
    from rich.text import Text
    from rich.rule import Rule
    import time

    diagnosis = result.get("diagnosis", "")
    fixes = result.get("fixes", [])
    severity = result.get("severity", "warn")
    log_type = result.get("log_type", "unknown").upper()

    severity_colors = {
        "critical": "red",
        "warn": "yellow",
        "info": "green"
    }
    severity_badges = {
        "critical": "[bold white on red] CRITICAL [/] 🔴",
        "warn": "[bold black on yellow] WARN [/] 🟡",
        "info": "[bold black on green] INFO [/] 🟢"
    }
    severity_border = {
        "critical": "red",
        "warn": "yellow",
        "info": "green"
    }

    color = severity_colors.get(severity, "yellow")
    badge = severity_badges.get(severity, severity_badges["warn"])
    border_c = severity_border.get(severity, "yellow")

    # ── ANIMATED BOOT ──────────────────────────────
    with console.status(
        "[bold cyan]🔮 Initializing AI Analysis Engine...[/]",
        spinner="dots",
        speed=0.6
    ) as status:
        time.sleep(0.8)
        status.update("[bold magenta]🧠 Processing log patterns...[/]")
        time.sleep(0.5)
        status.update("[bold cyan]⚡ Running diagnosis...[/]")
        time.sleep(0.4)

    console.print()

    # ── MAIN HEADER ─────────────────────────────────
    header_text = Text()
    header_text.append("╔", style="cyan")
    header_text.append("═" * 54, style="bold cyan")
    header_text.append("╗\n", style="cyan")
    header_text.append("║", style="cyan")
    header_text.append("  🚀 EXPLAIN-LOG  //  AI ANALYSIS ENGINE  🚀", style="bold cyan")
    header_text.append(" ║\n", style="cyan")
    header_text.append("╚", style="cyan")
    header_text.append("═" * 54, style="bold cyan")
    header_text.append("╝", style="cyan")

    console.print(header_text)
    console.print()

    # ── METADATA TABLE ───────────────────────────────
    meta_table = Table(box=None, show_header=False, pad_edge=False, expand=True)
    meta_table.add_column(style="dim", width=20)
    meta_table.add_column(style="bold white", width=40)

    log_type_display = f"[bold cyan]{log_type}[/]"
    severity_display = badge
    meta_table.add_row("📋 LOG TYPE", log_type_display)
    meta_table.add_row("⚠ SEVERITY", severity_display)

    console.print(Panel(
        meta_table,
        box=box.ROUNDED,
        border_style="cyan",
        title="[bold]📡 SYSTEM METADATA[/bold]",
        title_align="left",
        padding=(0, 2)
    ))
    console.print()

    # ── DIAGNOSIS PANEL ──────────────────────────────
    diagnosis_clean = diagnosis if diagnosis else "No diagnosis available."
    diag_text = Text(diagnosis_clean, style="white")

    console.print(Panel(
        diag_text,
        title="[bold]🔍  ROOT CAUSE  🔍[/]",
        border_style=border_c,
        box=box.HEAVY,
        title_align="center",
        padding=(1, 3),
        width=70
    ))
    console.print()

    # ── FIXES PANEL ─────────────────────────────────
    if fixes:
        fixes_lines = []
        for i, fix in enumerate(fixes, 1):
            num = Text(f"{i:02d}", style="bold yellow")
            arrow = Text("  →  ", style="dim")
            fixes_lines.append(num + arrow + Text(fix, style="white"))
        fixes_text = fixes_lines[0]
        for line in fixes_lines[1:]:
            fixes_text = fixes_text + Text("\n") + line
    else:
        fixes_text = Text("   No fixes available at this time.", style="dim")

    console.print(Panel(
        fixes_text,
        title="[bold]🔧  SUGGESTED FIXES  🔧[/]",
        border_style="green",
        box=box.HEAVY,
        title_align="center",
        padding=(1, 3),
        width=70
    ))
    console.print()

    # ── STATUS BAR ───────────────────────────────────
    status_icon = "🔴" if severity == "critical" else ("🟡" if severity == "warn" else "🟢")
    console.print(
        Rule(style="cyan", characters="─"),
        justify="center"
    )
    console.print(
        f"  {status_icon} [bold]Analysis Complete[/bold] — "
        f"[dim]Errors: [white]{len(fixes) if fixes else 0}[/] fixes identified[/dim]  {status_icon}",
        justify="center"
    )
    console.print(
        Rule(style="cyan", characters="─"),
        justify="center"
    )
    console.print()

    # ── FOOTER ────────────────────────────────────────
    footer = Text()
    footer.append("  ╰────────────────────────────────────────╯", style="dim cyan")
    footer.append("\n   ", style="dim")
    footer.append("⚡ Powered by AI", style="bold dim cyan")
    footer.append("   •   ", style="dim")
    footer.append("explain-log", style="dim white")
    footer.append("   •   ", style="dim")
    footer.append("v1.0.0", style="dim")
    console.print(footer)
    console.print()

    # ── DRAMATIC PAUSE (optional vibe) ────────────────
    time.sleep(0.1)


# ── JSON OUTPUT ───────────────────────────────────────

def print_json(result: dict):
    print(json.dumps(result, indent=2))


# ── MARKDOWN EXPORT ───────────────────────────────────

def save_markdown(result: dict, path: str = None):
    if not path:
        path = "report.md"

    diagnosis = result.get("diagnosis", "")
    fixes = result.get("fixes", [])
    severity = result.get("severity", "warn")
    log_type = result.get("log_type", "unknown").upper()

    md = f"""# 🚀 Explain Log Report

## 🧠 Log Type
{log_type}

## ⚠ Severity
{severity.upper()}

## 🔍 Diagnosis
{diagnosis}

## 🔧 Fixes
"""

    for i, fix in enumerate(fixes, 1):
        md += f"{i}. {fix}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(md)

    console.print(f"[green]✔ Report saved to {path}[/green]")


# ── ERROR HANDLING ────────────────────────────────────

def handle_error(e: Exception):
    msg = str(e).lower()

    if "api key" in msg:
        console.print("[red]❌ Missing API key. Set GROQ_API_KEY[/red]")
    elif "rate limit" in msg:
        console.print("[yellow]⚠ Rate limit exceeded. Try later[/yellow]")
    elif "empty" in msg:
        console.print("[red]❌ Log file is empty[/red]")
    else:
        console.print(f"[red]❌ Error:[/red] {e}")

    sys.exit(1)


# ── TEST MODE ─────────────────────────────────────────

if __name__ == "__main__":
    sample = {
        "log_type": "windows",
        "severity": "critical",
        "diagnosis": "MySQL service failed due to missing file.",
        "fixes": [
            "Check config path",
            "Run system file checker",
            "Reinstall service"
        ]
    }

    render(sample)

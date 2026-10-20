#!/usr/bin/env python3
"""
DEV_Cheat: Autonomous Real-Time Screen Question Solver & Developer Assistant
Author: Bisman Singh
Repository: Bisman-Singh-Dev/DEV_Cheat
"""

import sys
import os
import argparse
import webbrowser
import threading
import time
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dev_cheat.config import config
from dev_cheat.screen_monitor import screen_monitor
from dev_cheat.server import app

console = Console(force_terminal=True, legacy_windows=False)

BANNER = r"""[bold red]
====================================================================
  ____  _______     __     ____ _                     _   
 |  _ \| ____\ \   / /    / ___| |__   ___  __ _  ___| |_ 
 | | | |  _|  \ \ / /____| |   | '_ \ / _ \/ _` |/ __| __|
 | |_| | |___  \ V /_____| |___| | | |  __/ (_| | (__| |_ 
 |____/|_____|  \_/       \____|_| |_|\___|\__,_|\___|\__|
====================================================================
[/bold red]
[bold cyan]>> Real-Time Screen Question Solver & Neural Assistant <<[/bold cyan]
"""

def print_banner(host: str, port: int):
    console.print(BANNER)
    
    table = Table(title="[bold green]System Configuration & Status[/bold green]", border_style="bright_blue")
    table.add_column("Property", style="cyan", justify="left")
    table.add_column("Value", style="magenta", justify="left")
    
    table.add_row("Localhost Dashboard", f"[bold underline green]http://{host}:{port}[/bold underline green]")
    table.add_row("AI Engine", f"[bold yellow]{config.gemini_model}[/bold yellow] (Gemini Neural)")
    table.add_row("Screen OCR", "Windows Native Windows.Media.Ocr (Zero-Latency)")
    table.add_row("Scan Interval", f"{config.scan_interval}s")
    table.add_row("Auto-Solve Single", "[bold green]ENABLED[/bold green]" if config.auto_solve_single else "[yellow]DISABLED[/yellow]")
    table.add_row("Desktop Red Box HUD", "[bold green]ENABLED[/bold green]" if config.enable_desktop_overlay else "[yellow]DISABLED[/yellow]")
    
    console.print(table)
    
    hotkey_panel = Panel(
        Text.from_markup(
            "[bold red][Q][/bold red] : Hide active responses & dismiss overlay\n"
            "[bold cyan][S][/bold cyan] : Force instant manual screen scan\n"
            "[bold yellow][C][/bold yellow] : Clear highlighted questions & cache\n"
            "[bold green][Click][/bold green] : Click on any Red Bounding Box on screen/dashboard to solve\n"
            "[bold white][Ctrl+C][/bold white] : Stop Dev_Cheat safely"
        ),
        title="[bold white]Command Prompt Hotkey Legend[/bold white]",
        border_style="red"
    )
    console.print(hotkey_panel)
    console.print("[dim]Monitoring screen for coding problems, multiple choice, and tech questions...[/dim]\n")


def parse_args():
    parser = argparse.ArgumentParser(description="DEV_Cheat: Autonomous Screen Question Solver")
    parser.add_argument("--port", type=int, default=config.port, help=f"Localhost server port (default: {config.port})")
    parser.add_argument("--host", type=str, default=config.host, help=f"Server host (default: {config.host})")
    parser.add_argument("--interval", type=float, default=config.scan_interval, help="Screen scan interval in seconds")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--no-overlay", action="store_true", help="Disable transparent desktop red box overlay")
    parser.add_argument("--no-auto-solve", action="store_true", help="Disable auto-solving for single questions")
    return parser.parse_args()


def main():
    args = parse_args()

    # Update config with CLI args
    config.port = args.port
    config.host = args.host
    config.scan_interval = args.interval
    if args.no_overlay:
        config.enable_desktop_overlay = False
    if args.no_auto_solve:
        config.auto_solve_single = False

    # Find available port if specified port is already bound
    import socket
    def is_port_in_use(port, host):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    active_port = config.port
    if is_port_in_use(active_port, config.host):
        console.print(f"[yellow]Port {active_port} is currently busy. Finding alternative open port...[/yellow]")
        for alt_port in range(active_port + 1, active_port + 20):
            if not is_port_in_use(alt_port, config.host):
                active_port = alt_port
                break

    config.port = active_port
    print_banner(config.host, config.port)

    # Start screen monitor background worker
    screen_monitor.start()

    # Open localhost in browser
    if not args.no_browser:
        def open_browser():
            time.sleep(1.2)
            url = f"http://{config.host}:{config.port}"
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=open_browser, daemon=True).start()

    # Run Uvicorn server (blocking main thread)
    try:
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level="warning"
        )
    except KeyboardInterrupt:
        console.print("\n[bold red]Stopping DEV_Cheat...[/bold red]")
    finally:
        screen_monitor.stop()
        console.print("[bold green]DEV_Cheat stopped cleanly.[/bold green]")


if __name__ == "__main__":
    main()

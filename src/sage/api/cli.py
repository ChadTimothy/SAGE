"""SAGE Command Line Interface."""

import typer
from rich.console import Console

app = typer.Typer(
    name="sage",
    help="SAGE - AI tutor that teaches through conversation, not curriculum",
    add_completion=False,
)
console = Console()


@app.command()
def chat(
    learner: str = typer.Option(None, "--learner", "-l", help="Learner name"),
):
    """Start a conversation with SAGE."""
    console.print("[bold blue]SAGE[/bold blue] - Knows what you're ready to learn")
    console.print()
    console.print("[dim]Chat functionality coming soon...[/dim]")


@app.command()
def status():
    """Show current learner status and progress."""
    console.print("[bold]SAGE Status[/bold]")
    console.print("[dim]Status functionality coming soon...[/dim]")


if __name__ == "__main__":
    app()

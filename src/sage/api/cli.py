"""SAGE Command Line Interface.

Provides interactive conversation, status, history, and management commands
for the SAGE learning system.
"""

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt

from sage.core.config import get_settings
from sage.graph.learning_graph import LearningGraph
from sage.dialogue.conversation import create_conversation_engine

app = typer.Typer(
    name="sage",
    help="SAGE - AI tutor that teaches through conversation, not curriculum",
    add_completion=False,
)
console = Console()


def _get_graph() -> LearningGraph:
    """Get configured learning graph instance."""
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return LearningGraph(str(settings.db_path))


def _format_timestamp(ts: Optional[datetime]) -> str:
    """Format timestamp for display."""
    if not ts:
        return "Never"
    return ts.strftime("%Y-%m-%d %H:%M")


@app.command()
def chat(
    learner: Optional[str] = typer.Option(
        None, "--learner", "-l", help="Learner ID (creates new if not found)"
    ),
    resume: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Session ID to resume"
    ),
):
    """Start an interactive conversation with SAGE.

    Examples:
        sage chat                    # Start new session for default learner
        sage chat -l john            # Start session for learner 'john'
        sage chat -r session-123     # Resume existing session
    """
    settings = get_settings()

    if not settings.llm_api_key:
        console.print(
            "[bold red]Error:[/bold red] LLM_API_KEY environment variable is required.",
            style="red",
        )
        console.print("Set it in your .env file or environment.")
        raise typer.Exit(1)

    console.print(
        Panel(
            "[bold blue]SAGE[/bold blue] - Knows what you're ready to learn\n\n"
            "[dim]Type 'exit' or 'quit' to end the conversation.[/dim]",
            title="Welcome",
            border_style="blue",
        )
    )

    try:
        graph = _get_graph()
        engine = create_conversation_engine(
            graph=graph,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )

        # Get or create learner
        if learner:
            learner_obj = graph.get_or_create_learner(learner_id=learner)
            console.print(f"[dim]Using learner: {learner}[/dim]\n")
        else:
            learner_obj = graph.get_or_create_learner()
            console.print(f"[dim]Using learner: {learner_obj.id}[/dim]\n")

        # Start or resume session
        if resume:
            session, mode = engine.resume_session(resume)
            console.print(f"[dim]Resumed session: {session.id}[/dim]\n")
        else:
            session, mode = engine.start_session(learner_obj.id)
            console.print(f"[dim]Started session: {session.id}[/dim]\n")

        # Conversation loop
        while True:
            try:
                user_input = Prompt.ask("[bold green]You[/bold green]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Conversation ended.[/dim]")
                break

            if not user_input.strip():
                continue

            if user_input.lower().strip() in ["exit", "quit", "bye", "q"]:
                console.print("[dim]Ending conversation...[/dim]")
                break

            # Process turn and get response
            try:
                response = engine.process_turn(user_input)
                console.print()
                console.print(
                    Panel(
                        Markdown(response.message),
                        title="[bold blue]SAGE[/bold blue]",
                        border_style="blue",
                    )
                )
                console.print()

                # Show mode change if any
                if response.transition_to:
                    console.print(
                        f"[dim]Mode: {response.current_mode.value} → {response.transition_to.value}[/dim]"
                    )

                # Check if outcome achieved
                if response.outcome_achieved:
                    console.print(
                        "\n[bold green]Congratulations! You've achieved your learning goal.[/bold green]\n"
                    )
                    break

            except Exception as e:
                console.print(f"[red]Error processing response: {e}[/red]")
                continue

        # End session
        try:
            session = engine.end_session()
            console.print(f"\n[dim]Session saved: {session.id}[/dim]")
        except RuntimeError:
            pass  # Session may already be ended

    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    learner: Optional[str] = typer.Option(
        None, "--learner", "-l", help="Learner ID to show status for"
    ),
):
    """Show current learner status and progress.

    Displays active outcome, proven concepts, session history, and insights.

    Examples:
        sage status              # Show status for default learner
        sage status -l john      # Show status for learner 'john'
    """
    try:
        graph = _get_graph()

        # Get learner
        if learner:
            learner_obj = graph.get_learner(learner)
        else:
            learner_obj = graph.get_or_create_learner()

        if not learner_obj:
            console.print(f"[yellow]Learner '{learner}' not found.[/yellow]")
            raise typer.Exit(1)

        # Header
        console.print(
            Panel(
                f"[bold]{learner_obj.profile.name or learner_obj.id}[/bold]",
                title="Learner Status",
                border_style="blue",
            )
        )

        # Stats table
        stats = Table(show_header=False, box=None, padding=(0, 2))
        stats.add_column("Label", style="dim")
        stats.add_column("Value")

        stats.add_row("Total Sessions", str(learner_obj.total_sessions))
        stats.add_row("Total Proofs", str(learner_obj.total_proofs))
        stats.add_row("Last Session", _format_timestamp(learner_obj.last_session_at))
        stats.add_row("Member Since", _format_timestamp(learner_obj.created_at))

        console.print(stats)
        console.print()

        # Active outcome
        if learner_obj.active_outcome_id:
            outcome = graph.get_outcome(learner_obj.active_outcome_id)
            if outcome:
                console.print("[bold]Active Goal:[/bold]")
                console.print(f"  {outcome.stated_goal}")
                console.print()

        # Proven concepts
        proven_pairs = graph.get_proven_concepts(learner_obj.id)
        if proven_pairs:
            console.print(f"[bold]Proven Concepts ({len(proven_pairs)}):[/bold]")
            for concept, _proof in proven_pairs[:5]:
                console.print(f"  • {concept.title}")
            if len(proven_pairs) > 5:
                console.print(f"  [dim]... and {len(proven_pairs) - 5} more[/dim]")
            console.print()

        # Insights
        if learner_obj.insights:
            insights = learner_obj.insights
            if insights.best_energy_level or insights.preferred_learning_style:
                console.print("[bold]Learning Insights:[/bold]")
                if insights.best_energy_level:
                    console.print(f"  Best energy: {insights.best_energy_level}")
                if insights.preferred_learning_style:
                    console.print(f"  Style: {insights.preferred_learning_style}")
                if insights.effective_approaches:
                    console.print(f"  Effective: {', '.join(insights.effective_approaches[:3])}")
                console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def history(
    learner: Optional[str] = typer.Option(
        None, "--learner", "-l", help="Learner ID"
    ),
    limit: int = typer.Option(
        5, "--limit", "-n", help="Number of sessions to show"
    ),
    session: Optional[str] = typer.Option(
        None, "--session", "-s", help="Show specific session details"
    ),
):
    """Display conversation history.

    Shows recent sessions or detailed view of a specific session.

    Examples:
        sage history              # Show last 5 sessions
        sage history -n 10        # Show last 10 sessions
        sage history -s sess-123  # Show specific session
    """
    try:
        graph = _get_graph()

        # Show specific session
        if session:
            sess = graph.get_session(session)
            if not sess:
                console.print(f"[yellow]Session '{session}' not found.[/yellow]")
                raise typer.Exit(1)

            console.print(
                Panel(
                    f"Session: {sess.id}\n"
                    f"Started: {_format_timestamp(sess.started_at)}\n"
                    f"Ended: {_format_timestamp(sess.ended_at)}\n"
                    f"Messages: {len(sess.messages)}",
                    title="Session Details",
                    border_style="blue",
                )
            )
            console.print()

            # Show messages
            for msg in sess.messages:
                if msg.role == "user":
                    console.print(f"[green]You:[/green] {msg.content}")
                else:
                    console.print(f"[blue]SAGE:[/blue] {msg.content}")
                console.print()

            return

        # Get learner
        if learner:
            learner_obj = graph.get_learner(learner)
        else:
            learner_obj = graph.get_or_create_learner()

        if not learner_obj:
            console.print(f"[yellow]Learner '{learner}' not found.[/yellow]")
            raise typer.Exit(1)

        # Get sessions
        sessions = graph.get_sessions_by_learner(learner_obj.id)

        if not sessions:
            console.print("[dim]No conversation history yet.[/dim]")
            return

        console.print(
            Panel(
                f"Showing last {min(limit, len(sessions))} of {len(sessions)} sessions",
                title="Conversation History",
                border_style="blue",
            )
        )
        console.print()

        # Sessions table
        table = Table(show_header=True)
        table.add_column("Session ID", style="cyan")
        table.add_column("Date", style="dim")
        table.add_column("Messages")
        table.add_column("Concepts")
        table.add_column("Proofs")

        for sess in sessions[:limit]:
            table.add_row(
                sess.id[:20] + "..." if len(sess.id) > 20 else sess.id,
                _format_timestamp(sess.started_at),
                str(len(sess.messages)),
                str(len(sess.concepts_explored)),
                str(len(sess.proofs_earned)),
            )

        console.print(table)
        console.print()
        console.print("[dim]Use 'sage history -s <session-id>' to view a specific session.[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def reset(
    learner: Optional[str] = typer.Option(
        None, "--learner", "-l", help="Learner ID to reset"
    ),
    confirm: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt"
    ),
):
    """Reset learner data.

    Clears all data for a learner including sessions, proofs, and progress.
    This action cannot be undone.

    Examples:
        sage reset                # Reset default learner (with confirmation)
        sage reset -l john -y     # Reset learner 'john' without confirmation
    """
    try:
        graph = _get_graph()

        # Get learner
        if learner:
            learner_obj = graph.get_learner(learner)
        else:
            learner_obj = graph.get_or_create_learner()

        if not learner_obj:
            console.print(f"[yellow]Learner '{learner}' not found.[/yellow]")
            raise typer.Exit(1)

        learner_id = learner_obj.id

        # Show what will be deleted
        sessions = graph.get_sessions_by_learner(learner_id)
        proven_pairs = graph.get_proven_concepts(learner_id)

        console.print(
            Panel(
                f"[bold]Learner:[/bold] {learner_id}\n"
                f"[bold]Sessions:[/bold] {len(sessions)}\n"
                f"[bold]Proven Concepts:[/bold] {len(proven_pairs)}\n\n"
                "[bold red]This action cannot be undone.[/bold red]",
                title="Reset Learner Data",
                border_style="red",
            )
        )

        # Confirm
        if not confirm:
            response = Prompt.ask(
                "Are you sure you want to delete all data?",
                choices=["y", "n"],
                default="n",
            )
            if response.lower() != "y":
                console.print("[dim]Reset cancelled.[/dim]")
                return

        # Note: Full reset requires database deletion
        # For now, we can only reset by manually deleting the database file
        console.print(
            "[yellow]Note: Full learner reset not yet implemented.[/yellow]\n"
            f"To fully reset, delete the database file at: {get_settings().db_path}"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

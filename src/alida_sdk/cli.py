"""Typer CLI for the Alida SDK."""

from __future__ import annotations

import csv
import io
import sys
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from alida_sdk.client import AlidaClient
from alida_sdk.exceptions import AlidaError, NotFoundError
from alida_sdk.output import emit_error, emit_json
from alida_sdk.surveys import SurveyResource

app = typer.Typer(name="alida-sdk", help="Alida CXM SDK — survey data extraction")
surveys_app = typer.Typer(help="Survey operations")
app.add_typer(surveys_app, name="surveys")

console = Console(stderr=True)


@surveys_app.command("list")
def surveys_list(
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON to stdout")
    ] = False,
) -> None:
    """List all surveys."""
    try:
        with AlidaClient() as client:
            resource = SurveyResource(client)
            surveys = resource.list_surveys()
    except NotFoundError as e:
        if json_output:
            emit_error(str(e), 2)
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    except AlidaError as e:
        if json_output:
            emit_error(str(e), 1)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        emit_json([s.to_dict() for s in surveys])
        return

    table = Table(title="Surveys")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Status", style="green")
    table.add_column("Type")
    table.add_column("Created")

    for s in surveys:
        table.add_row(s.id, s.name, s.status, s.type or "", s.created_at or "")

    console.print(table)


@surveys_app.command("get")
def surveys_get(
    survey_id: Annotated[str, typer.Argument(help="Survey ID")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON to stdout")
    ] = False,
) -> None:
    """Get details for a single survey."""
    try:
        with AlidaClient() as client:
            resource = SurveyResource(client)
            survey = resource.get_survey(survey_id)
    except NotFoundError as e:
        if json_output:
            emit_error("Survey not found", 2)
        console.print(f"[red]Survey not found:[/red] {e}")
        raise typer.Exit(2)
    except AlidaError as e:
        if json_output:
            emit_error(str(e), 1)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        emit_json(survey.to_dict())
        return

    console.print(f"[bold]ID:[/bold] {survey.id}")
    console.print(f"[bold]Name:[/bold] {survey.name}")
    console.print(f"[bold]Status:[/bold] {survey.status}")
    console.print(f"[bold]Type:[/bold] {survey.type or 'N/A'}")
    console.print(f"[bold]Created:[/bold] {survey.created_at or 'N/A'}")
    console.print(f"[bold]Updated:[/bold] {survey.updated_at or 'N/A'}")


@surveys_app.command("responses")
def surveys_responses(
    survey_id: Annotated[str, typer.Argument(help="Survey ID")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON to stdout")
    ] = False,
    csv_output: Annotated[
        bool, typer.Option("--csv", help="Output as CSV")
    ] = False,
    output_file: Annotated[
        Optional[str], typer.Option("--output", "-o", help="Write output to file")
    ] = None,
) -> None:
    """Export all responses for a survey."""
    try:
        with AlidaClient() as client:
            resource = SurveyResource(client)
            console.print(f"Exporting responses for survey {survey_id}...")
            responses = resource.get_responses(survey_id)
    except NotFoundError as e:
        if json_output:
            emit_error("Survey not found", 2)
        console.print(f"[red]Survey not found:[/red] {e}")
        raise typer.Exit(2)
    except AlidaError as e:
        if json_output:
            emit_error(str(e), 1)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"Retrieved {len(responses)} responses.")

    dest = open(output_file, "w") if output_file else sys.stdout  # noqa: SIM115

    try:
        if json_output:
            import json

            dest.write(json.dumps([r.to_dict() for r in responses], indent=2, default=str))
            dest.write("\n")
        elif csv_output:
            if not responses:
                return
            # Collect all keys from response data for CSV columns
            all_keys = ["id", "survey_id", "submitted_at"]
            data_keys: set[str] = set()
            for r in responses:
                data_keys.update(r.data.keys())
            all_keys.extend(sorted(data_keys))

            writer = csv.DictWriter(dest, fieldnames=all_keys)
            writer.writeheader()
            for r in responses:
                row = {
                    "id": r.id,
                    "survey_id": r.survey_id,
                    "submitted_at": r.submitted_at,
                    **r.data,
                }
                writer.writerow(row)
        else:
            # Rich table output to stderr
            table = Table(title=f"Responses for Survey {survey_id}")
            table.add_column("ID", style="cyan")
            table.add_column("Submitted At")
            table.add_column("Fields", style="dim")

            for r in responses:
                fields = ", ".join(f"{k}={v}" for k, v in list(r.data.items())[:5])
                if len(r.data) > 5:
                    fields += f" (+{len(r.data) - 5} more)"
                table.add_row(r.id, r.submitted_at or "", fields)

            console.print(table)
    finally:
        if output_file and dest is not sys.stdout:
            dest.close()

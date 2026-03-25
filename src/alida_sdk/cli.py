"""Typer CLI for the Alida SDK."""

from __future__ import annotations

import json
import sys
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from alida_sdk.client import AlidaClient
from alida_sdk.exceptions import AlidaError, NotFoundError
from alida_sdk.output import emit_csv, emit_error, emit_json, output_dest
from alida_sdk.questions import QuestionResource
from alida_sdk.surveys import SurveyResource
from alida_sdk.transforms import strip_html, transform_responses

app = typer.Typer(name="alida-sdk", help="Alida CXM SDK — survey data extraction")
surveys_app = typer.Typer(help="Survey operations")
app.add_typer(surveys_app, name="surveys")
datasets_app = typer.Typer(help="Dataset operations")
app.add_typer(datasets_app, name="datasets")
questions_app = typer.Typer(help="Question operations (via datasets)")
app.add_typer(questions_app, name="questions")

console = Console(stderr=True)


@surveys_app.command("list")
def surveys_list(
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

    if csv_output:
        headers = ["id", "name", "status", "type", "created_at"]
        rows = [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status,
                "type": s.type or "",
                "created_at": s.created_at or "",
            }
            for s in surveys
        ]
        with output_dest(output_file) as dest:
            emit_csv(headers, rows, dest)
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
    dataset_id: Annotated[
        Optional[str],
        typer.Option("--dataset-id", help="Dataset ID for human-readable column headers"),
    ] = None,
) -> None:
    """Export all responses for a survey."""
    structured = json_output or csv_output
    try:
        with AlidaClient() as client:
            resource = SurveyResource(client)
            if not structured:
                console.print(f"Exporting responses for survey {survey_id}...")
            responses = resource.get_responses(survey_id)

            questions = None
            if dataset_id:
                if not structured:
                    console.print(f"Fetching question metadata from dataset {dataset_id}...")
                qr = QuestionResource(client)
                questions = qr.list_questions(dataset_id)
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

    if not structured:
        console.print(f"Retrieved {len(responses)} responses.")

    with output_dest(output_file) as dest:
        if json_output:
            if questions:
                headers, rows = transform_responses(responses, questions)
                dest.write(json.dumps(rows, indent=2, default=str))
            else:
                dest.write(
                    json.dumps(
                        [r.to_dict() for r in responses], indent=2, default=str
                    )
                )
            dest.write("\n")
        elif csv_output:
            if not responses:
                return
            headers, rows = transform_responses(responses, questions)
            emit_csv(headers, rows, dest)
        else:
            # Rich table output to stderr
            table = Table(title=f"Responses for Survey {survey_id}")
            table.add_column("ID", style="cyan")
            table.add_column("Submitted At")
            table.add_column("Fields", style="dim")

            for r in responses:
                fields = ", ".join(
                    f"{k}={v}" for k, v in list(r.data.items())[:5]
                )
                if len(r.data) > 5:
                    fields += f" (+{len(r.data) - 5} more)"
                table.add_row(r.id, r.submitted_at or "", fields)

            console.print(table)


@datasets_app.command("list")
def datasets_list(
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
    """List all datasets (use dataset IDs for questions commands)."""
    try:
        with AlidaClient() as client:
            items = client.get_paginated("datasets")
    except AlidaError as e:
        if json_output:
            emit_error(str(e), 1)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        emit_json(items)
        return

    if csv_output:
        headers = ["id", "name"]
        rows = [
            {"id": str(item.get("id", "")), "name": item.get("name", "")}
            for item in items
        ]
        with output_dest(output_file) as dest:
            emit_csv(headers, rows, dest)
        return

    table = Table(title="Datasets")
    table.add_column("ID", style="cyan")
    table.add_column("Name")

    for item in items:
        table.add_row(str(item.get("id", "")), item.get("name", ""))

    console.print(table)


@questions_app.command("list")
def questions_list(
    dataset_id: Annotated[str, typer.Argument(help="Dataset ID (from 'datasets list')")],
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
    """List all questions for a dataset."""
    try:
        with AlidaClient() as client:
            resource = QuestionResource(client)
            questions = resource.list_questions(dataset_id)
    except NotFoundError as e:
        if json_output:
            emit_error("Dataset not found", 2)
        console.print(f"[red]Dataset not found:[/red] {e}")
        raise typer.Exit(2)
    except AlidaError as e:
        if json_output:
            emit_error(str(e), 1)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        emit_json([q.to_dict() for q in questions])
        return

    if csv_output:
        headers = ["id", "name", "text", "type", "num_options"]
        rows = [
            {
                "id": q.id,
                "name": q.name,
                "text": strip_html(q.text),
                "type": q.type or "",
                "num_options": str(len(q.answer_options)),
            }
            for q in questions
        ]
        with output_dest(output_file) as dest:
            emit_csv(headers, rows, dest)
        return

    table = Table(title=f"Questions for Dataset {dataset_id}")
    table.add_column("ID", style="cyan")
    table.add_column("Text")
    table.add_column("Type", style="green")
    table.add_column("Options", style="dim")

    for q in questions:
        option_count = str(len(q.answer_options)) if q.answer_options else "—"
        table.add_row(q.id, q.text, q.type or "", option_count)

    console.print(table)


@questions_app.command("get")
def questions_get(
    dataset_id: Annotated[str, typer.Argument(help="Dataset ID (from 'datasets list')")],
    question_id: Annotated[str, typer.Argument(help="Question ID")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON to stdout")
    ] = False,
) -> None:
    """Get details for a single question, including answer options."""
    try:
        with AlidaClient() as client:
            resource = QuestionResource(client)
            question = resource.get_question(dataset_id, question_id)
    except NotFoundError as e:
        if json_output:
            emit_error("Question not found", 2)
        console.print(f"[red]Question not found:[/red] {e}")
        raise typer.Exit(2)
    except AlidaError as e:
        if json_output:
            emit_error(str(e), 1)
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if json_output:
        emit_json(question.to_dict())
        return

    console.print(f"[bold]ID:[/bold] {question.id}")
    console.print(f"[bold]Text:[/bold] {question.text}")
    console.print(f"[bold]Type:[/bold] {question.type or 'N/A'}")
    console.print(f"[bold]Dataset:[/bold] {question.survey_id}")

    if question.answer_options:
        console.print(f"\n[bold]Answer Options ({len(question.answer_options)}):[/bold]")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Text")

        for opt in question.answer_options:
            table.add_row(opt.id, opt.text)

        console.print(table)

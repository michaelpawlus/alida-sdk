"""Question resource methods for the Alida API.

Questions are accessed via the datasets/concepts API (v1):
  GET datasets/{datasetId}/concepts — returns all concepts (questions,
  survey root, system variables). Filter for tag "question".

Each question concept has extraData with:
  - text: the question text (may contain HTML)
  - questionType: OpenEnd, SingleChoice, MultipleChoice, etc.
  - choices: list of answer options with id/text/state
"""

from __future__ import annotations

from alida_sdk.client import AlidaClient
from alida_sdk.models import AnswerOption, Question


class QuestionResource:
    """Operations on questions within an Alida dataset."""

    def __init__(self, client: AlidaClient):
        self._client = client

    def list_questions(
        self,
        dataset_id: str,
        *,
        include_system: bool = False,
        search: str | None = None,
    ) -> list[Question]:
        """List all questions for a dataset.

        Args:
            dataset_id: The dataset ID (from ``datasets`` endpoint).
            include_system: If True, include system questions
                (DisplayType, RespondentLocale, etc.).
            search: Case-insensitive substring match on question name or text.
        """
        concepts = self._client.get_paginated(
            f"datasets/{dataset_id}/concepts"
        )
        questions = []
        for concept in concepts:
            tags = concept.get("tags", [])
            if "question" not in tags:
                continue
            if not include_system and "systemquestion" in tags:
                continue
            questions.append(self._to_question(dataset_id, concept))

        if search:
            search_lower = search.lower()
            questions = [
                q
                for q in questions
                if search_lower in q.name.lower() or search_lower in q.text.lower()
            ]

        return questions

    def get_question(self, dataset_id: str, question_id: str) -> Question:
        """Get a single question by ID, including answer options."""
        data = self._client.get(
            f"datasets/{dataset_id}/concepts/{question_id}"
        )
        return self._to_question(dataset_id, data)

    @staticmethod
    def _to_answer_option(data: dict) -> AnswerOption:
        """Map a choice from extraData.choices to AnswerOption model."""
        return AnswerOption(
            id=str(data.get("id", "")),
            text=data.get("text") or data.get("label") or "",
            position=None,
            raw=data,
        )

    @staticmethod
    def _to_question(dataset_id: str, data: dict) -> Question:
        """Map a concept to Question model.

        Concepts have the structure:
            {
              "id": "...",
              "name": "Q2",
              "tags": ["question", "singlechoice"],
              "orderInParent": 5,
              "extraData": {
                "text": "<p>Question text...</p>",
                "questionType": "SingleChoice",
                "choices": [{"id": "...", "text": "Yes"}, ...]
              }
            }
        """
        extra = data.get("extraData") or {}
        raw_choices = extra.get("choices") or []

        # Text: prefer extraData.text, fall back to name
        text = extra.get("text") or data.get("name") or ""

        # Question type from extraData
        question_type = extra.get("questionType") or None

        return Question(
            id=str(data.get("id", "")),
            survey_id=dataset_id,
            name=data.get("name", ""),
            text=text,
            type=question_type,
            answer_options=[
                QuestionResource._to_answer_option(choice)
                for choice in raw_choices
            ],
            raw=data,
        )

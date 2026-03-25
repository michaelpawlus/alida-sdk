"""Tests for the question resource module."""

from __future__ import annotations

from unittest.mock import MagicMock

from alida_sdk.models import AnswerOption, Question
from alida_sdk.questions import QuestionResource


def _sample_concept_open_end() -> dict:
    """A concept representing an open-ended question."""
    return {
        "id": "b52d9e99-f57c-48d9-ba7c-ff9649a662c1",
        "name": "Long Answer",
        "parentId": "4c1a8229-95c4-438b-8491-2a928f2e1f9a",
        "tags": ["question", "openend"],
        "orderInParent": 1,
        "extraData": {
            "id": "b52d9e99-f57c-48d9-ba7c-ff9649a662c1",
            "state": "Alive",
            "name": "Long Answer",
            "text": "<p>Share your favorite memory below.</p>",
            "questionType": "OpenEnd",
            "extensionType": "NotDefined",
            "choices": [],
        },
        "datasetId": "4c1a8229-95c4-438b-8491-2a928f2e1f9a",
    }


def _sample_concept_single_choice() -> dict:
    """A concept representing a single-choice question with choices."""
    return {
        "id": "4c65ece7-6d4e-47a6-bc1b-4b50895575c6",
        "name": "Q2",
        "parentId": "4c1a8229-95c4-438b-8491-2a928f2e1f9a",
        "tags": ["question", "singlechoice"],
        "orderInParent": 5,
        "extraData": {
            "id": "4c65ece7-6d4e-47a6-bc1b-4b50895575c6",
            "state": "Alive",
            "name": "Q2",
            "text": "<p>Do we have your permission?</p>",
            "questionType": "SingleChoice",
            "extensionType": "NotDefined",
            "choices": [
                {
                    "id": "c477e380-2b3a-4096-8c9f-406c28337d32",
                    "state": "Alive",
                    "answerType": "RegularAnswer",
                    "text": "Yes",
                },
                {
                    "id": "9f886d43-562d-44e4-9763-9b148c110990",
                    "state": "Alive",
                    "answerType": "RegularAnswer",
                    "text": "No",
                },
            ],
        },
        "datasetId": "4c1a8229-95c4-438b-8491-2a928f2e1f9a",
    }


def _sample_concept_system() -> dict:
    """A system question concept (should be excluded by default)."""
    return {
        "id": "fd1d474e-9ab7-42c1-8e51-71c5c82167d0",
        "name": "DisplayType",
        "tags": ["question", "singlechoice", "responsevariable", "systemquestion"],
        "orderInParent": 9,
        "extraData": {
            "questionType": "SingleChoice",
            "text": "",
            "choices": [
                {"id": "a1", "text": "Mobile"},
                {"id": "a2", "text": "Desktop"},
            ],
        },
    }


def _sample_concept_survey_root() -> dict:
    """The survey root concept (not a question — no 'question' tag)."""
    return {
        "id": "4c1a8229-95c4-438b-8491-2a928f2e1f9a",
        "name": "My Survey",
        "tags": ["survey"],
        "orderInParent": 0,
    }


class TestToQuestion:
    def test_maps_open_end(self):
        data = _sample_concept_open_end()
        q = QuestionResource._to_question("ds-001", data)
        assert isinstance(q, Question)
        assert q.id == "b52d9e99-f57c-48d9-ba7c-ff9649a662c1"
        assert q.survey_id == "ds-001"
        assert q.name == "Long Answer"
        assert q.text == "<p>Share your favorite memory below.</p>"
        assert q.type == "OpenEnd"
        assert q.answer_options == []

    def test_maps_single_choice_with_options(self):
        data = _sample_concept_single_choice()
        q = QuestionResource._to_question("ds-001", data)
        assert q.name == "Q2"
        assert q.type == "SingleChoice"
        assert len(q.answer_options) == 2
        assert q.answer_options[0].text == "Yes"
        assert q.answer_options[1].text == "No"

    def test_preserves_raw_data(self):
        data = _sample_concept_single_choice()
        q = QuestionResource._to_question("ds-001", data)
        assert q.raw == data

    def test_falls_back_to_name_when_no_text(self):
        data = {
            "id": "q1",
            "name": "Fallback Name",
            "tags": ["question"],
            "extraData": {"choices": []},
        }
        q = QuestionResource._to_question("ds-001", data)
        assert q.text == "Fallback Name"

    def test_to_dict_includes_all_fields(self):
        data = _sample_concept_single_choice()
        q = QuestionResource._to_question("ds-001", data)
        d = q.to_dict()
        assert d["id"] == "4c65ece7-6d4e-47a6-bc1b-4b50895575c6"
        assert d["survey_id"] == "ds-001"
        assert len(d["answer_options"]) == 2
        assert d["answer_options"][0]["text"] == "Yes"


class TestToAnswerOption:
    def test_maps_choice_fields(self):
        data = {
            "id": "c477e380",
            "state": "Alive",
            "answerType": "RegularAnswer",
            "text": "Yes",
        }
        opt = QuestionResource._to_answer_option(data)
        assert isinstance(opt, AnswerOption)
        assert opt.id == "c477e380"
        assert opt.text == "Yes"
        assert opt.position is None

    def test_preserves_raw_data(self):
        data = {"id": "opt-1", "text": "Maybe", "state": "Alive"}
        opt = QuestionResource._to_answer_option(data)
        assert opt.raw == data


class TestListQuestions:
    def test_filters_to_question_concepts(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = [
            _sample_concept_survey_root(),
            _sample_concept_open_end(),
            _sample_concept_single_choice(),
            _sample_concept_system(),
        ]
        resource = QuestionResource(mock_client)
        questions = resource.list_questions("ds-001")

        # Should exclude the survey root and system question
        assert len(questions) == 2
        assert questions[0].type == "OpenEnd"
        assert questions[1].type == "SingleChoice"
        mock_client.get_paginated.assert_called_once_with("datasets/ds-001/concepts")

    def test_include_system_questions(self):
        mock_client = MagicMock()
        mock_client.get_paginated.return_value = [
            _sample_concept_survey_root(),
            _sample_concept_open_end(),
            _sample_concept_system(),
        ]
        resource = QuestionResource(mock_client)
        questions = resource.list_questions("ds-001", include_system=True)

        # Should include the system question but not the survey root
        assert len(questions) == 2


class TestGetQuestion:
    def test_fetches_single_concept(self):
        mock_client = MagicMock()
        mock_client.get.return_value = _sample_concept_single_choice()
        resource = QuestionResource(mock_client)
        q = resource.get_question("ds-001", "q-id")

        assert q.type == "SingleChoice"
        mock_client.get.assert_called_once_with("datasets/ds-001/concepts/q-id")

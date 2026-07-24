from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import streamlit as st


APP_FOLDER = Path(__file__).resolve().parent
QUESTION_BANK_FOLDER = APP_FOLDER / "question_banks"


def load_sections(folder: Path) -> list[dict[str, Any]]:
    """Load and validate all question-bank JSON files."""

    sections: list[dict[str, Any]] = []

    if not folder.exists():
        st.error(f"Question-bank folder not found: {folder}")
        return sections

    for file_path in sorted(folder.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as file:
                section = json.load(file)

            required_fields = {"section_id", "title", "questions"}
            missing_fields = required_fields - section.keys()

            if missing_fields:
                st.warning(
                    f"{file_path.name} is missing: "
                    f"{', '.join(sorted(missing_fields))}"
                )
                continue

            section["_source_file"] = file_path.name
            sections.append(section)

        except json.JSONDecodeError as error:
            st.error(f"Invalid JSON in {file_path.name}: {error}")
        except OSError as error:
            st.error(f"Could not read {file_path.name}: {error}")

    return sections


def initialize_section_state(section_id: str) -> None:
    """Create section-specific session-state variables."""

    defaults = {
        f"{section_id}_submitted": False,
        f"{section_id}_selected_questions": [],
        f"{section_id}_answers": {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def generate_quiz(
    section: dict[str, Any],
    number_of_questions: int,
) -> None:
    """Randomly select questions for one section."""

    section_id = section["section_id"]
    questions = section["questions"]

    number_of_questions = min(number_of_questions, len(questions))

    st.session_state[f"{section_id}_selected_questions"] = random.sample(
        questions,
        number_of_questions,
    )
    st.session_state[f"{section_id}_answers"] = {}
    st.session_state[f"{section_id}_submitted"] = False


def display_question(
    question: dict[str, Any],
    section_id: str,
    question_number: int,
) -> None:
    """Display one MCQ and save the selected answer."""

    question_id = question["id"]
    choices = question["choices"]

    st.markdown(f"### Question {question_number}")
    st.write(question["question"])

    choice_keys = list(choices.keys())

    selected_answer = st.radio(
        label="Select your answer:",
        options=choice_keys,
        format_func=lambda key: f"{key}. {choices[key]}",
        key=f"radio_{section_id}_{question_id}",
        index=None,
    )

    if selected_answer is not None:
        st.session_state[f"{section_id}_answers"][question_id] = selected_answer


def display_results(
    questions: list[dict[str, Any]],
    submitted_answers: dict[str, str],
) -> None:
    """Grade the quiz and display explanations."""

    correct_count = 0

    for number, question in enumerate(questions, start=1):
        question_id = question["id"]
        correct_answer = question["answer"]
        student_answer = submitted_answers.get(question_id)

        if student_answer == correct_answer:
            correct_count += 1
            result = "Correct"
        elif student_answer is None:
            result = "Not answered"
        else:
            result = "Incorrect"

        st.markdown("---")
        st.markdown(f"#### Question {number}: {result}")
        st.write(question["question"])

        st.write(
            f"**Your answer:** "
            f"{student_answer if student_answer else 'No answer'}"
        )
        st.write(f"**Correct answer:** {correct_answer}")
        st.info(question.get("explanation", "No explanation available."))

    total_questions = len(questions)
    percentage = (
        100 * correct_count / total_questions if total_questions else 0
    )

    st.markdown("---")
    st.metric(
        label="Quiz score",
        value=f"{correct_count}/{total_questions}",
        delta=f"{percentage:.1f}%",
    )


def display_section(section: dict[str, Any]) -> None:
    """Display controls and quiz content for one section."""

    section_id = section["section_id"]
    questions = section["questions"]

    initialize_section_state(section_id)

    st.subheader(section["title"])

    if section.get("description"):
        st.write(section["description"])

    st.caption(f"Available questions: {len(questions)}")

    if not questions:
        st.warning("No questions have been added to this section.")
        return

    default_number = min(10, len(questions))

    number_of_questions = st.number_input(
        "Number of questions",
        min_value=1,
        max_value=len(questions),
        value=default_number,
        step=1,
        key=f"number_{section_id}",
    )

    if st.button(
        "Generate quiz",
        key=f"generate_{section_id}",
        type="primary",
    ):
        generate_quiz(section, int(number_of_questions))
        st.rerun()

    selected_questions = st.session_state[
        f"{section_id}_selected_questions"
    ]

    if not selected_questions:
        st.info("Select the number of questions and generate a quiz.")
        return

    answers = st.session_state[f"{section_id}_answers"]
    submitted = st.session_state[f"{section_id}_submitted"]

    if not submitted:
        for number, question in enumerate(selected_questions, start=1):
            display_question(
                question=question,
                section_id=section_id,
                question_number=number,
            )

        answered_count = len(answers)
        total_count = len(selected_questions)

        st.write(f"Answered: {answered_count} of {total_count}")

        if st.button(
            "Submit quiz",
            key=f"submit_{section_id}",
            disabled=answered_count == 0,
        ):
            st.session_state[f"{section_id}_submitted"] = True
            st.rerun()

    else:
        display_results(selected_questions, answers)

        if st.button(
            "Start a new quiz",
            key=f"restart_{section_id}",
        ):
            generate_quiz(section, int(number_of_questions))
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="MEEN 368 MCQ Practice",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("MEEN 368 MCQ Practice")

    st.write(
        "Select a topic, generate a randomized quiz, and review "
        "the answers and explanations."
    )

    sections = load_sections(QUESTION_BANK_FOLDER)

    if not sections:
        st.error("No valid question-bank files were found.")
        st.stop()

    section_titles = [
        f"{section['section_id']}. {section['title']} "
        f"({len(section['questions'])} questions)"
        for section in sections
    ]

    st.subheader("Select a Section")

    selected_title = st.radio(
        label="Choose a topic",
        options=section_titles,
        label_visibility="collapsed",
        key="section_selector",
    )

    selected_index = section_titles.index(selected_title)
    selected_section = sections[selected_index]

    st.markdown("---")

    display_section(selected_section)


if __name__ == "__main__":
    main()

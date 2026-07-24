from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import streamlit as st


# ============================================================
# FILE LOCATIONS
# ============================================================

APP_FOLDER = Path(__file__).resolve().parent
QUESTION_BANK_FOLDER = APP_FOLDER / "question_banks"


# ============================================================
# SECTION ICONS
# ============================================================

SECTION_ICONS = {
    "01": "📐",
    "02": "📊",
    "03": "🔩",
    "04": "🏗️",
    "05": "🌀",
    "06": "⚙️",
    "07": "🛢️",
    "08": "⚙️",
    "09": "📏",
    "10": "🧭",
}


# ============================================================
# DATA LOADING
# ============================================================

def load_sections(folder: Path) -> list[dict[str, Any]]:
    """Load all valid JSON question-bank files."""

    sections: list[dict[str, Any]] = []

    if not folder.exists():
        st.error(f"Question-bank folder not found: {folder}")
        return sections

    for file_path in sorted(folder.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as file:
                section = json.load(file)

            required_fields = {
                "section_id",
                "title",
                "questions",
            }

            missing_fields = required_fields - section.keys()

            if missing_fields:
                st.warning(
                    f"{file_path.name} is missing required fields: "
                    f"{', '.join(sorted(missing_fields))}"
                )
                continue

            section["section_id"] = str(section["section_id"])
            section["_source_file"] = file_path.name

            sections.append(section)

        except json.JSONDecodeError as error:
            st.error(
                f"Invalid JSON in {file_path.name}: {error}"
            )

        except OSError as error:
            st.error(
                f"Could not read {file_path.name}: {error}"
            )

    return sections


def find_section(
    sections: list[dict[str, Any]],
    section_id: str,
) -> dict[str, Any] | None:
    """Find one section using its section ID."""

    for section in sections:
        if str(section["section_id"]) == str(section_id):
            return section

    return None


def get_all_questions(
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine questions from all sections."""

    all_questions: list[dict[str, Any]] = []

    for section in sections:
        all_questions.extend(
            section.get("questions", [])
        )

    return all_questions


def get_section_icon(section_id: str) -> str:
    """Return an icon for a section."""

    return SECTION_ICONS.get(
        str(section_id),
        "📘",
    )


# ============================================================
# DIFFICULTY FUNCTIONS
# ============================================================

def count_difficulties(
    questions: list[dict[str, Any]],
) -> dict[str, int]:
    """Count questions by difficulty."""

    counts = {
        "Basic": 0,
        "Intermediate": 0,
        "Advanced": 0,
        "Unspecified": 0,
    }

    for question in questions:
        difficulty = question.get(
            "difficulty",
            "Unspecified",
        )

        if difficulty not in counts:
            difficulty = "Unspecified"

        counts[difficulty] += 1

    return counts


def filter_questions_by_difficulty(
    questions: list[dict[str, Any]],
    selected_difficulty: str,
) -> list[dict[str, Any]]:
    """Filter questions by difficulty."""

    if selected_difficulty == "Mixed":
        return questions

    return [
        question
        for question in questions
        if question.get(
            "difficulty",
            "Unspecified",
        ) == selected_difficulty
    ]


# ============================================================
# NAVIGATION STATE
# ============================================================

def initialize_navigation_state() -> None:
    """Initialize page-navigation session variables."""

    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    if "selected_section_id" not in st.session_state:
        st.session_state.selected_section_id = None


def open_section(section_id: str) -> None:
    """Open a selected section."""

    st.session_state.selected_section_id = str(
        section_id
    )

    st.session_state.current_page = "section"


def return_home() -> None:
    """Return to the topic-selection page."""

    st.session_state.current_page = "home"
    st.session_state.selected_section_id = None


# ============================================================
# QUIZ STATE
# ============================================================

def initialize_section_state(section_id: str) -> None:
    """Initialize quiz state for one section."""

    defaults = {
        f"{section_id}_selected_questions": [],
        f"{section_id}_answers": {},
        f"{section_id}_submitted": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_section_quiz(section_id: str) -> None:
    """Clear the current quiz for a section."""

    st.session_state[
        f"{section_id}_selected_questions"
    ] = []

    st.session_state[
        f"{section_id}_answers"
    ] = {}

    st.session_state[
        f"{section_id}_submitted"
    ] = False


def generate_quiz(
    section: dict[str, Any],
    number_of_questions: int,
    difficulty: str,
    question_order: str,
) -> None:
    """Generate a filtered random or sequential quiz."""

    section_id = str(section["section_id"])

    available_questions = (
        filter_questions_by_difficulty(
            section.get("questions", []),
            difficulty,
        )
    )

    if not available_questions:
        clear_section_quiz(section_id)
        return

    number_of_questions = min(
        number_of_questions,
        len(available_questions),
    )

    if question_order == "Sequential":
        selected_questions = (
            available_questions[
                :number_of_questions
            ]
        )
    else:
        selected_questions = random.sample(
            available_questions,
            number_of_questions,
        )

    st.session_state[
        f"{section_id}_selected_questions"
    ] = selected_questions

    st.session_state[
        f"{section_id}_answers"
    ] = {}

    st.session_state[
        f"{section_id}_submitted"
    ] = False


# ============================================================
# HOME PAGE
# ============================================================

def display_dashboard_statistics(
    sections: list[dict[str, Any]],
) -> None:
    """Display overall question-bank statistics."""

    all_questions = get_all_questions(sections)

    total_topics = len(sections)
    total_questions = len(all_questions)

    active_topics = sum(
        1
        for section in sections
        if len(section.get("questions", [])) > 0
    )

    difficulty_counts = count_difficulties(
        all_questions
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Topics",
        total_topics,
    )

    col2.metric(
        "Questions",
        total_questions,
    )

    col3.metric(
        "Active Topics",
        active_topics,
    )

    col4.metric(
        "Advanced Questions",
        difficulty_counts["Advanced"],
    )


def display_topic_cards(
    sections: list[dict[str, Any]],
) -> None:
    """Display sections as vertical topic cards."""

    st.subheader("Available Topics")

    search_text = st.text_input(
        "Search topics",
        placeholder=(
            "Search by section number, title, "
            "or description"
        ),
    )

    normalized_search = search_text.strip().lower()

    visible_sections: list[dict[str, Any]] = []

    for section in sections:
        searchable_text = " ".join(
            [
                str(section.get("section_id", "")),
                section.get("title", ""),
                section.get("description", ""),
            ]
        ).lower()

        if (
            not normalized_search
            or normalized_search in searchable_text
        ):
            visible_sections.append(section)

    if not visible_sections:
        st.warning(
            "No topics match your search."
        )
        return

    for section in visible_sections:
        section_id = str(section["section_id"])
        title = section["title"]
        questions = section.get("questions", [])
        question_count = len(questions)

        description = section.get(
            "description",
            "No description is available.",
        )

        icon = get_section_icon(section_id)

        difficulty_counts = count_difficulties(
            questions
        )

        with st.container(border=True):
            title_col, count_col = st.columns(
                [5, 1]
            )

            with title_col:
                st.markdown(
                    f"### {icon} {section_id}. {title}"
                )

            with count_col:
                st.metric(
                    "Questions",
                    question_count,
                )

            st.write(description)

            st.caption(
                f"Basic: "
                f"{difficulty_counts['Basic']}  ·  "
                f"Intermediate: "
                f"{difficulty_counts['Intermediate']}  ·  "
                f"Advanced: "
                f"{difficulty_counts['Advanced']}"
            )

            if question_count == 0:
                st.button(
                    "No Questions Available",
                    key=f"empty_{section_id}",
                    disabled=True,
                    use_container_width=True,
                )

            else:
                if st.button(
                    "Open Section",
                    key=f"open_{section_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    open_section(section_id)
                    st.rerun()


def display_home_page(
    sections: list[dict[str, Any]],
) -> None:
    """Display the main topic-selection page."""

    st.title("MEEN 368 MCQ Practice")

    st.write(
        "Learn core mechanical-design concepts, "
        "practice with randomized questions, and "
        "test your knowledge using challenge quizzes."
    )

    display_dashboard_statistics(sections)

    st.divider()

    display_topic_cards(sections)


# ============================================================
# LEARN MODE
# ============================================================

def display_learn_mode(
    section: dict[str, Any],
) -> None:
    """Display questions, choices, answers, and explanations."""

    section_id = str(section["section_id"])

    questions = section.get(
        "questions",
        [],
    )

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        difficulty = st.selectbox(
            "Difficulty",
            options=[
                "Mixed",
                "Basic",
                "Intermediate",
                "Advanced",
            ],
            key=f"learn_difficulty_{section_id}",
        )

    with filter_col2:
        search_text = st.text_input(
            "Search questions",
            placeholder=(
                "Search question text, explanations, "
                "or tags"
            ),
            key=f"learn_search_{section_id}",
        )

    filtered_questions = (
        filter_questions_by_difficulty(
            questions,
            difficulty,
        )
    )

    normalized_search = search_text.strip().lower()

    if normalized_search:
        matching_questions = []

        for question in filtered_questions:
            searchable_text = " ".join(
                [
                    question.get("question", ""),
                    question.get(
                        "explanation",
                        "",
                    ),
                    " ".join(
                        question.get(
                            "tags",
                            [],
                        )
                    ),
                ]
            ).lower()

            if normalized_search in searchable_text:
                matching_questions.append(question)

        filtered_questions = matching_questions

    st.caption(
        f"Showing {len(filtered_questions)} "
        f"of {len(questions)} questions"
    )

    if not filtered_questions:
        st.info(
            "No questions match the selected filters."
        )
        return

    for number, question in enumerate(
        filtered_questions,
        start=1,
    ):
        question_text = question.get(
            "question",
            "Question text unavailable.",
        )

        with st.expander(
            f"{number}. {question_text}"
        ):
            choices = question.get(
                "choices",
                {},
            )

            for letter, choice in choices.items():
                st.write(
                    f"**{letter}.** {choice}"
                )

            correct_answer = question.get(
                "answer",
                "Not specified",
            )

            st.success(
                f"Correct answer: {correct_answer}"
            )

            explanation = question.get(
                "explanation",
                "No explanation is available.",
            )

            st.info(explanation)

            difficulty_value = question.get(
                "difficulty",
                "Unspecified",
            )

            tags = question.get(
                "tags",
                [],
            )

            details = (
                f"Difficulty: {difficulty_value}"
            )

            if tags:
                details += (
                    "  ·  Tags: "
                    + ", ".join(tags)
                )

            st.caption(details)


# ============================================================
# QUIZ DISPLAY
# ============================================================

def display_question(
    question: dict[str, Any],
    section_id: str,
    question_number: int,
) -> None:
    """Display one multiple-choice question."""

    question_id = question["id"]
    choices = question.get("choices", {})

    st.markdown(
        f"### Question {question_number}"
    )

    st.write(
        question.get(
            "question",
            "Question text unavailable.",
        )
    )

    choice_keys = list(choices.keys())

    selected_answer = st.radio(
        "Select your answer",
        options=choice_keys,
        format_func=lambda key: (
            f"{key}. {choices[key]}"
        ),
        key=(
            f"answer_{section_id}_{question_id}"
        ),
        index=None,
    )

    if selected_answer is not None:
        st.session_state[
            f"{section_id}_answers"
        ][question_id] = selected_answer

    st.divider()


def display_results(
    questions: list[dict[str, Any]],
    submitted_answers: dict[str, str],
) -> None:
    """Grade the quiz and display explanations."""

    correct_count = 0

    for number, question in enumerate(
        questions,
        start=1,
    ):
        question_id = question["id"]

        correct_answer = question.get(
            "answer",
            "",
        )

        student_answer = submitted_answers.get(
            question_id
        )

        choices = question.get(
            "choices",
            {},
        )

        is_correct = (
            student_answer == correct_answer
        )

        if is_correct:
            correct_count += 1
            result_text = "Correct"
        elif student_answer is None:
            result_text = "Not Answered"
        else:
            result_text = "Incorrect"

        st.markdown(
            f"### Question {number}: {result_text}"
        )

        st.write(
            question.get(
                "question",
                "Question text unavailable.",
            )
        )

        if student_answer is None:
            st.write(
                "**Your answer:** No answer"
            )
        else:
            student_choice_text = choices.get(
                student_answer,
                "",
            )

            st.write(
                f"**Your answer:** "
                f"{student_answer}. "
                f"{student_choice_text}"
            )

        correct_choice_text = choices.get(
            correct_answer,
            "",
        )

        st.write(
            f"**Correct answer:** "
            f"{correct_answer}. "
            f"{correct_choice_text}"
        )

        if is_correct:
            st.success("Correct")
        else:
            st.error(result_text)

        st.info(
            question.get(
                "explanation",
                "No explanation is available.",
            )
        )

        st.divider()

    total_questions = len(questions)

    percentage = (
        100 * correct_count / total_questions
        if total_questions
        else 0
    )

    st.subheader("Quiz Results")

    result_col1, result_col2 = st.columns(2)

    result_col1.metric(
        "Score",
        f"{correct_count}/{total_questions}",
    )

    result_col2.metric(
        "Percentage",
        f"{percentage:.1f}%",
    )


def display_quiz_mode(
    section: dict[str, Any],
    challenge_mode: bool,
) -> None:
    """Display Practice or Challenge mode."""

    section_id = str(section["section_id"])
    questions = section.get("questions", [])

    initialize_section_state(section_id)

    settings_col1, settings_col2 = st.columns(2)

    with settings_col1:
        difficulty = st.selectbox(
            "Difficulty",
            options=[
                "Mixed",
                "Basic",
                "Intermediate",
                "Advanced",
            ],
            key=(
                f"quiz_difficulty_"
                f"{section_id}_"
                f"{challenge_mode}"
            ),
        )

    available_questions = (
        filter_questions_by_difficulty(
            questions,
            difficulty,
        )
    )

    with settings_col2:
        question_order = st.selectbox(
            "Question order",
            options=[
                "Random",
                "Sequential",
            ],
            key=(
                f"question_order_"
                f"{section_id}_"
                f"{challenge_mode}"
            ),
        )

    if not available_questions:
        st.warning(
            "No questions are available for "
            "the selected difficulty."
        )
        return

    number_of_questions = st.number_input(
        "Number of questions",
        min_value=1,
        max_value=len(available_questions),
        value=min(
            10,
            len(available_questions),
        ),
        step=1,
        key=(
            f"number_questions_"
            f"{section_id}_"
            f"{challenge_mode}"
        ),
    )

    if challenge_mode:
        suggested_time = max(
            5,
            int(number_of_questions),
        )

        st.info(
            f"Challenge mode: try to complete this "
            f"quiz in approximately "
            f"{suggested_time} minutes. Answers and "
            f"explanations will appear only after "
            f"submission."
        )

    else:
        st.info(
            "Practice mode: complete the questions "
            "and submit the quiz to view your score, "
            "correct answers, and explanations."
        )

    if st.button(
        "Generate Quiz",
        key=(
            f"generate_"
            f"{section_id}_"
            f"{challenge_mode}"
        ),
        type="primary",
    ):
        generate_quiz(
            section=section,
            number_of_questions=int(
                number_of_questions
            ),
            difficulty=difficulty,
            question_order=question_order,
        )

        st.rerun()

    selected_questions = st.session_state[
        f"{section_id}_selected_questions"
    ]

    submitted_answers = st.session_state[
        f"{section_id}_answers"
    ]

    submitted = st.session_state[
        f"{section_id}_submitted"
    ]

    if not selected_questions:
        st.caption(
            "Choose the quiz settings and "
            "generate a quiz."
        )
        return

    st.divider()

    if not submitted:
        for number, question in enumerate(
            selected_questions,
            start=1,
        ):
            display_question(
                question=question,
                section_id=section_id,
                question_number=number,
            )

        answered_count = len(
            submitted_answers
        )

        total_count = len(
            selected_questions
        )

        progress = (
            answered_count / total_count
            if total_count
            else 0
        )

        st.progress(
            progress,
            text=(
                f"Answered {answered_count} "
                f"of {total_count} questions"
            ),
        )

        if st.button(
            "Submit Quiz",
            key=(
                f"submit_"
                f"{section_id}_"
                f"{challenge_mode}"
            ),
            type="primary",
            disabled=answered_count == 0,
        ):
            st.session_state[
                f"{section_id}_submitted"
            ] = True

            st.rerun()

    else:
        display_results(
            selected_questions,
            submitted_answers,
        )

        if st.button(
            "Generate Another Quiz",
            key=(
                f"another_"
                f"{section_id}_"
                f"{challenge_mode}"
            ),
            type="primary",
        ):
            generate_quiz(
                section=section,
                number_of_questions=int(
                    number_of_questions
                ),
                difficulty=difficulty,
                question_order=question_order,
            )

            st.rerun()

        if st.button(
            "Clear Quiz",
            key=(
                f"clear_"
                f"{section_id}_"
                f"{challenge_mode}"
            ),
        ):
            clear_section_quiz(section_id)
            st.rerun()


# ============================================================
# SECTION PAGE
# ============================================================

def display_section_page(
    section: dict[str, Any],
) -> None:
    """Display one selected section."""

    section_id = str(section["section_id"])
    title = section["title"]

    questions = section.get(
        "questions",
        [],
    )

    icon = get_section_icon(section_id)

    if st.button(
        "← Back to Topics",
        key=f"back_{section_id}",
    ):
        return_home()
        st.rerun()

    st.title(
        f"{icon} {title}"
    )

    description = section.get(
        "description",
        "",
    )

    if description:
        st.write(description)

    difficulty_counts = count_difficulties(
        questions
    )

    stat_col1, stat_col2, stat_col3, stat_col4 = (
        st.columns(4)
    )

    stat_col1.metric(
        "Questions",
        len(questions),
    )

    stat_col2.metric(
        "Basic",
        difficulty_counts["Basic"],
    )

    stat_col3.metric(
        "Intermediate",
        difficulty_counts[
            "Intermediate"
        ],
    )

    stat_col4.metric(
        "Advanced",
        difficulty_counts["Advanced"],
    )

    if not questions:
        st.warning(
            "No questions have been added "
            "to this section."
        )
        return

    st.divider()

    mode = st.radio(
        "Select a learning mode",
        options=[
            "Learn",
            "Practice",
            "Challenge",
        ],
        horizontal=True,
        key=f"mode_{section_id}",
    )

    st.divider()

    if mode == "Learn":
        display_learn_mode(section)

    elif mode == "Challenge":
        display_quiz_mode(
            section,
            challenge_mode=True,
        )

    else:
        display_quiz_mode(
            section,
            challenge_mode=False,
        )


# ============================================================
# MAIN APPLICATION
# ============================================================

def main() -> None:
    st.set_page_config(
        page_title="MEEN 368 MCQ Practice",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    initialize_navigation_state()

    sections = load_sections(
        QUESTION_BANK_FOLDER
    )

    if not sections:
        st.error(
            "No valid question-bank files "
            "were found."
        )
        st.stop()

    if st.session_state.current_page == "home":
        display_home_page(sections)

    elif (
        st.session_state.current_page
        == "section"
    ):
        selected_section = find_section(
            sections,
            st.session_state.selected_section_id,
        )

        if selected_section is None:
            st.error(
                "The selected section could "
                "not be found."
            )

            if st.button(
                "Return to Topics"
            ):
                return_home()
                st.rerun()

            return

        display_section_page(
            selected_section
        )


if __name__ == "__main__":
    main()

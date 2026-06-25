import streamlit as st
from google import genai
from pypdf import PdfReader
from pathlib import Path

st.set_page_config(
    page_title="Gusset Plate Design Coach",
    page_icon="🧠",
    layout="wide"
)

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

BASE_DIR = Path(__file__).parent

SOLUTION_FILE = BASE_DIR / "Solution.pdf"
UNLOCK_COUNT = 10
GEMINI_MODEL = "gemini-3.5-flash"

SYSTEM_PROMPT = """
You are a Gusset Plate Mechanics Coach implementing cognitive apprenticeship.

Never provide final numerical answers.

Ask Socratic questions that guide students through:
1. Load path
2. Mechanism prediction
3. Modeling assumptions
4. Physical interpretation
5. Verification and reflection

Guide but do not confirm or deny conclusions immediately.
Keep responses concise, organized, and focused on mechanics reasoning.
"""

SOLUTION_EXPLAINER_PROMPT = """
You are explaining an instructor-provided solution.

Rules:
- The instructor solution is authoritative.
- Do not create a new solution.
- Do not change numerical values.
- Do not introduce unsupported equations.
- Explain only the reasoning in the provided solution.
- If the solution excerpt is unclear or incomplete, say so.
- Focus on physical interpretation, assumptions, governing mechanisms, and verification.
"""

examples = {
    "Thin plate": "I think tension governs because the plate is thin.",
    "Increase thickness": "If thickness doubles, does the governing mechanism change?",
    "Bearing stress": "I think bearing stress at the bolt holes controls.",
    "Block shear": "Could block shear failure govern?",
    "Buckling concern": "Could out-of-plane buckling occur?",
    "Stiffness": "Which geometric parameters most affect stiffness?",
    "Load path question": "How does the load flow through the gusset plate?"
}

def ask_gemini(system_prompt, user_input):
    response = client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=system_prompt,
        input=user_input,
        store=False
    )
    return response.output_text

if "coach_count" not in st.session_state:
    st.session_state.coach_count = 0

st.title("TAMU Mechanics: Gusset Plate Design Coach")
st.caption("AI as a cognitive apprenticeship scaffold")

main_tab, solution_tab, concept_tab = st.tabs(
    ["AI Coach", "Solution Access", "Concept Review"]
)

with main_tab:
    example = st.selectbox("Example scenario", list(examples.keys()))

    col1, col2 = st.columns([1, 2])

    with col1:
        st.image(BASE_DIR / "GussetPlate.png", caption="F63-5 Gusset Plate")

    with col2:
        student_input = st.text_area(
            "Student reasoning",
            value=examples[example],
            height=140,
            key="student_reasoning"
        )

        st.write(f"Coaching interactions used: **{st.session_state.coach_count}/{UNLOCK_COUNT}**")

        if st.button("Coach Me", key="coach_button"):
            st.session_state.coach_count += 1

            with st.spinner("Thinking like a mechanics coach..."):
                try:
                    answer = ask_gemini(SYSTEM_PROMPT, student_input)
                    st.markdown("## AI-Guided Prompt")
                    st.success(answer)
                except Exception as e:
                    st.error(f"Gemini API error: {e}")

    if st.session_state.coach_count < UNLOCK_COUNT:
        remaining = UNLOCK_COUNT - st.session_state.coach_count
        st.info(f"Complete {remaining} more coaching interaction(s) to unlock the instructor solution.")
    else:
        st.success("Instructor solution is now unlocked. Go to the Solution Access tab.")

with solution_tab:
    st.header("Instructor Solution")

    if st.session_state.coach_count < UNLOCK_COUNT:
        st.warning(
            f"The solution is locked. Complete {UNLOCK_COUNT} AI coaching interactions first."
        )

    else:
        st.success("Solution unlocked.")

        with open(SOLUTION_FILE, "rb") as f:
            st.download_button(
                label="Download Instructor Solution PDF",
                data=f,
                file_name="Solution.pdf",
                mime="application/pdf"
            )

        st.markdown("### Ask AI to explain the instructor solution")

        try:
            reader = PdfReader(str(SOLUTION_FILE))
            solution_text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    solution_text += page_text + "\n"

            if len(solution_text) > 12000:
                solution_text = solution_text[:12000]

        except Exception:
            solution_text = ""

        if not solution_text:
            st.warning(
                "Could not automatically read the PDF text. Paste the relevant solution step below."
            )
            solution_text = st.text_area(
                "Paste solution step or excerpt",
                height=250,
                key="manual_solution_text"
            )
        else:
            with st.expander("View extracted solution text"):
                st.write(solution_text)

        student_question = st.text_area(
            "What do you want explained?",
            "Explain why bearing stress governs instead of net-section stress.",
            height=100,
            key="solution_question"
        )

        if st.button("Explain Instructor Solution", key="explain_solution"):
            prompt = f"""
Instructor solution:
{solution_text}

Student question:
{student_question}
"""

            with st.spinner("Explaining the instructor solution..."):
                try:
                    explanation = ask_gemini(SOLUTION_EXPLAINER_PROMPT, prompt)
                    st.markdown("## Explanation")
                    st.info(explanation)
                except Exception as e:
                    st.error(f"Gemini API error: {e}")

with concept_tab:
    tab1, tab2, tab3 = st.tabs(["Strength", "Stability", "Stiffness"])

    with tab1:
        st.markdown("""
### Strength Considerations
- Bearing stress at bolt holes
- Net-section fracture
- Block shear
- Yielding

**Coaching focus:**  
Where does the load enter the plate, and which regions experience localized contact pressure?
""")

    with tab2:
        st.markdown("""
### Stability Considerations
- Compression zones
- Out-of-plane buckling
- Effective width effects
- Boundary restraint from bolt groups

**Coaching focus:**  
Could any part of the gusset plate behave like a compressed plate or strip?
""")

    with tab3:
        st.markdown("""
### Stiffness Considerations
- Load path
- Compliance
- Deformation mechanisms
- Plate thickness and geometry effects

**Coaching focus:**  
Is deformation dominated by axial membrane action, bending, or joint rotation?
""")

st.markdown("---")
st.caption("MEEN 368 Mechanics Coach | Reasoning-first, verification-focused AI support")

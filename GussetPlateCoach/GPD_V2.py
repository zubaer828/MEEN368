"""
TAMU MEEN 368: Gusset Plate Design Coach

Users enter their own Gemini API key in the sidebar.
Get a free key from:
https://aistudio.google.com/apikey
"""

from pathlib import Path

import streamlit as st
from pypdf import PdfReader

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None


# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gusset Plate Design Coach",
    page_icon="🧠",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
SOLUTION_FILE = BASE_DIR / "Solution.pdf"
IMAGE_FILE = BASE_DIR / "GussetPlate.png"

UNLOCK_COUNT = 10
GEMINI_MODEL = "gemini-2.5-flash"


# -----------------------------------------------------------------------------
# Prompts
# -----------------------------------------------------------------------------
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
Ask 1-3 targeted questions at the end.
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

EXAMPLES = {
    "Thin plate": "I think tension governs because the plate is thin.",
    "Increase thickness": "If thickness doubles, does the governing mechanism change?",
    "Bearing stress": "I think bearing stress at the bolt holes controls.",
    "Block shear": "Could block shear failure govern?",
    "Buckling concern": "Could out-of-plane buckling occur?",
    "Stiffness": "Which geometric parameters most affect stiffness?",
    "Load path question": "How does the load flow through the gusset plate?",
}


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def get_client(api_key: str):
    if genai is None:
        return None

    if not api_key:
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def ask_gemini(client, system_prompt: str, user_input: str) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_input,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.35,
        ),
    )
    return response.text


def extract_solution_text() -> str:
    if not SOLUTION_FILE.exists():
        return ""

    try:
        reader = PdfReader(str(SOLUTION_FILE))
        solution_text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                solution_text += page_text + "\n"

        return solution_text[:12000]

    except Exception:
        return ""


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "coach_count" not in st.session_state:
    st.session_state.coach_count = 0

if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = ""


# -----------------------------------------------------------------------------
# Sidebar: Gemini API key
# -----------------------------------------------------------------------------
st.sidebar.header("🔑 Gemini API Key")

st.sidebar.markdown(
    """
This app uses **your own Gemini API key**.

1. Go to: https://aistudio.google.com/apikey  
2. Create a free API key.  
3. Paste it below.

**Privacy Notice**

Your Gemini API key is used only to communicate directly with Google's Gemini API during your current browser session.

This application does **not** store, log, transmit, or share your API key with the app creator or any third party.
"""
)

api_key = st.sidebar.text_input(
    "Enter your Gemini API key",
    value=st.session_state.gemini_api_key,
    type="password",
    placeholder="Paste your Gemini API key here...",
)

st.session_state.gemini_api_key = api_key

client = get_client(api_key)

if genai is None or types is None:
    st.sidebar.error("google-genai is not installed. Check requirements.txt.")
elif api_key and client is not None:
    st.sidebar.success("Gemini connected.")
elif api_key and client is None:
    st.sidebar.error("Could not connect to Gemini. Check the API key.")
else:
    st.sidebar.warning("Enter a Gemini API key to enable AI coaching.")


# -----------------------------------------------------------------------------
# Main app
# -----------------------------------------------------------------------------
st.title("TAMU Mechanics: Gusset Plate Design Coach")
st.caption("AI as a cognitive apprenticeship scaffold")

st.info(
    """
**Open Educational Resource**

This AI Coach is freely available for educational use. Users supply their own free Gemini API key from Google AI Studio. The app does not store or share your API key.
"""
)

main_tab, solution_tab, concept_tab = st.tabs(
    ["AI Coach", "Solution Access", "Concept Review"]
)


# -----------------------------------------------------------------------------
# AI Coach tab
# -----------------------------------------------------------------------------
with main_tab:
    example = st.selectbox("Example scenario", list(EXAMPLES.keys()))

    col1, col2 = st.columns([1, 2])

    with col1:
        if IMAGE_FILE.exists():
            st.image(IMAGE_FILE, caption="F63-5 Gusset Plate")
        else:
            st.warning("GussetPlate.png was not found in the app folder.")

    with col2:
        student_input = st.text_area(
            "Student reasoning",
            value=EXAMPLES[example],
            height=140,
            key="student_reasoning",
        )

        st.write(
            f"Coaching interactions used: **{st.session_state.coach_count}/{UNLOCK_COUNT}**"
        )

        if client is None:
            st.warning("Enter your Gemini API key in the sidebar to enable AI coaching.")

        else:
            if st.button("Coach Me", key="coach_button"):
                st.session_state.coach_count += 1

                with st.spinner("Thinking like a mechanics coach..."):
                    try:
                        answer = ask_gemini(client, SYSTEM_PROMPT, student_input)
                        st.markdown("## AI-Guided Prompt")
                        st.success(answer)
                    except Exception as e:
                        st.error(f"Gemini API error: {e}")

    if st.session_state.coach_count < UNLOCK_COUNT:
        remaining = UNLOCK_COUNT - st.session_state.coach_count
        st.info(
            f"Complete {remaining} more coaching interaction(s) to unlock the instructor solution."
        )
    else:
        st.success("Instructor solution is now unlocked. Go to the Solution Access tab.")


# -----------------------------------------------------------------------------
# Solution Access tab
# -----------------------------------------------------------------------------
with solution_tab:
    st.header("Instructor Solution")

    if st.session_state.coach_count < UNLOCK_COUNT:
        st.warning(
            f"The solution is locked. Complete {UNLOCK_COUNT} AI coaching interactions first."
        )

    else:
        st.success("Solution unlocked.")

        if SOLUTION_FILE.exists():
            with open(SOLUTION_FILE, "rb") as f:
                st.download_button(
                    label="Download Instructor Solution PDF",
                    data=f,
                    file_name="Solution.pdf",
                    mime="application/pdf",
                )
        else:
            st.error("Solution.pdf was not found in the app folder.")

        st.markdown("### Ask AI to explain the instructor solution")

        solution_text = extract_solution_text()

        if not solution_text:
            st.warning(
                "Could not automatically read the PDF text. Paste the relevant solution step below."
            )
            solution_text = st.text_area(
                "Paste solution step or excerpt",
                height=250,
                key="manual_solution_text",
            )
        else:
            with st.expander("View extracted solution text"):
                st.write(solution_text)

        student_question = st.text_area(
            "What do you want explained?",
            "Explain why bearing stress governs instead of net-section stress.",
            height=100,
            key="solution_question",
        )

        if client is None:
            st.warning("Enter your Gemini API key in the sidebar to enable AI explanation.")

        else:
            if st.button("Explain Instructor Solution", key="explain_solution"):
                prompt = f"""
Instructor solution:
{solution_text}

Student question:
{student_question}
"""

                with st.spinner("Explaining the instructor solution..."):
                    try:
                        explanation = ask_gemini(
                            client,
                            SOLUTION_EXPLAINER_PROMPT,
                            prompt,
                        )
                        st.markdown("## Explanation")
                        st.info(explanation)
                    except Exception as e:
                        st.error(f"Gemini API error: {e}")


# -----------------------------------------------------------------------------
# Concept Review tab
# -----------------------------------------------------------------------------
with concept_tab:
    tab1, tab2, tab3 = st.tabs(["Strength", "Stability", "Stiffness"])

    with tab1:
        st.markdown(
            """
### Strength Considerations

- Bearing stress at bolt holes
- Net-section fracture
- Block shear
- Yielding

**Coaching focus:**  
Where does the load enter the plate, and which regions experience localized contact pressure?
"""
        )

    with tab2:
        st.markdown(
            """
### Stability Considerations

- Compression zones
- Out-of-plane buckling
- Effective width effects
- Boundary restraint from bolt groups

**Coaching focus:**  
Could any part of the gusset plate behave like a compressed plate or strip?
"""
        )

    with tab3:
        st.markdown(
            """
### Stiffness Considerations

- Load path
- Compliance
- Deformation mechanisms
- Plate thickness and geometry effects

**Coaching focus:**  
Is deformation dominated by axial membrane action, bending, or joint rotation?
"""
        )


st.markdown("---")
st.caption("MEEN 368 Mechanics Coach | Reasoning-first, verification-focused AI support")

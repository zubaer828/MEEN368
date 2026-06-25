"""
TAMU MEEN 368: Stepped Shaft Fatigue Design Coach

For Streamlit Community Cloud, add this in secrets:
GEMINI_API_KEY = "your-gemini-api-key"
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


st.set_page_config(
    page_title="Stepped Shaft Fatigue Design Coach",
    page_icon="🧠",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
SOLUTION_FILE = BASE_DIR / "L19_FatigueExample2.pdf"
NOTEBOOK_FILE = BASE_DIR / "FatigueSteppedShaft.ipynb"
UNLOCK_COUNT = 8
GEMINI_MODEL = "gemini-2.5-flash"


SYSTEM_PROMPT = """
You are a MEEN 368 Stepped Shaft Fatigue Design Coach implementing cognitive apprenticeship.

Primary rule:
- Do not simply give final design answers or final diameters.
- Guide students to reason from mechanics, computation, and verification.

Coach students through:
1. Prediction: What trend should happen before running code?
2. Modeling: What assumptions are being made?
3. Computation: Which equations and parameters control the result?
4. Interpretation: What physical mechanism explains the computed trend?
5. Verification: What parameter sweep, limiting case, or hand check would confirm the result?
6. Reflection: What design decision is justified by the evidence?

For this problem, emphasize:
- rotating bending gives fully reversed normal stress at a surface point, so sigma_m = 0 when no steady axial/torsional component is present;
- the fatigue hotspot may occur at the small shoulder because nominal bending stress scales as 1/d^3 and the shoulder introduces Kt and Kf;
- Marin factors reduce the laboratory endurance limit to the component endurance limit;
- Kf depends on notch sensitivity and fillet radius, so changing d can change Kf when r/d is fixed;
- fatigue safety, static yielding safety, and finite-life design factor answer different questions;
- parameter sweeps are evidence, not decoration.

Keep responses concise, organized, and Socratic. Ask 1-3 targeted questions at the end.
"""

SOLUTION_EXPLAINER_PROMPT = """
You are explaining an instructor-provided solution for a stepped shaft fatigue problem.

Rules:
- The instructor solution is authoritative.
- Do not create a different solution path unless explicitly asked to compare.
- Do not change numerical values from the instructor solution.
- Do not introduce unsupported equations.
- Explain only the reasoning in the provided solution excerpt.
- If the excerpt is unclear or incomplete, say so.
- Focus on physical interpretation, assumptions, governing mechanisms, parameter sensitivity, and verification.
- When useful, ask the student what they would check in the JupyterLite computation.
"""

EXAMPLE_PROMPTS = {
    "Critical section": "I think the maximum bending moment location must always be the fatigue-critical section.",
    "Amplitude vs mean": "Why is the mean stress zero in rotating bending?",
    "Marin factors": "Which Marin factor changes when I increase the shaft diameter?",
    "Notch sensitivity": "Why does Kf depend on diameter if Kt is fixed from a chart?",
    "Finite life": "If nf is less than 1, why can the part still have a finite life estimate?",
    "Design factor": "Why does the required diameter increase from the trial value?",
    "Verification": "What parameter sweep should I run to verify the fatigue design trend?",
}


@dataclass
class ShaftInputs:
    F_kip: float = 8.0
    L_in: float = 20.0
    load_from_left_a_in: float = 15.0
    critical_from_left_c_in: float = 10.0
    d_in: float = 2.0
    D_over_d: float = 1.4
    r_over_d: float = 0.10
    Kt_bending: float = 1.65
    Sut_ksi: float = 120.0
    Sy_ksi: float = 66.0
    rpm: float = 950.0
    life_hours: float = 10.0
    ka_a: float = 2.0
    ka_b: float = -0.217
    kb_a: float = 0.91
    kb_b: float = -0.157
    kc: float = 1.0
    kd: float = 1.0
    ke: float = 1.0
    mean_stress_ksi: float = 0.0


def sqrta_for_steel(Sut_ksi: float) -> float:
    return 0.246 - 3.08e-3 * Sut_ksi + 1.51e-5 * Sut_ksi**2 - 2.67e-8 * Sut_ksi**3


def compute_shaft(inp: ShaftInputs) -> Dict[str, float]:
    b_in = inp.L_in - inp.load_from_left_a_in
    R1_kip = inp.F_kip * b_in / inp.L_in
    R2_kip = inp.F_kip - R1_kip
    M_kip_in = R1_kip * inp.critical_from_left_c_in

    r_in = inp.r_over_d * inp.d_in
    sqrta = sqrta_for_steel(inp.Sut_ksi)

    Kf = 1.0 + (inp.Kt_bending - 1.0) / (
        1.0 + sqrta / np.sqrt(max(r_in, 1e-12))
    )

    sigma_nom_ksi = 32.0 * M_kip_in / (np.pi * inp.d_in**3)
    sigma_max_ksi = Kf * sigma_nom_ksi
    sigma_min_ksi = -sigma_max_ksi + 2.0 * inp.mean_stress_ksi
    sigma_a_ksi = abs(sigma_max_ksi - sigma_min_ksi) / 2.0
    sigma_m_ksi = (sigma_max_ksi + sigma_min_ksi) / 2.0

    Se_prime_ksi = 0.5 * inp.Sut_ksi
    ka = inp.ka_a * inp.Sut_ksi ** inp.ka_b
    kb = inp.kb_a * inp.d_in ** inp.kb_b
    Se_ksi = ka * kb * inp.kc * inp.kd * inp.ke * Se_prime_ksi

    if sigma_m_ksi <= 0:
        nf = Se_ksi / sigma_a_ksi
    else:
        nf = 1.0 / (sigma_a_ksi / Se_ksi + sigma_m_ksi / inp.Sut_ksi)

    ny = inp.Sy_ksi / max(
        sigma_max_ksi,
        sigma_a_ksi + max(sigma_m_ksi, 0.0)
    )

    N_target = inp.rpm * 60.0 * inp.life_hours
    f = 1.06 - 2.8e-3 * inp.Sut_ksi + 6.9e-6 * inp.Sut_ksi**2
    a_basquin = (f * inp.Sut_ksi) ** 2 / Se_ksi
    b_basquin = -(1.0 / 3.0) * np.log10((f * inp.Sut_ksi) / Se_ksi)
    sigma_aN_ksi = a_basquin * N_target ** b_basquin
    nd = sigma_aN_ksi / sigma_a_ksi
    N_pred = (sigma_a_ksi / a_basquin) ** (1.0 / b_basquin)

    return {
        "b_in": b_in,
        "R1_kip": R1_kip,
        "R2_kip": R2_kip,
        "M_kip_in": M_kip_in,
        "r_in": r_in,
        "sqrta": sqrta,
        "Kf": Kf,
        "sigma_nom_ksi": sigma_nom_ksi,
        "sigma_max_ksi": sigma_max_ksi,
        "sigma_min_ksi": sigma_min_ksi,
        "sigma_a_ksi": sigma_a_ksi,
        "sigma_m_ksi": sigma_m_ksi,
        "Se_prime_ksi": Se_prime_ksi,
        "ka": ka,
        "kb": kb,
        "Se_ksi": Se_ksi,
        "nf": nf,
        "ny": ny,
        "N_target": N_target,
        "f": f,
        "a_basquin": a_basquin,
        "b_basquin": b_basquin,
        "sigma_aN_ksi": sigma_aN_ksi,
        "nd": nd,
        "N_pred": N_pred,
    }


def sweep_diameters(inp: ShaftInputs, d_min=1.5, d_max=3.2, n=120) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    ds = np.linspace(d_min, d_max, n)
    out = {"sigma_a_ksi": [], "Se_ksi": [], "nf": [], "nd": [], "ny": [], "Kf": []}

    for d in ds:
        temp = ShaftInputs(**{**asdict(inp), "d_in": float(d)})
        res = compute_shaft(temp)
        for key in out:
            out[key].append(res[key])

    return ds, {k: np.array(v) for k, v in out.items()}


def make_jupyterlite_code(inp: ShaftInputs) -> str:
    return f'''from numpy import *
import matplotlib.pyplot as plt

S_ut = {inp.Sut_ksi:.6g}
S_y = {inp.Sy_ksi:.6g}
F = {inp.F_kip:.6g}
L = {inp.L_in:.6g}
a_load = {inp.load_from_left_a_in:.6g}
c_critical = {inp.critical_from_left_c_in:.6g}
d = {inp.d_in:.6g}
r_over_d = {inp.r_over_d:.6g}
Kt = {inp.Kt_bending:.6g}
rpm = {inp.rpm:.6g}
life_hours = {inp.life_hours:.6g}

b = L - a_load
R1 = F*b/L
R2 = F - R1
M = R1*c_critical

sqrta = 0.246 - 3.08e-3*S_ut + 1.51e-5*S_ut**2 - 2.67e-8*S_ut**3
r = r_over_d*d
Kf = 1 + (Kt - 1)/(1 + sqrta/sqrt(r))

sigma_nom = 32*M/(pi*d**3)
sigma_max = Kf*sigma_nom
sigma_min = -sigma_max
sigma_a = (sigma_max - sigma_min)/2
sigma_m = (sigma_max + sigma_min)/2

ka = {inp.ka_a:.6g}*S_ut**({inp.ka_b:.6g})
kb = {inp.kb_a:.6g}*d**({inp.kb_b:.6g})
kc = {inp.kc:.6g}
kd = {inp.kd:.6g}
ke = {inp.ke:.6g}

Se_prime = 0.5*S_ut
Se = ka*kb*kc*kd*ke*Se_prime

if sigma_m <= 0:
    n_f = Se/sigma_a
else:
    n_f = (sigma_a/Se + sigma_m/S_ut)**(-1)

N = rpm*60*life_hours
f = 1.06 - 2.8e-3*S_ut + 6.9e-6*S_ut**2
a_B = (f*S_ut)**2/Se
b_B = -(1/3)*log10(f*S_ut/Se)
sigma_aN = a_B*N**b_B
n_d = sigma_aN/sigma_a
n_y = S_y/sigma_a

print(f"R1 = {{R1:.3f}} kip, R2 = {{R2:.3f}} kip")
print(f"M at critical shoulder = {{M:.3f}} kip-in")
print(f"sqrt(a) = {{sqrta:.4f}}, Kf = {{Kf:.3f}}")
print(f"sigma_a = {{sigma_a:.3f}} ksi, sigma_m = {{sigma_m:.3f}} ksi")
print(f"Se = {{Se:.3f}} ksi")
print(f"nf = {{n_f:.3f}}, ny = {{n_y:.3f}}, nd = {{n_d:.3f}}")

D = linspace(1.5, 3.2, 120)
nd_list = []
nf_list = []
siga_list = []

for d_i in D:
    r_i = r_over_d*d_i
    Kf_i = 1 + (Kt - 1)/(1 + sqrta/sqrt(r_i))
    sigma_i = Kf_i*32*M/(pi*d_i**3)
    kb_i = {inp.kb_a:.6g}*d_i**({inp.kb_b:.6g})
    Se_i = ka*kb_i*kc*kd*ke*Se_prime
    a_i = (f*S_ut)**2/Se_i
    b_i = -(1/3)*log10(f*S_ut/Se_i)
    sigaN_i = a_i*N**b_i

    siga_list.append(sigma_i)
    nf_list.append(Se_i/sigma_i)
    nd_list.append(sigaN_i/sigma_i)

plt.figure()
plt.plot(D, nd_list, label="finite-life design factor, nd")
plt.plot(D, nf_list, label="infinite-life fatigue factor, nf")
plt.axhline(1.6, linestyle="--", label="target design factor")
plt.xlabel("diameter d (in)")
plt.ylabel("factor")
plt.grid(True)
plt.legend()
plt.show()
'''


def get_client():
    if genai is None:
        return None
    try:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception:
        return None


def ask_gemini(client, system_prompt: str, user_input: str) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_input,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,
        ),
    )
    return response.text


def extract_solution_text() -> str:
    if PdfReader is None or not SOLUTION_FILE.exists():
        return ""

    try:
        reader = PdfReader(str(SOLUTION_FILE))
        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        return text[:16000]

    except Exception:
        return ""


if "coach_count" not in st.session_state:
    st.session_state.coach_count = 0

if "last_results" not in st.session_state:
    st.session_state.last_results = None


st.sidebar.header("Stepped shaft parameters")
st.sidebar.caption("Use sliders first, then ask the AI coach to interpret the computed behavior.")

with st.sidebar.expander("Loading and geometry", expanded=True):
    F_kip = st.slider("Transverse load F (kip)", 2.0, 16.0, 8.0, 0.5)
    L_in = st.slider("Bearing span L (in)", 12.0, 30.0, 20.0, 0.5)
    a_load = st.slider("Load location from left support a (in)", 4.0, 26.0, 15.0, 0.5)
    c_critical = st.slider("Small-shoulder location c (in)", 2.0, 24.0, 10.0, 0.5)
    d_in = st.slider("Trial small diameter d (in)", 1.50, 3.20, 2.00, 0.01)
    D_over_d = st.slider("Large/small diameter ratio D/d", 1.05, 2.00, 1.40, 0.01)
    r_over_d = st.slider("Fillet ratio r/d", 0.02, 0.25, 0.10, 0.01)
    Kt_bending = st.slider("Theoretical stress concentration Kt", 1.00, 3.00, 1.65, 0.01)

with st.sidebar.expander("Material and fatigue inputs", expanded=True):
    Sut_ksi = st.slider("Ultimate strength Sut (ksi)", 60.0, 220.0, 120.0, 1.0)
    Sy_ksi = st.slider("Yield strength Sy (ksi)", 40.0, 180.0, 66.0, 1.0)
    rpm = st.slider("Speed (rev/min)", 100.0, 3000.0, 950.0, 50.0)
    life_hours = st.slider("Target life (hours)", 1.0, 200.0, 10.0, 1.0)
    ke = st.selectbox("Reliability factor ke", [1.000, 0.897, 0.868, 0.814, 0.753, 0.702], index=0)
    mean_stress = st.slider("Optional steady mean stress (ksi)", 0.0, 30.0, 0.0, 0.5)


inp = ShaftInputs(
    F_kip=F_kip,
    L_in=L_in,
    load_from_left_a_in=min(a_load, L_in - 0.5),
    critical_from_left_c_in=min(c_critical, L_in - 0.5),
    d_in=d_in,
    D_over_d=D_over_d,
    r_over_d=r_over_d,
    Kt_bending=Kt_bending,
    Sut_ksi=Sut_ksi,
    Sy_ksi=Sy_ksi,
    rpm=rpm,
    life_hours=life_hours,
    ke=float(ke),
    mean_stress_ksi=mean_stress,
)

res = compute_shaft(inp)
st.session_state.last_results = res


st.title("TAMU Mechanics: Stepped Shaft Fatigue Design Coach")
st.caption("Close integration of JupyterLite-style computation and AI-guided learning")

coach_tab, compute_tab, jlite_tab, solution_tab, concept_tab = st.tabs(
    ["AI Coach", "Computation Dashboard", "JupyterLite Code", "Solution Access", "Concept Review"]
)


with coach_tab:
    st.subheader("AI-guided learning connected to current computed parameters")
    st.write(
        "Use the dashboard or sidebar to change the shaft parameters. Then ask the AI coach to "
        "help interpret the trend, identify assumptions, and propose verification checks."
    )

    left, right = st.columns([1, 1.6])

    with left:
        st.markdown("### Current computational evidence")
        st.metric("Alternating stress, σa", f"{res['sigma_a_ksi']:.2f} ksi")
        st.metric("Mean stress, σm", f"{res['sigma_m_ksi']:.2f} ksi")
        st.metric("Endurance limit, Se", f"{res['Se_ksi']:.2f} ksi")
        st.metric("Fatigue factor, nf", f"{res['nf']:.2f}")
        st.metric("Finite-life design factor, nd", f"{res['nd']:.2f}")
        st.info(
            "The AI sees these current values only as context. It should help students reason "
            "about why the values changed and how to verify them."
        )

    with right:
        example = st.selectbox("Example student question", list(EXAMPLE_PROMPTS.keys()))

        student_input = st.text_area(
            "Student reasoning or question",
            value=EXAMPLE_PROMPTS[example],
            height=140,
        )

        st.write(f"Coaching interactions used: **{st.session_state.coach_count}/{UNLOCK_COUNT}**")

        client = get_client()

        if client is None:
            st.warning("AI coaching is disabled until GEMINI_API_KEY is added to Streamlit secrets.")
        else:
            if st.button("Coach Me", key="coach_button"):
                st.session_state.coach_count += 1

                context = f"""
Current parameter state:
{asdict(inp)}

Current computed results:
{res}

Student question/reasoning:
{student_input}
"""

                with st.spinner("Thinking like a fatigue design coach..."):
                    try:
                        answer = ask_gemini(client, SYSTEM_PROMPT, context)
                        st.markdown("### AI-guided prompt")
                        st.success(answer)
                    except Exception as e:
                        st.error(f"Gemini API error: {e}")

        if st.session_state.coach_count < UNLOCK_COUNT:
            st.info(
                f"Complete {UNLOCK_COUNT - st.session_state.coach_count} more coaching interaction(s) "
                "to unlock the instructor solution."
            )
        else:
            st.success("Instructor solution is now unlocked. Go to the Solution Access tab.")


with compute_tab:
    st.subheader("Computation dashboard: make the mechanics visible")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kf", f"{res['Kf']:.3f}")
    m2.metric("σa", f"{res['sigma_a_ksi']:.2f} ksi")
    m3.metric("Se", f"{res['Se_ksi']:.2f} ksi")
    m4.metric("nd", f"{res['nd']:.2f}")

    st.markdown("### Diameter sweep for verification")
    d_sweep, sw = sweep_diameters(inp)

    fig1, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(d_sweep, sw["sigma_a_ksi"], label="applied σa")
    ax1.plot(d_sweep, sw["Se_ksi"], label="component endurance limit Se")
    ax1.set_xlabel("diameter d (in)")
    ax1.set_ylabel("stress (ksi)")
    ax1.grid(True)
    ax1.legend()
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots(figsize=(7, 4))
    ax2.plot(d_sweep, sw["nf"], label="infinite-life fatigue factor nf")
    ax2.plot(d_sweep, sw["nd"], label="finite-life design factor nd")
    ax2.plot(d_sweep, sw["ny"], label="yield factor ny")
    ax2.axhline(1.6, linestyle="--", label="target design factor 1.6")
    ax2.set_xlabel("diameter d (in)")
    ax2.set_ylabel("factor")
    ax2.grid(True)
    ax2.legend()
    st.pyplot(fig2)

    st.markdown("### What students should notice")
    st.markdown(
        """
- The applied alternating bending stress decreases rapidly because nominal bending stress scales with d⁻³.
- The endurance limit changes more slowly because the size factor kb has a mild power-law dependence on d.
- The fatigue stress concentration factor Kf also changes with d when r/d is fixed, because the fillet radius r changes.
- The finite-life design factor nd and infinite-life fatigue factor nf do not answer exactly the same design question.
"""
    )

    st.markdown("### Calculation trace")

    trace = {
        "R1 (kip)": res["R1_kip"],
        "R2 (kip)": res["R2_kip"],
        "M at critical shoulder (kip-in)": res["M_kip_in"],
        "sqrt(a) (sqrt(in))": res["sqrta"],
        "fillet radius r (in)": res["r_in"],
        "Kf": res["Kf"],
        "ka": res["ka"],
        "kb": res["kb"],
        "Se prime (ksi)": res["Se_prime_ksi"],
        "Se (ksi)": res["Se_ksi"],
        "sigma_aN at target life (ksi)": res["sigma_aN_ksi"],
        "predicted life at current d (cycles)": res["N_pred"],
    }

    st.dataframe(
        [{"Quantity": k, "Value": v} for k, v in trace.items()],
        hide_index=True,
        use_container_width=True,
    )


with jlite_tab:
    st.subheader("JupyterLite-ready computation cell")
    st.write(
        "This is the direct link between the Streamlit AI coach and the browser-based computation. "
        "Students can copy the current parameter state into JupyterLite, run the sweep, and return "
        "to the AI coach to explain the trend."
    )

    code = make_jupyterlite_code(inp)
    st.code(code, language="python")

    st.download_button(
        "Download current JupyterLite code cell (.py)",
        data=code,
        file_name="stepped_shaft_current_case.py",
        mime="text/x-python",
    )

    if NOTEBOOK_FILE.exists():
        with open(NOTEBOOK_FILE, "rb") as f:
            st.download_button(
                "Download instructor notebook",
                data=f,
                file_name="FatigueSteppedShaft.ipynb",
                mime="application/x-ipynb+json",
            )

    st.markdown("### Suggested student loop")
    st.markdown(
        """
1. Predict how changing d, r/d, Kt, Sut, or reliability will affect σa, Se, nf, and nd.
2. Run the JupyterLite cell.
3. Compare the plot against the prediction.
4. Ask the AI coach why the trend occurred.
5. Verify with one additional sweep or limiting case.
"""
    )


with solution_tab:
    st.subheader("Instructor solution and AI explanation")

    if st.session_state.coach_count < UNLOCK_COUNT:
        st.warning(f"The solution is locked. Complete {UNLOCK_COUNT} AI coaching interactions first.")
        st.write("Students should first use prediction, computation, interpretation, and verification.")

    else:
        st.success("Solution unlocked.")

        if SOLUTION_FILE.exists():
            with open(SOLUTION_FILE, "rb") as f:
                st.download_button(
                    "Download instructor solution PDF",
                    data=f,
                    file_name="L19_FatigueExample2.pdf",
                    mime="application/pdf",
                )
        else:
            st.error("Instructor solution PDF was not found in the app folder.")

        solution_text = extract_solution_text()

        if solution_text:
            with st.expander("View extracted solution text"):
                st.write(solution_text)
        else:
            st.warning("Could not automatically extract PDF text. Paste the relevant solution excerpt below.")
            solution_text = st.text_area("Paste solution excerpt", height=240)

        student_question = st.text_area(
            "What part of the instructor solution should AI explain?",
            "Explain why the small shoulder is fatigue-critical and why sigma_m is zero in rotating bending.",
            height=100,
        )

        client = get_client()

        if client is None:
            st.warning("AI solution explanation is disabled until GEMINI_API_KEY is added to Streamlit secrets.")

        elif st.button("Explain Instructor Solution", key="explain_solution"):
            prompt = f"""
Instructor solution excerpt:
{solution_text}

Current computed parameter state:
{asdict(inp)}

Current computed results:
{res}

Student question:
{student_question}
"""

            with st.spinner("Explaining the instructor solution..."):
                try:
                    explanation = ask_gemini(client, SOLUTION_EXPLAINER_PROMPT, prompt)
                    st.markdown("### Explanation")
                    st.info(explanation)
                except Exception as e:
                    st.error(f"Gemini API error: {e}")


with concept_tab:
    st.subheader("Concept review: fatigue design of a rotating stepped shaft")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Critical section", "σa vs σm", "Marin factors", "Life and safety"]
    )

    with tab1:
        st.markdown(
            """
### Critical section
The maximum bending moment location is not automatically the fatigue-critical location.
A shoulder can govern because:
- the local diameter may be smaller;
- bending stress scales as 1/d³;
- the fillet introduces Kt;
- material notch sensitivity converts Kt into Kf.

**Coaching question:** If the bending moment is lower at the shoulder than under the load, what must be true for the shoulder still to govern?
"""
        )

    with tab2:
        st.markdown(
            """
### Alternating and mean stress
For rotating bending with no steady axial or torsional bias, a surface point alternates between tension and compression.
That produces fully reversed stress:
- σa is nonzero;
- σm is zero.

**Coaching question:** What physical change would introduce nonzero mean stress?
"""
        )

    with tab3:
        st.markdown(
            """
### Marin factors
The laboratory endurance limit is modified for real components:

Se = ka kb kc kd ke Se′

Important interpretations:
- ka accounts for surface finish;
- kb accounts for size;
- kc accounts for loading type;
- kd accounts for temperature;
- ke accounts for reliability.

**Coaching question:** Which factor changes directly when the shaft diameter changes?
"""
        )

    with tab4:
        st.markdown(
            """
### Fatigue factor, yield factor, and finite-life design factor
- ny checks static yielding.
- nf checks infinite-life fatigue resistance.
- nd compares finite-life allowable stress to the applied alternating stress for the target life.

A design may pass static yielding but fail fatigue.

**Coaching question:** Why can ny be greater than 1 while nf is less than 1?
"""
        )


st.markdown("---")
st.caption("MEEN 368 Mechanics Coach | Computation as evidence, AI as interpretive scaffold")

import math
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Bolted Connection Equation Explorer",
    page_icon="🔩",
    layout="wide",
)

st.title("🔩 Bolted Connection Equation Explorer")
st.caption("Interactive calculator and concept map for bolted joints in tension, fatigue, shear, and bearing.")

st.sidebar.header("Problem Type")
mode = st.sidebar.radio(
    "Choose analysis mode",
    [
        "Tension Joint",
        "Fatigue in Tension Joint",
        "Bolts Under Shear",
        "Equation Interdependence Map",
        "AI Tutor Prompt Builder",
    ],
)

st.sidebar.markdown("---")
st.sidebar.info(
    "Use consistent units. For example, use N and MPa with mm², "
    "or lb and ksi with in². The app does not automatically convert units."
)

def safe_div(num, den):
    if den == 0:
        return None
    return num / den

def show_metric(label, value, fmt="{:.4g}"):
    if value is None or isinstance(value, complex) or math.isnan(value):
        st.metric(label, "Undefined")
    else:
        st.metric(label, fmt.format(value))

def tension_joint():
    st.header("Tension Joint: Stiffness, Load Sharing, and FOS")

    col1, col2, col3 = st.columns(3)
    with col1:
        Sp = st.number_input("Proof strength, Sp", value=380.0)
        At = st.number_input("Tensile stress area, At", value=58.0)
        Fi = st.number_input("Preload, Fi", value=0.75 * 380.0 * 58.0)
    with col2:
        P = st.number_input("External tensile load, P", value=5000.0)
        kb = st.number_input("Bolt stiffness, kb", value=1.0e6)
        km = st.number_input("Member stiffness, km", value=3.0e6)
    with col3:
        connection = st.selectbox("Preload recommendation", ["Non-permanent: Fi = 0.75 Sp At", "Permanent: Fi = 0.90 Sp At", "Custom Fi"])
        if st.button("Update Fi from recommendation"):
            if connection.startswith("Non"):
                Fi = 0.75 * Sp * At
            elif connection.startswith("Permanent"):
                Fi = 0.90 * Sp * At

    C = safe_div(kb, kb + km)
    Fb = Fi + C * P if C is not None else None
    Fm = (1 - C) * P if C is not None else None
    np_ = safe_div(Sp * At, C * P + Fi) if C is not None else None
    nL = safe_div(Sp * At - Fi, C * P) if C not in [None, 0] else None
    n0 = safe_div(Fi, (1 - C) * P) if C is not None else None

    st.subheader("Results")
    r1, r2, r3, r4, r5 = st.columns(5)
    with r1: show_metric("Load fraction, C", C)
    with r2: show_metric("Bolt load, Fb", Fb)
    with r3: show_metric("Member load relief, Fm", Fm)
    with r4: show_metric("Proof FOS, np", np_)
    with r5: show_metric("Separation FOS, n0", n0)

    st.subheader("Equations")
    st.latex(r"C=\frac{k_b}{k_b+k_m}")
    st.latex(r"F_b=F_i+CP")
    st.latex(r"F_m=(1-C)P")
    st.latex(r"n_p=\frac{S_pA_t}{CP+F_i}")
    st.latex(r"n_L=\frac{S_pA_t-F_i}{CP}")
    st.latex(r"n_0=\frac{F_i}{(1-C)P}")

    st.subheader("Conceptual interpretation")
    if C is not None:
        st.write(
            f"The bolt takes {100*C:.1f}% of the external load increment, while the members unload by "
            f"{100*(1-C):.1f}% of the external load. Increasing member stiffness usually decreases C, "
            "so less of the external load increment goes into the bolt."
        )

def fatigue_joint():
    st.header("Fatigue in Preloaded Tension Joint")

    col1, col2, col3 = st.columns(3)
    with col1:
        Sut = st.number_input("Ultimate strength, Sut", value=830.0)
        Se = st.number_input("Endurance strength, Se", value=300.0)
        At = st.number_input("Tensile stress area, At", value=58.0)
    with col2:
        Fi = st.number_input("Preload, Fi", value=16500.0)
        C = st.number_input("Load fraction, C", value=0.25, min_value=0.0, max_value=1.0)
        Pmax = st.number_input("Maximum external load, Pmax", value=7000.0)
    with col3:
        Pmin = st.number_input("Minimum external load, Pmin", value=1000.0)
        Kf = st.number_input("Fatigue stress concentration factor, Kf", value=1.0)
        use_modified = st.checkbox("Use modified endurance: Se = 0.85(0.5 Sut)/Kf", value=False)

    if use_modified:
        Se_eff = 0.85 * 0.5 * Sut / Kf
    else:
        Se_eff = Se

    sigma_i = safe_div(Fi, At)
    sigma_a = safe_div(C * (Pmax - Pmin), 2 * At)
    sigma_m = safe_div(C * (Pmax + Pmin), 2 * At)
    if sigma_m is not None and sigma_i is not None:
        sigma_m += sigma_i

    nf = None
    if sigma_a is not None and sigma_m is not None:
        nf = safe_div(Se_eff * (Sut - sigma_i), sigma_a * Sut + Se_eff * (sigma_m - sigma_i))

    st.subheader("Results")
    r1, r2, r3, r4 = st.columns(4)
    with r1: show_metric("Pre-stress, σi", sigma_i)
    with r2: show_metric("Alternating stress, σa", sigma_a)
    with r3: show_metric("Mean stress, σm", sigma_m)
    with r4: show_metric("Fatigue FOS, nf", nf)

    st.subheader("Equations")
    st.latex(r"\sigma_i=\frac{F_i}{A_t}")
    st.latex(r"\sigma_a=\frac{C(P_{\max}-P_{\min})}{2A_t}")
    st.latex(r"\sigma_m=\frac{C(P_{\max}+P_{\min})}{2A_t}+\frac{F_i}{A_t}")
    st.latex(r"n_f=\frac{S_e(S_{ut}-\sigma_i)}{\sigma_aS_{ut}+S_e(\sigma_m-\sigma_i)}")

    st.subheader("Interpretation")
    st.write(
        "Preload increases the mean stress, but it can reduce the effect of external load variation on joint separation. "
        "The fatigue calculation is sensitive to C, At, Fi, and the load range Pmax − Pmin."
    )

def shear_bearing():
    st.header("Bolts Under Shear and Bearing")

    col1, col2, col3 = st.columns(3)
    with col1:
        Sy_bolt = st.number_input("Bolt yield strength, Sy_bolt", value=380.0)
        Sy_member = st.number_input("Member yield strength, Sy_member", value=250.0)
    with col2:
        d = st.number_input("Bolt diameter, d", value=10.0)
        t = st.number_input("Member thickness, t", value=8.0)
    with col3:
        F = st.number_input("Applied shear load per bolt, F", value=5000.0)

    area = math.pi * d**2 / 4
    tau_vm = safe_div(math.sqrt(3) * F, area)
    n_shear = safe_div(Sy_bolt, tau_vm) if tau_vm is not None else None
    n_bearing_bolt = safe_div(Sy_bolt, safe_div(F, d*t))
    n_bearing_member = safe_div(Sy_member, safe_div(F, d*t))

    st.subheader("Results")
    r1, r2, r3, r4 = st.columns(4)
    with r1: show_metric("Bolt area", area)
    with r2: show_metric("Shear FOS", n_shear)
    with r3: show_metric("Bearing FOS, bolt", n_bearing_bolt)
    with r4: show_metric("Bearing FOS, member", n_bearing_member)

    st.subheader("Equations")
    st.latex(r"n_{\mathrm{shear}}=\frac{S_y^{bolt}}{\sigma_{vm}}=\frac{\pi d^2S_y^{bolt}}{4\sqrt{3}F}")
    st.latex(r"n_{\mathrm{bearing,bolt}}=\frac{S_y^{bolt}}{F/(dt)}")
    st.latex(r"n_{\mathrm{bearing,member}}=\frac{S_y^{member}}{F/(dt)}")

def interdependence_map():
    st.header("Equation Interdependence Map")

    st.markdown(
        """
        This map helps students see which quantities control other quantities.

        **Stiffness path**

        `kb, km → C → Fb, Fm → np, nL, n0`

        **Fatigue path**

        `Fi, At → σi`

        `C, Pmax, Pmin, At → σa, σm`

        `Sut, Se, σi, σa, σm → nf`

        **Shear/bearing path**

        `d, F, Sy_bolt → shear FOS`

        `d, t, F, Sy_bolt, Sy_member → bearing FOS`
        """
    )

    data = [
        ["kb", "C", "Increasing kb increases C"],
        ["km", "C", "Increasing km decreases C"],
        ["C", "Fb", "Increasing C increases bolt load from external P"],
        ["Fi", "Fb", "Increasing Fi increases total bolt load"],
        ["Fi", "n0", "Increasing Fi increases separation resistance"],
        ["At", "stress", "Increasing At reduces stress"],
        ["Pmax − Pmin", "σa", "Larger load range increases fatigue damage"],
        ["Sut, Se", "nf", "Higher strengths generally increase fatigue FOS"],
        ["d", "shear/bearing FOS", "Larger diameter improves shear and bearing capacity"],
    ]
    df = pd.DataFrame(data, columns=["Input", "Affects", "Conceptual effect"])
    st.dataframe(df, use_container_width=True)

def ai_tutor_prompt_builder():
    st.header("AI Tutor Prompt Builder")

    st.write(
        "This section creates prompts students can paste into an AI tutor. "
        "For classroom use, ask students to explain their reasoning and verify equations instead of only requesting final answers."
    )

    topic = st.selectbox(
        "Topic",
        [
            "Load fraction C",
            "Preload and separation",
            "Fatigue safety factor",
            "Bolt shear",
            "Bearing stress",
        ],
    )
    student_question = st.text_area("Student question", "Why does increasing member stiffness reduce the load taken by the bolt?")

    prompt = f"""
You are a mechanics of materials tutor. Explain the following bolted-connection concept clearly and step by step.

Topic: {topic}

Student question:
{student_question}

Requirements:
1. Define the relevant variables.
2. Write the governing equation.
3. Explain the physical meaning.
4. State what increases or decreases the factor of safety.
5. Do not skip dimensional consistency.
6. End with one conceptual check question for the student.
"""
    st.subheader("Copyable AI Tutor Prompt")
    st.code(prompt, language="text")

if mode == "Tension Joint":
    tension_joint()
elif mode == "Fatigue in Tension Joint":
    fatigue_joint()
elif mode == "Bolts Under Shear":
    shear_bearing()
elif mode == "Equation Interdependence Map":
    interdependence_map()
elif mode == "AI Tutor Prompt Builder":
    ai_tutor_prompt_builder()
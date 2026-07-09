import os
import math
import plotly.express as px
from dataclasses import dataclass, asdict

import pandas as pd
import streamlit as st

try:
    from google import genai
except Exception:
    genai = None


st.set_page_config(
    page_title="Bolted Connection AI Tutor",
    page_icon="🔩",
    layout="wide",
)


def safe_div(a, b):
    if b == 0:
        return None
    return a / b


@dataclass
class JointInputs:
    Sp: float = 380.0
    Sy_bolt: float = 380.0
    Sy_member: float = 250.0
    Sut: float = 830.0
    Se: float = 300.0
    At: float = 58.0
    d: float = 10.0
    t: float = 8.0
    Fi: float = 16500.0
    P: float = 5000.0
    Pmax: float = 7000.0
    Pmin: float = 1000.0
    kb: float = 1.0e6
    km: float = 3.0e6
    Kf: float = 1.0


def compute(x: JointInputs):
    C = safe_div(x.kb, x.kb + x.km)
    Fb = x.Fi + C * x.P if C is not None else None
    Fm = (1 - C) * x.P if C is not None else None

    np_ = safe_div(x.Sp * x.At, C * x.P + x.Fi) if C is not None else None
    nL = safe_div(x.Sp * x.At - x.Fi, C * x.P) if C not in [None, 0] else None
    n0 = safe_div(x.Fi, (1 - C) * x.P) if C is not None else None

    sigma_i = safe_div(x.Fi, x.At)
    sigma_a = safe_div(C * (x.Pmax - x.Pmin), 2 * x.At) if C is not None else None
    sigma_m = safe_div(C * (x.Pmax + x.Pmin), 2 * x.At) if C is not None else None
    if sigma_m is not None and sigma_i is not None:
        sigma_m += sigma_i

    nf = None
    if sigma_i is not None and sigma_a is not None and sigma_m is not None:
        nf = safe_div(
            x.Se * (x.Sut - sigma_i),
            sigma_a * x.Sut + x.Se * (sigma_m - sigma_i),
        )

    bolt_area = math.pi * x.d**2 / 4
    tau_vm = safe_div(math.sqrt(3) * x.P, bolt_area)
    n_shear = safe_div(x.Sy_bolt, tau_vm) if tau_vm is not None else None
    bearing_stress = safe_div(x.P, x.d * x.t)
    n_bearing_bolt = safe_div(x.Sy_bolt, bearing_stress) if bearing_stress else None
    n_bearing_member = safe_div(x.Sy_member, bearing_stress) if bearing_stress else None

    return {
        "C": C,
        "Fb": Fb,
        "Fm": Fm,
        "np": np_,
        "nL": nL,
        "n0": n0,
        "sigma_i": sigma_i,
        "sigma_a": sigma_a,
        "sigma_m": sigma_m,
        "nf": nf,
        "bolt_area": bolt_area,
        "tau_vm": tau_vm,
        "n_shear": n_shear,
        "bearing_stress": bearing_stress,
        "n_bearing_bolt": n_bearing_bolt,
        "n_bearing_member": n_bearing_member,
    }


def fmt(v):
    if v is None:
        return "undefined"
    try:
        if math.isnan(v) or math.isinf(v):
            return "undefined"
    except Exception:
        pass
    return f"{v:.4g}"


SYSTEM_PROMPT = """
You are an AI tutor for a mechanical engineering course on bolted connections.
Teach conceptually. Do not merely give final answers.

Use the current numerical context provided by the app.
Explain equations physically.
Ask Socratic questions when useful.
Do not invent values not provided.
Use consistent units and remind the student to check units.

Important equations:
C = kb/(kb + km)
Fb = Fi + C P
Fm = (1 - C) P
np = Sp At/(C P + Fi)
nL = (Sp At - Fi)/(C P)
n0 = Fi/((1 - C)P)
sigma_i = Fi/At
sigma_a = C(Pmax - Pmin)/(2 At)
sigma_m = C(Pmax + Pmin)/(2 At) + Fi/At
nf = Se(Sut - sigma_i)/(sigma_a Sut + Se(sigma_m - sigma_i))
n_shear = pi d^2 Sy_bolt/(4 sqrt(3) F)
n_bearing = Sy/[F/(dt)]
"""


def get_api_key():
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY")


def ask_ai(messages, context):
    api_key = get_api_key()
    if not api_key or genai is None:
        return None

    client = genai.Client(api_key=api_key)

    conversation_text = ""
    for m in messages:
        role = m["role"]
        content = m["content"]
        conversation_text += f"{role.upper()}:\n{content}\n\n"

    prompt = f"""
{SYSTEM_PROMPT}

Current app context:

Inputs:
{context["inputs"]}

Computed results:
{context["results"]}

Conversation:
{conversation_text}

Respond as a bolted-connection tutor.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text


def fallback_tutor_answer(question, x, r):
    q = question.lower()

    if "member stiffness" in q or "km" in q or "load fraction" in q:
        return f"""
The key equation is

C = kb/(kb + km)

For your current values,

kb = {fmt(x.kb)}

km = {fmt(x.km)}

so

C = {fmt(r["C"])}

The bolt receives only the fraction C of the external tensile load P. The members unload by the fraction 1 - C.

If member stiffness km increases, the denominator kb + km becomes larger while kb stays the same. Therefore C decreases.

Physically, stiffer members resist deformation more strongly, so more of the external load is absorbed as member unloading rather than additional bolt stretching.

Concept check: If km became extremely large compared with kb, what value would C approach?
"""

    if "preload" in q or "separation" in q or "n0" in q:
        return f"""
For separation, the important equation is

n0 = Fi/((1 - C)P)

For your current values,

Fi = {fmt(x.Fi)}

C = {fmt(r["C"])}

P = {fmt(x.P)}

so

n0 = {fmt(r["n0"])}

Increasing preload Fi increases resistance to separation. However, preload also increases the initial bolt stress sigma_i = Fi/At.

Concept check: Why might too little preload be dangerous even if the external load is moderate?
"""

    if "fatigue" in q or "nf" in q or "alternating" in q:
        return f"""
For fatigue, the important stresses are

sigma_i = Fi/At = {fmt(r["sigma_i"])}

sigma_a = C(Pmax - Pmin)/(2At) = {fmt(r["sigma_a"])}

sigma_m = C(Pmax + Pmin)/(2At) + Fi/At = {fmt(r["sigma_m"])}

The fatigue factor of safety is

nf = {fmt(r["nf"])}

The fatigue response is strongly affected by the load range Pmax - Pmin, the load fraction C, the tensile stress area At, and the preload Fi.

Concept check: Which would reduce sigma_a more directly: increasing preload or increasing At?
"""

    if "shear" in q:
        return f"""
For bolt shear,

n_shear = pi d^2 Sy_bolt/(4 sqrt(3) F)

For your current values,

d = {fmt(x.d)}

Sy_bolt = {fmt(x.Sy_bolt)}

F = {fmt(x.P)}

n_shear = {fmt(r["n_shear"])}

Because d is squared, increasing bolt diameter has a strong effect on shear capacity.

Concept check: If the diameter increases by 20%, by what approximate percentage does the shear area increase?
"""

    return f"""
I can help using the current app values.

Current key results:

C = {fmt(r["C"])}

Fb = {fmt(r["Fb"])}

n0 = {fmt(r["n0"])}

np = {fmt(r["np"])}

sigma_a = {fmt(r["sigma_a"])}

sigma_m = {fmt(r["sigma_m"])}

nf = {fmt(r["nf"])}

Try asking:
- Why does increasing member stiffness reduce C?
- What happens if preload is too low?
- Why does fatigue depend on Pmax - Pmin?
- How does bolt diameter affect shear FOS?
"""

# ----------------------------
# Header
# ----------------------------
st.title("TAMU Mechanics: 🔩 Bolted Connection AI Tutor")

st.caption(
    "Interactive equation explorer, dependency map, what-if analysis, and context-aware tutoring."
    "Developed by **Dr. Zubaer Hossain**, Department of Mechanical Engineering, Texas A&M University • "
    "Questions or comments: [zubaer@tamu.edu](mailto:zubaer@tamu.edu)"
)

st.info("""
**Open Educational Resource**

This calculator is freely available for educational use.
""")

st.write("""
This app calculates the fatigue stress concentration factor, \(K_f\), using the notch sensitivity relation. 
Students can change material strength, notch radius, loading type, unit system, and static stress concentration factor.
""")

with st.sidebar:
    st.header("Inputs")

    st.subheader("Strengths")
    Sp = st.number_input("Proof strength, Sp", value=380.0)
    Sy_bolt = st.number_input("Bolt yield strength, Sy_bolt", value=380.0)
    Sy_member = st.number_input("Member yield strength, Sy_member", value=250.0)
    Sut = st.number_input("Ultimate strength, Sut", value=830.0)
    Se = st.number_input("Endurance strength, Se", value=300.0)

    st.subheader("Geometry")
    At = st.number_input("Tensile stress area, At", value=58.0)
    d = st.number_input("Bolt diameter, d", value=10.0)
    t = st.number_input("Member thickness, t", value=8.0)

    st.subheader("Loads")
    Fi = st.number_input("Preload, Fi", value=16500.0)
    P = st.number_input("External load, P", value=5000.0)
    Pmax = st.number_input("Maximum load, Pmax", value=7000.0)
    Pmin = st.number_input("Minimum load, Pmin", value=1000.0)

    st.subheader("Stiffness")
    kb = st.number_input("Bolt stiffness, kb", value=1.0e6)
    km = st.number_input("Member stiffness, km", value=3.0e6)

    Kf = st.number_input("Fatigue stress concentration factor, Kf", value=1.0)

x = JointInputs(
    Sp=Sp, Sy_bolt=Sy_bolt, Sy_member=Sy_member, Sut=Sut, Se=Se,
    At=At, d=d, t=t, Fi=Fi, P=P, Pmax=Pmax, Pmin=Pmin,
    kb=kb, km=km, Kf=Kf
)
r = compute(x)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Equation Explorer",
        "Dependency Map",
        "What-if Analysis",
        "Parametric Plots",
        "AI Tutor",
        "Worked Example",
    ]
)

with tab1:
    st.header("Equation Explorer")

    eq = st.selectbox(
        "Select an equation",
        [
            "Load fraction: C = kb/(kb + km)",
            "Bolt load: Fb = Fi + CP",
            "Member unloading: Fm = (1 - C)P",
            "Proof FOS: np = Sp At/(CP + Fi)",
            "Separation FOS: n0 = Fi/((1 - C)P)",
            "Fatigue FOS: nf",
            "Shear FOS",
            "Bearing FOS",
        ],
    )

    if eq.startswith("Load fraction"):
        st.latex(r"C=\frac{k_b}{k_b+k_m}")
        st.write(f"Current value: **C = {fmt(r['C'])}**")
        st.info("C is the fraction of the external tensile load increment taken by the bolt.")

    elif eq.startswith("Bolt load"):
        st.latex(r"F_b=F_i+CP")
        st.write(f"Current value: **Fb = {fmt(r['Fb'])}**")
        st.info("The bolt already carries preload Fi. External load adds only CP to the bolt, not the full P.")

    elif eq.startswith("Member"):
        st.latex(r"F_m=(1-C)P")
        st.write(f"Current value: **Fm = {fmt(r['Fm'])}**")
        st.info("The external load partially unloads the compressed members.")

    elif eq.startswith("Proof"):
        st.latex(r"n_p=\frac{S_pA_t}{CP+F_i}")
        st.write(f"Current value: **np = {fmt(r['np'])}**")

    elif eq.startswith("Separation"):
        st.latex(r"n_0=\frac{F_i}{(1-C)P}")
        st.write(f"Current value: **n0 = {fmt(r['n0'])}**")

    elif eq.startswith("Fatigue"):
        st.latex(r"\sigma_i=\frac{F_i}{A_t}")
        st.latex(r"\sigma_a=\frac{C(P_{\max}-P_{\min})}{2A_t}")
        st.latex(r"\sigma_m=\frac{C(P_{\max}+P_{\min})}{2A_t}+\frac{F_i}{A_t}")
        st.latex(r"n_f=\frac{S_e(S_{ut}-\sigma_i)}{\sigma_aS_{ut}+S_e(\sigma_m-\sigma_i)}")
        st.write(f"Current value: **nf = {fmt(r['nf'])}**")

    elif eq.startswith("Shear"):
        st.latex(r"n_{\mathrm{shear}}=\frac{\pi d^2 S_y^{bolt}}{4\sqrt{3}F}")
        st.write(f"Current value: **n_shear = {fmt(r['n_shear'])}**")

    else:
        st.latex(r"n_{\mathrm{bearing}}=\frac{S_y}{F/(dt)}")
        st.write(f"Bolt bearing FOS: **{fmt(r['n_bearing_bolt'])}**")
        st.write(f"Member bearing FOS: **{fmt(r['n_bearing_member'])}**")

    st.subheader("Current calculated quantities")
    df = pd.DataFrame([{"Quantity": k, "Value": fmt(v)} for k, v in r.items()])
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    st.header("Dependency Map")

    deps = pd.DataFrame(
        [
            ["kb", "C", "Increasing kb increases C."],
            ["km", "C", "Increasing km decreases C."],
            ["C", "Fb", "Increasing C increases the additional bolt load."],
            ["Fi", "Fb", "Increasing Fi increases total bolt load."],
            ["Fi", "n0", "Increasing Fi increases separation resistance."],
            ["C", "n0", "Increasing C decreases member unloading and increases n0."],
            ["At", "stress", "Increasing At reduces bolt stresses."],
            ["Pmax - Pmin", "sigma_a", "Increasing load range increases alternating stress."],
            ["d", "shear FOS", "Increasing diameter increases shear area."],
            ["d and t", "bearing FOS", "Increasing projected area dt reduces bearing stress."],
        ],
        columns=["Input", "Affects", "Physical meaning"],
    )
    st.dataframe(deps, use_container_width=True, hide_index=True)

    st.markdown(
        """
Simple dependency chain:

`kb, km → C → Fb, Fm → proof/separation FOS`

`Fi, At → sigma_i`

`C, Pmax, Pmin, At → sigma_a, sigma_m → fatigue FOS`

`d, t, F → shear and bearing FOS`
"""
    )

with tab3:
    st.header("What-if Analysis")

    variable = st.selectbox("Choose one variable to vary", ["km", "kb", "Fi", "P", "At", "d", "Pmax", "Pmin"])
    factor = st.slider("Multiplier", 0.25, 3.0, 1.5, 0.05)

    x2 = JointInputs(**asdict(x))
    setattr(x2, variable, getattr(x2, variable) * factor)
    r2 = compute(x2)

    rows = []
    for key in ["C", "Fb", "Fm", "np", "n0", "sigma_i", "sigma_a", "sigma_m", "nf", "n_shear", "n_bearing_bolt", "n_bearing_member"]:
        old = r[key]
        new = r2[key]
        if old not in [None, 0] and new is not None:
            pct = 100 * (new - old) / old
            change = f"{pct:+.1f}%"
        else:
            change = "n/a"
        rows.append([key, fmt(old), fmt(new), change])

    st.write(f"Varying **{variable}** by a factor of **{factor:.2f}**.")
    st.dataframe(pd.DataFrame(rows, columns=["Quantity", "Original", "New", "Change"]), use_container_width=True, hide_index=True)

    if variable == "km":
        st.info("Increasing km usually decreases C, so the bolt receives less of the external load increment.")
    elif variable == "kb":
        st.info("Increasing kb usually increases C, so the bolt receives more of the external load increment.")
    elif variable == "Fi":
        st.info("Increasing preload improves separation resistance but also increases initial bolt stress.")
    elif variable == "At":
        st.info("Increasing tensile stress area reduces bolt stresses and usually improves static and fatigue FOS.")
    elif variable == "d":
        st.info("Increasing diameter strongly improves shear capacity because shear area scales with d².")

with tab4:
    st.header("Parametric Plots")

    st.write(
        "Use this section to visualize how changing one design parameter affects "
        "load sharing, bolt load, separation, proof safety factor, and fatigue safety factor."
    )

    sweep_var = st.selectbox(
        "Parameter to vary",
        ["km", "kb", "Fi", "P", "At", "d", "Pmax", "Pmin"],
        key="sweep_var",
    )

    base_value = getattr(x, sweep_var)

    col_a, col_b = st.columns(2)

    with col_a:
        min_factor = st.number_input(
            "Minimum multiplier",
            value=0.25,
            min_value=0.01,
            max_value=10.0,
            step=0.05,
        )

    with col_b:
        max_factor = st.number_input(
            "Maximum multiplier",
            value=3.0,
            min_value=0.01,
            max_value=10.0,
            step=0.05,
        )

    n_points = st.slider("Number of points", 10, 200, 80)

    factors = [
        min_factor + i * (max_factor - min_factor) / (n_points - 1)
        for i in range(n_points)
    ]

    rows = []

    for factor in factors:
        x_sweep = JointInputs(**asdict(x))
        setattr(x_sweep, sweep_var, base_value * factor)

        r_sweep = compute(x_sweep)

        rows.append(
            {
                sweep_var: base_value * factor,
                "Multiplier": factor,
                "C": r_sweep["C"],
                "Fb": r_sweep["Fb"],
                "Fm": r_sweep["Fm"],
                "np": r_sweep["np"],
                "n0": r_sweep["n0"],
                "sigma_i": r_sweep["sigma_i"],
                "sigma_a": r_sweep["sigma_a"],
                "sigma_m": r_sweep["sigma_m"],
                "nf": r_sweep["nf"],
                "n_shear": r_sweep["n_shear"],
                "n_bearing_bolt": r_sweep["n_bearing_bolt"],
                "n_bearing_member": r_sweep["n_bearing_member"],
            }
        )

    df_sweep = pd.DataFrame(rows)

    output = st.selectbox(
        "Output to plot",
        [
            "C",
            "Fb",
            "Fm",
            "np",
            "n0",
            "sigma_i",
            "sigma_a",
            "sigma_m",
            "nf",
            "n_shear",
            "n_bearing_bolt",
            "n_bearing_member",
        ],
    )

    fig = px.line(
        df_sweep,
        x=sweep_var,
        y=output,
        markers=True,
        title=f"Effect of changing {sweep_var} on {output}",
    )

    fig.update_layout(
        xaxis_title=sweep_var,
        yaxis_title=output,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Design interpretation")

    if sweep_var == "km":
        st.info(
            "As member stiffness km increases, the load fraction C usually decreases. "
            "This means the bolt takes a smaller portion of the external load increment."
        )

    elif sweep_var == "kb":
        st.info(
            "As bolt stiffness kb increases, the load fraction C usually increases. "
            "The bolt attracts more of the external load increment."
        )

    elif sweep_var == "Fi":
        st.info(
            "Increasing preload usually improves separation resistance n0, "
            "but it also increases initial bolt stress."
        )

    elif sweep_var == "At":
        st.info(
            "Increasing tensile stress area At reduces bolt stresses and generally "
            "improves static and fatigue safety factors."
        )

    elif sweep_var == "d":
        st.info(
            "Increasing bolt diameter strongly improves shear resistance because "
            "the shear area scales with d²."
        )

    elif sweep_var in ["P", "Pmax", "Pmin"]:
        st.info(
            "Changing the external load changes bolt load, separation resistance, "
            "and fatigue response. Fatigue is especially sensitive to the load range."
        )

    st.subheader("Sweep data")
    st.dataframe(df_sweep, use_container_width=True)
    
with tab5:
    st.header("AI Tutor")

    api_key = get_api_key()
    if not api_key or genai is None:
        st.warning(
            "AI is not connected yet. The app will use built-in tutoring responses. "
            "To enable real AI chat, add GEMINI_API_KEY to Streamlit secrets."
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    quick = st.selectbox(
        "Quick questions",
        [
            "",
            "Why does increasing member stiffness reduce the load taken by the bolt?",
            "Why does preload improve separation resistance?",
            "How does bolt diameter affect shear factor of safety?",
            "Why does fatigue depend on Pmax minus Pmin?",
            "What should I change first if fatigue FOS is too low?",
        ],
    )

    user_q = st.chat_input("Ask the AI tutor about the current bolted joint...")
    if quick and st.button("Ask selected question"):
        user_q = quick

    if user_q:
        st.session_state.messages.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)

        context = {
            "inputs": asdict(x),
            "results": {k: fmt(v) for k, v in r.items()},
        }

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                ai_answer = ask_ai(st.session_state.messages, context)
                if ai_answer is None:
                    ai_answer = fallback_tutor_answer(user_q, x, r)
                st.markdown(ai_answer)

        st.session_state.messages.append({"role": "assistant", "content": ai_answer})

with tab6:
    st.header("Worked Example: Guided Solution")

    step = st.radio(
        "Where is the student in the solution?",
        [
            "Step 1: Identify inputs",
            "Step 2: Compute load fraction C",
            "Step 3: Compute bolt load",
            "Step 4: Check separation",
            "Step 5: Check fatigue",
            "Step 6: Interpret design",
        ],
    )

    if step.startswith("Step 1"):
        st.write("First list known quantities: geometry, material strengths, preload, external loads, and stiffnesses.")
    elif step.startswith("Step 2"):
        st.latex(r"C=\frac{k_b}{k_b+k_m}")
        st.write(f"Using the current inputs, C = **{fmt(r['C'])}**.")
    elif step.startswith("Step 3"):
        st.latex(r"F_b=F_i+CP")
        st.write(f"Using the current inputs, Fb = **{fmt(r['Fb'])}**.")
    elif step.startswith("Step 4"):
        st.latex(r"n_0=\frac{F_i}{(1-C)P}")
        st.write(f"Using the current inputs, n0 = **{fmt(r['n0'])}**.")
    elif step.startswith("Step 5"):
        st.write(f"sigma_i = **{fmt(r['sigma_i'])}**")
        st.write(f"sigma_a = **{fmt(r['sigma_a'])}**")
        st.write(f"sigma_m = **{fmt(r['sigma_m'])}**")
        st.write(f"nf = **{fmt(r['nf'])}**")
    else:
        st.write("Design interpretation should connect variables to physical behavior: preload controls separation, stiffness ratio controls load sharing, area controls stress, and load range controls fatigue.")

st.markdown("---")
st.caption("Teaching note: Use this app for conceptual exploration. Students should still show assumptions, units, and hand calculations.")

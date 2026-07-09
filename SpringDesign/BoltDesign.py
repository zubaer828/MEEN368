import os
import math
from dataclasses import dataclass, asdict

import pandas as pd
import streamlit as st
import plotly.express as px

try:
    from google import genai
except Exception:
    genai = None

st.set_page_config(page_title="Spring Design AI Tutor", page_icon="🌀", layout="wide")


def safe_div(a, b):
    return None if b == 0 else a / b


def fmt(v):
    if v is None:
        return "undefined"
    try:
        if math.isnan(v) or math.isinf(v):
            return "undefined"
    except Exception:
        pass
    return f"{v:.4g}"


@dataclass
class SpringInputs:
    F: float = 100.0
    Fmax: float = 150.0
    Fmin: float = 50.0
    D: float = 25.0
    d: float = 3.0
    Na: float = 10.0
    Nt: float = 12.0
    L0: float = 80.0
    E: float = 200000.0
    G: float = 77000.0
    Sut: float = 1400.0
    Sys: float = 630.0
    Ssu: float = 938.0
    Ssa: float = 241.0
    Ssm: float = 379.0
    alpha: float = 1.0
    conical_R1: float = 8.0
    conical_R2: float = 20.0


def compute(x: SpringInputs):
    C = safe_div(x.D, x.d)
    KB = safe_div(4*C + 2, 4*C - 3) if C is not None else None
    Ks = safe_div(2*C + 1, 2*C) if C is not None else None
    tau = KB * safe_div(8*x.F*x.D, math.pi*x.d**3) if KB is not None else None

    Ls = x.d * x.Nt
    delta_s = x.L0 - Ls
    p = safe_div(x.L0 - 2*x.d, x.Na)
    Ne = x.Nt - x.Na

    delta = safe_div(8*x.F*x.D**3*x.Na, x.d**4*x.G)
    if delta is not None and C is not None:
        delta *= (1 + safe_div(1, 2*C**2))
    k = safe_div(x.F, delta) if delta not in [None, 0] else None
    Fs = k * delta_s if k is not None else None
    tau_s = KB * safe_div(8*Fs*x.D, math.pi*x.d**3) if KB is not None and Fs is not None else None

    slenderness = safe_div(x.L0, x.D)
    stability_limit = None
    stable = None
    root_arg = safe_div(2*(x.E - x.G), 2*x.G + x.E)
    if root_arg is not None and root_arg > 0 and x.alpha != 0:
        stability_limit = math.pi / x.alpha * math.sqrt(root_arg)
        stable = slenderness < stability_limit if slenderness is not None else None

    Fa = (x.Fmax - x.Fmin)/2
    Fm = (x.Fmax + x.Fmin)/2
    tau_a = KB * safe_div(8*Fa*x.D, math.pi*x.d**3) if KB is not None else None
    tau_m = KB * safe_div(8*Fm*x.D, math.pi*x.d**3) if KB is not None else None
    ny = safe_div(math.pi*x.d**3*x.Sys, 8*KB*Fs*x.D) if KB not in [None, 0] and Fs not in [None, 0] else None

    Sse_goodman = safe_div(x.Ssa, 1 - safe_div(x.Ssm, x.Ssu))
    Sse_gerber = safe_div(x.Ssa, 1 - (safe_div(x.Ssm, x.Ssu))**2) if x.Ssu != 0 else None
    nf_goodman = safe_div(1, tau_a/Sse_goodman + tau_m/x.Ssu) if tau_a not in [None, 0] and tau_m is not None and Sse_goodman not in [None, 0] and x.Ssu != 0 else None

    nf_gerber = None
    if tau_a not in [None, 0] and tau_m not in [None, 0] and Sse_gerber not in [None, 0] and x.Ssu != 0:
        bracket = -1 + math.sqrt(1 + (safe_div(2*tau_m*Sse_gerber, x.Ssu*tau_a))**2)
        nf_gerber = 0.5 * (x.Ssu/tau_m)**2 * (tau_a/Sse_gerber) * bracket

    denom_shape = (x.conical_R2 + x.conical_R1) * (x.conical_R2**2 + x.conical_R1**2)
    delta_conical = x.F * safe_div(16*x.Na*denom_shape, x.G*x.d**4) if x.G != 0 and x.d != 0 else None
    k_conical = safe_div(x.G*x.d**4, 16*x.Na*denom_shape) if denom_shape != 0 else None

    return {"C": C, "KB": KB, "Ks": Ks, "tau": tau, "delta": delta, "k": k,
            "Ls": Ls, "delta_s": delta_s, "Fs": Fs, "tau_s": tau_s, "p": p, "Ne": Ne,
            "slenderness": slenderness, "stability_limit": stability_limit, "stable": stable,
            "Fa": Fa, "Fm": Fm, "tau_a": tau_a, "tau_m": tau_m, "ny": ny,
            "Sse_goodman": Sse_goodman, "Sse_gerber": Sse_gerber,
            "nf_goodman": nf_goodman, "nf_gerber": nf_gerber,
            "delta_conical": delta_conical, "k_conical": k_conical}


SYSTEM_PROMPT = """
You are an AI tutor for mechanical design, specifically helical compression springs.
Teach conceptually and step by step. Do not merely give final answers.
Use the current numerical context provided by the app.
Explain physical meaning, equations, assumptions, and design tradeoffs.
Ask Socratic questions when helpful. Remind students to check units.

Equations:
C = D/d
KB = (4C + 2)/(4C - 3)
Ks = (2C + 1)/(2C)
tau = KB*8FD/(pi d^3)
delta = 8FD^3Na/(d^4G)*(1 + 1/(2C^2))
k = F/delta = Gd^4/(8D^3Na)/(1 + 1/(2C^2))
Ls = dNt, delta_s = L0 - Ls, p = (L0 - 2d)/Na
L0/D < pi/alpha*sqrt(2(E-G)/(2G+E))
Fa = (Fmax-Fmin)/2, Fm = (Fmax+Fmin)/2
tau_a = KB*8FaD/(pi d^3), tau_m = KB*8FmD/(pi d^3)
ny = pi d^3 Sys/(8KB Fs D)
nf Goodman = 1/(tau_a/Sse + tau_m/Ssu)
Sse Goodman = Ssa/(1 - Ssm/Ssu)
Sse Gerber = Ssa/(1 - (Ssm/Ssu)^2)
Conical: delta = F*16Na(R2+R1)(R2^2+R1^2)/(Gd^4)
Conical: k = Gd^4/[16Na(R2+R1)(R2^2+R1^2)]
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
    conversation_text = "".join([f'{m["role"].upper()}:\n{m["content"]}\n\n' for m in messages])
    prompt = f"""{SYSTEM_PROMPT}\n\nCurrent app context:\nInputs:\n{context['inputs']}\n\nComputed results:\n{context['results']}\n\nConversation:\n{conversation_text}\nRespond as a compression-spring design tutor."""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text


def fallback_tutor_answer(question, x, r):
    q = question.lower()
    if "diameter" in q or "wire" in q:
        return f"""
Wire diameter d has a very strong effect because stress scales with 1/d³ and deflection scales with 1/d⁴.

Current values:
C = {fmt(r['C'])}
tau = {fmt(r['tau'])}
delta = {fmt(r['delta'])}
k = {fmt(r['k'])}

Increasing d greatly reduces stress and deflection, but it also changes the spring index C = D/d.
"""
    if "spring index" in q or " c" in q:
        return f"""
Spring index is C = D/d = {fmt(r['C'])}.
It affects the Bergstrasser correction factor KB = (4C + 2)/(4C - 3) = {fmt(r['KB'])}.
A small C means a tightly wound spring and higher stress concentration.
"""
    if "fatigue" in q:
        return f"""
For fatigue:
Fa = {fmt(r['Fa'])}, Fm = {fmt(r['Fm'])}
tau_a = {fmt(r['tau_a'])}, tau_m = {fmt(r['tau_m'])}
Goodman nf = {fmt(r['nf_goodman'])}, Gerber nf = {fmt(r['nf_gerber'])}.
"""
    if "stability" in q or "buckling" in q:
        status = "stable" if r["stable"] else "not stable"
        return f"L0/D = {fmt(r['slenderness'])}; limit = {fmt(r['stability_limit'])}. The design is **{status}** by this criterion."
    return f"""
Current key results:
C = {fmt(r['C'])}, KB = {fmt(r['KB'])}, tau = {fmt(r['tau'])}, delta = {fmt(r['delta'])}, k = {fmt(r['k'])}, ny = {fmt(r['ny'])}, nf Goodman = {fmt(r['nf_goodman'])}, nf Gerber = {fmt(r['nf_gerber'])}.

Try asking: Why does wire diameter affect stress so strongly? How do Fmax and Fmin affect fatigue? How do I check stability?
"""

st.title("🌀 Spring Design AI Tutor")

st.caption(
    "Interactive equation explorer, parametric plots, what-if analysis, and AI tutoring for helical and conical compression springs • "
    "Developed by **Dr. Zubaer Hossain**, Department of Mechanical Engineering, Texas A&M University • "
)

st.info("""
**Open Educational Resource**

This calculator is freely available for educational use. Send questions or comments to [zubaer@tamu.edu](mailto:zubaer@tamu.edu)
""")

with st.sidebar:
    st.header("Inputs")
    st.subheader("Loads")
    F = st.number_input("Applied force, F", value=100.0)
    Fmax = st.number_input("Maximum force, Fmax", value=150.0)
    Fmin = st.number_input("Minimum force, Fmin", value=50.0)
    st.subheader("Helical spring geometry")
    D = st.number_input("Mean spring diameter, D", value=25.0)
    d = st.number_input("Wire diameter, d", value=3.0)
    Na = st.number_input("Active coils, Na", value=10.0)
    Nt = st.number_input("Total coils, Nt", value=12.0)
    L0 = st.number_input("Free length, L0", value=80.0)
    st.subheader("Material")
    E = st.number_input("Young's modulus, E", value=200000.0)
    G = st.number_input("Shear modulus, G", value=77000.0)
    Sut = st.number_input("Ultimate strength, Sut", value=1400.0)
    Sys = st.number_input("Yield strength in torsion, Sys", value=630.0)
    Ssu = st.number_input("Rupture strength in torsion, Ssu", value=938.0)
    Ssa = st.number_input("Zimmerli amplitude strength, Ssa", value=241.0)
    Ssm = st.number_input("Zimmerli mean strength, Ssm", value=379.0)
    st.subheader("Stability and conical spring")
    alpha = st.number_input("End-condition parameter, alpha", value=1.0)
    conical_R1 = st.number_input("Conical small radius, R1", value=8.0)
    conical_R2 = st.number_input("Conical large radius, R2", value=20.0)

x = SpringInputs(F=F, Fmax=Fmax, Fmin=Fmin, D=D, d=d, Na=Na, Nt=Nt, L0=L0, E=E, G=G, Sut=Sut, Sys=Sys, Ssu=Ssu, Ssa=Ssa, Ssm=Ssm, alpha=alpha, conical_R1=conical_R1, conical_R2=conical_R2)
r = compute(x)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Equation Explorer", "Design Summary", "Parametric Plots", "What-if Analysis", "AI Tutor", "Guided Example"])

with tab1:
    st.header("Equation Explorer")
    eq = st.selectbox("Select equation group", ["Stress", "Stiffness", "Solid length and pitch", "Stability", "Fatigue", "Conical spring", "Strength estimates"])
    if eq == "Stress":
        st.latex(r"C=\frac{D}{d}")
        st.latex(r"K_B=\frac{4C+2}{4C-3}")
        st.latex(r"\tau=K_B\frac{8FD}{\pi d^3}")
        st.latex(r"\tau_s=K_B\frac{8F_sD}{\pi d^3}")
        st.write(f"C = **{fmt(r['C'])}**, KB = **{fmt(r['KB'])}**, tau = **{fmt(r['tau'])}**")
    elif eq == "Stiffness":
        st.latex(r"\delta=\frac{8FD^3N_a}{d^4G}\left(1+\frac{1}{2C^2}\right)")
        st.latex(r"k=\frac{F}{\delta}=\frac{Gd^4}{8D^3N_a}\left(\frac{1}{1+\frac{1}{2C^2}}\right)")
        st.write(f"delta = **{fmt(r['delta'])}**, k = **{fmt(r['k'])}**")
    elif eq == "Solid length and pitch":
        st.latex(r"L_s=dN_t")
        st.latex(r"\delta_s=L_0-L_s")
        st.latex(r"p=\frac{L_0-2d}{N_a}")
        st.write(f"Ls = **{fmt(r['Ls'])}**, delta_s = **{fmt(r['delta_s'])}**, pitch = **{fmt(r['p'])}**")
    elif eq == "Stability":
        st.latex(r"\frac{L_0}{D}<\frac{\pi}{\alpha}\sqrt{\frac{2(E-G)}{2G+E}}")
        status = "Stable by this criterion" if r["stable"] else "Not stable by this criterion"
        st.write(f"L0/D = **{fmt(r['slenderness'])}**, limit = **{fmt(r['stability_limit'])}**")
        st.info(status)
    elif eq == "Fatigue":
        st.latex(r"F_a=\frac{F_{\max}-F_{\min}}{2},\quad F_m=\frac{F_{\max}+F_{\min}}{2}")
        st.latex(r"\tau_a=K_B\frac{8F_aD}{\pi d^3},\quad \tau_m=K_B\frac{8F_mD}{\pi d^3}")
        st.latex(r"n_f=\left(\frac{\tau_a}{S_{se}}+\frac{\tau_m}{S_{su}}\right)^{-1}\quad \mathrm{Goodman}")
        st.latex(r"S_{se}=\frac{S_{sa}}{1-S_{sm}/S_{su}}\quad \mathrm{Goodman}")
        st.latex(r"S_{se}=\frac{S_{sa}}{1-(S_{sm}/S_{su})^2}\quad \mathrm{Gerber}")
        st.write(f"tau_a = **{fmt(r['tau_a'])}**, tau_m = **{fmt(r['tau_m'])}**")
        st.write(f"nf Goodman = **{fmt(r['nf_goodman'])}**, nf Gerber = **{fmt(r['nf_gerber'])}**")
    elif eq == "Conical spring":
        st.latex(r"\delta=F\left(\frac{16N_a(R_2+R_1)(R_2^2+R_1^2)}{Gd^4}\right)")
        st.latex(r"k=\frac{Gd^4}{16N_a(R_2+R_1)(R_2^2+R_1^2)}")
        st.write(f"Conical delta = **{fmt(r['delta_conical'])}**, conical k = **{fmt(r['k_conical'])}**")
    else:
        st.latex(r"0.35S_{ut}\leq S_{ys}\leq 0.52S_{ut}")
        st.latex(r"S_{su}=0.67S_{ut}")
        st.write(f"0.35Sut = **{fmt(0.35*x.Sut)}**, 0.52Sut = **{fmt(0.52*x.Sut)}**, Ssu estimate = **{fmt(0.67*x.Sut)}**")

with tab2:
    st.header("Design Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spring index C", fmt(r["C"]))
    c2.metric("Stress tau", fmt(r["tau"]))
    c3.metric("Deflection delta", fmt(r["delta"]))
    c4.metric("Stiffness k", fmt(r["k"]))
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Yield FOS ny", fmt(r["ny"]))
    c6.metric("Fatigue FOS Goodman", fmt(r["nf_goodman"]))
    c7.metric("Fatigue FOS Gerber", fmt(r["nf_gerber"]))
    c8.metric("L0/D", fmt(r["slenderness"]))
    st.subheader("All calculated quantities")
    df = pd.DataFrame([{"Quantity": key, "Value": fmt(value)} for key, value in r.items()])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.subheader("Dependency map")
    st.markdown("""
`D, d → C → KB → tau, tau_a, tau_m`

`F, D, d → tau`

`F, D, d, Na, G → delta → k`

`Nt, d → Ls`

`L0, D, E, G, alpha → stability`

`Fmax, Fmin → Fa, Fm → tau_a, tau_m → fatigue FOS`
""")

with tab3:
    st.header("Parametric Plots")
    sweep_var = st.selectbox("Parameter to vary", ["d", "D", "Na", "Nt", "L0", "F", "Fmax", "Fmin", "G", "Sut", "Sys", "Ssu", "Ssa", "Ssm"])
    base_value = getattr(x, sweep_var)
    col1, col2 = st.columns(2)
    with col1:
        min_factor = st.number_input("Minimum multiplier", value=0.5, min_value=0.01, max_value=10.0, step=0.05)
    with col2:
        max_factor = st.number_input("Maximum multiplier", value=2.0, min_value=0.01, max_value=10.0, step=0.05)
    n_points = st.slider("Number of points", 10, 200, 80)
    output = st.selectbox("Output to plot", ["C", "KB", "tau", "delta", "k", "Fs", "tau_s", "ny", "nf_goodman", "nf_gerber", "slenderness", "stability_limit", "delta_conical", "k_conical"])
    rows = []
    for i in range(n_points):
        factor = min_factor + i*(max_factor - min_factor)/(n_points - 1)
        xs = SpringInputs(**asdict(x))
        setattr(xs, sweep_var, base_value * factor)
        rs = compute(xs)
        row = {sweep_var: base_value * factor, "Multiplier": factor}
        row.update({key: value for key, value in rs.items() if not isinstance(value, bool)})
        rows.append(row)
    df_sweep = pd.DataFrame(rows)
    fig = px.line(df_sweep, x=sweep_var, y=output, markers=True, title=f"Effect of changing {sweep_var} on {output}")
    fig.update_layout(xaxis_title=sweep_var, yaxis_title=output, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    if sweep_var == "d":
        st.info("Wire diameter is very influential because stress scales with 1/d³ and deflection scales with 1/d⁴.")
    elif sweep_var == "D":
        st.info("Mean diameter increases stress and strongly increases deflection because deflection scales with D³.")
    elif sweep_var == "Na":
        st.info("More active coils make the spring more flexible, increasing deflection and reducing stiffness.")
    elif sweep_var in ["F", "Fmax", "Fmin"]:
        st.info("Loads directly affect stress and fatigue. Fatigue depends on both mean force and force amplitude.")
    st.subheader("Sweep data")
    st.dataframe(df_sweep, use_container_width=True)

with tab4:
    st.header("What-if Analysis")
    variable = st.selectbox("Choose one variable to change", ["d", "D", "Na", "Nt", "L0", "F", "Fmax", "Fmin", "G", "Sys", "Ssu"])
    factor = st.slider("Change multiplier", 0.25, 3.0, 1.25, 0.05)
    x2 = SpringInputs(**asdict(x))
    setattr(x2, variable, getattr(x2, variable) * factor)
    r2 = compute(x2)
    rows = []
    keys = ["C", "KB", "tau", "delta", "k", "Ls", "Fs", "tau_s", "ny", "tau_a", "tau_m", "nf_goodman", "nf_gerber", "slenderness"]
    for key in keys:
        old = r[key]
        new = r2[key]
        change = f"{100*(new-old)/old:+.1f}%" if old not in [None, 0] and new is not None else "n/a"
        rows.append([key, fmt(old), fmt(new), change])
    st.dataframe(pd.DataFrame(rows, columns=["Quantity", "Original", "New", "Change"]), use_container_width=True, hide_index=True)

with tab5:
    st.header("AI Tutor")
    api_key = get_api_key()
    if not api_key or genai is None:
        st.warning("Gemini is not connected. The app will use built-in tutoring responses. Add GEMINI_API_KEY to Streamlit secrets to enable real AI chat.")
    if "spring_messages" not in st.session_state:
        st.session_state.spring_messages = []
    for m in st.session_state.spring_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    quick = st.selectbox("Quick questions", ["", "Why does wire diameter affect spring stress so strongly?", "What is the physical meaning of spring index C?", "Why does increasing active coils reduce stiffness?", "How do Fmax and Fmin affect fatigue factor of safety?", "How do I check spring stability?", "What should I change if the fatigue FOS is too low?"])
    user_q = st.chat_input("Ask the spring-design tutor...")
    if quick and st.button("Ask selected question"):
        user_q = quick
    if user_q:
        st.session_state.spring_messages.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)
        context = {"inputs": asdict(x), "results": {k: fmt(v) for k, v in r.items()}}
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ask_ai(st.session_state.spring_messages, context)
                if answer is None:
                    answer = fallback_tutor_answer(user_q, x, r)
                st.markdown(answer)
        st.session_state.spring_messages.append({"role": "assistant", "content": answer})

with tab6:
    st.header("Guided Example")
    step = st.radio("Choose solution step", ["Step 1: Compute spring index", "Step 2: Compute correction factor", "Step 3: Compute stress", "Step 4: Compute deflection and stiffness", "Step 5: Check solid length and stability", "Step 6: Check fatigue", "Step 7: Interpret design changes"])
    if step.startswith("Step 1"):
        st.latex(r"C=\frac{D}{d}")
        st.write(f"C = {fmt(r['C'])}")
    elif step.startswith("Step 2"):
        st.latex(r"K_B=\frac{4C+2}{4C-3}")
        st.write(f"KB = {fmt(r['KB'])}")
    elif step.startswith("Step 3"):
        st.latex(r"\tau=K_B\frac{8FD}{\pi d^3}")
        st.write(f"tau = {fmt(r['tau'])}")
    elif step.startswith("Step 4"):
        st.latex(r"\delta=\frac{8FD^3N_a}{d^4G}\left(1+\frac{1}{2C^2}\right)")
        st.latex(r"k=\frac{F}{\delta}")
        st.write(f"delta = {fmt(r['delta'])}, k = {fmt(r['k'])}")
    elif step.startswith("Step 5"):
        st.latex(r"L_s=dN_t")
        st.latex(r"\frac{L_0}{D}<\frac{\pi}{\alpha}\sqrt{\frac{2(E-G)}{2G+E}}")
        st.write(f"Ls = {fmt(r['Ls'])}, L0/D = {fmt(r['slenderness'])}, limit = {fmt(r['stability_limit'])}")
    elif step.startswith("Step 6"):
        st.latex(r"\tau_a=K_B\frac{8F_aD}{\pi d^3},\quad \tau_m=K_B\frac{8F_mD}{\pi d^3}")
        st.write(f"tau_a = {fmt(r['tau_a'])}, tau_m = {fmt(r['tau_m'])}")
        st.write(f"nf Goodman = {fmt(r['nf_goodman'])}, nf Gerber = {fmt(r['nf_gerber'])}")
    else:
        st.write("Design changes should be interpreted physically: larger d reduces stress and deflection; larger D increases stress and deflection; larger Na reduces stiffness; load range affects fatigue.")

st.markdown("---")
st.caption("Teaching note: Use consistent units. For example, N, mm, MPa or lb, in, psi.")

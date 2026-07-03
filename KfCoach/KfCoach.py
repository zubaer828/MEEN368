import math
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="TAMU Mechanics: Kf Calculator",
    page_icon="⚙️",
    layout="wide"
)

# ----------------------------
# Custom CSS
# ----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

body, p, div[data-testid="stMarkdownContainer"] p,
label, button, input, textarea {
    font-family: 'Inter', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif !important;
}

.katex, .katex *, .MathJax, .MathJax * {
    font-family: KaTeX_Main, "Times New Roman", serif !important;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------
# Functions
# ----------------------------
def sqrt_a_bending_axial(Sut, unit):
    if unit == "kpsi":
        return 0.246 - 3.08e-3 * Sut + 1.51e-5 * Sut**2 - 2.67e-8 * Sut**3
    return 1.24 - 2.25e-3 * Sut + 1.60e-6 * Sut**2 - 4.11e-10 * Sut**3


def sqrt_a_torsion(Sut, unit):
    if unit == "kpsi":
        return 0.190 - 2.51e-3 * Sut + 1.35e-5 * Sut**2 - 2.67e-8 * Sut**3
    return 0.958 - 1.83e-3 * Sut + 1.43e-6 * Sut**2 - 4.11e-10 * Sut**3


def calculate_kf(Kt, Sut, r, loading, unit):
    if loading == "Bending or axial":
        sqrt_a = sqrt_a_bending_axial(Sut, unit)
    else:
        sqrt_a = sqrt_a_torsion(Sut, unit)

    q = 1.0 / (1.0 + sqrt_a / math.sqrt(r))
    Kf = 1.0 + q * (Kt - 1.0)

    return Kf, sqrt_a, q


# ----------------------------
# Header
# ----------------------------
st.title("TAMU Mechanics: Fatigue Stress Concentration Factor Calculator")

st.info("""
**Open Educational Resource**

This calculator is freely available for educational use.
""")

st.caption(
    "Developed by **Dr. Zubaer Hossain**, Texas A&M University • "
    "Questions or comments: [zubaer@tamu.edu](mailto:zubaer@tamu.edu)"
)

st.write("""
This app calculates the fatigue stress concentration factor, \(K_f\), using the notch sensitivity relation. 
Students can change material strength, notch radius, loading type, unit system, and static stress concentration factor.
""")

st.divider()


# ----------------------------
# Inputs on main page
# ----------------------------
st.header("Inputs")

input_col1, input_col2, input_col3 = st.columns(3)

with input_col1:
    unit_label = st.selectbox(
        "Unit system",
        ["MPa and mm", "kpsi and in"]
    )

unit = "MPa" if unit_label == "MPa and mm" else "kpsi"

with input_col2:
    loading = st.selectbox(
        "Loading type",
        ["Bending or axial", "Torsion"]
    )

with input_col3:
    Kt = st.slider(
        "Static stress concentration factor, Kt",
        min_value=1.00,
        max_value=5.00,
        value=2.00,
        step=0.01
    )

if unit == "MPa":
    r_unit = "mm"

    if loading == "Bending or axial":
        Sut_min, Sut_max, Sut_default = 340, 1700, 600
    else:
        Sut_min, Sut_max, Sut_default = 340, 1500, 600

    r_min, r_max, r_default, r_step = 0.1, 20.0, 2.0, 0.1

else:
    r_unit = "in"

    if loading == "Bending or axial":
        Sut_min, Sut_max, Sut_default = 50, 250, 90
    else:
        Sut_min, Sut_max, Sut_default = 50, 220, 90

    r_min, r_max, r_default, r_step = 0.005, 1.0, 0.100, 0.005


Sut = st.slider(
    f"Ultimate tensile strength, Sut ({unit})",
    min_value=Sut_min,
    max_value=Sut_max,
    value=Sut_default,
    step=10 if unit == "MPa" else 1
)

r = st.slider(
    f"Notch radius, r ({r_unit})",
    min_value=r_min,
    max_value=r_max,
    value=r_default,
    step=r_step
)

Kf, sqrt_a, q = calculate_kf(Kt, Sut, r, loading, unit)

result_col1, result_col2, result_col3, result_col4 = st.columns(4)

with result_col1:
    st.metric("Kt", f"{Kt:.3f}")

with result_col2:
    st.metric("√a", f"{sqrt_a:.4f} {r_unit}^0.5")

with result_col3:
    st.metric("q", f"{q:.3f}")

with result_col4:
    st.metric("Kf", f"{Kf:.3f}")

st.divider()


# ----------------------------
# Equations
# ----------------------------
st.header("Equations Used")

st.write("The fatigue stress concentration factor is")

st.latex(r"""
K_f = 1 + \frac{K_t - 1}{1 + \sqrt{a/r}}
""")

st.write("The notch sensitivity factor is")

st.latex(r"""
q = \frac{K_f - 1}{K_t - 1}
""")

st.write("Therefore,")

st.latex(r"""
K_f = 1 + q(K_t - 1)
""")

st.subheader("Material parameter, \( \sqrt{a} \)")

st.write("For bending or axial loading:")

st.latex(r"""
\sqrt{a}
=
0.246 - 3.08(10^{-3})S_{ut}
+ 1.51(10^{-5})S_{ut}^{2}
- 2.67(10^{-8})S_{ut}^{3}
\qquad
50 \le S_{ut} \le 250 \text{ kpsi}
""")

st.latex(r"""
\sqrt{a}
=
1.24 - 2.25(10^{-3})S_{ut}
+ 1.60(10^{-6})S_{ut}^{2}
- 4.11(10^{-10})S_{ut}^{3}
\qquad
340 \le S_{ut} \le 1700 \text{ MPa}
""")

st.write("For torsion:")

st.latex(r"""
\sqrt{a}
=
0.190 - 2.51(10^{-3})S_{ut}
+ 1.35(10^{-5})S_{ut}^{2}
- 2.67(10^{-8})S_{ut}^{3}
\qquad
50 \le S_{ut} \le 220 \text{ kpsi}
""")

st.latex(r"""
\sqrt{a}
=
0.958 - 1.83(10^{-3})S_{ut}
+ 1.43(10^{-6})S_{ut}^{2}
- 4.11(10^{-10})S_{ut}^{3}
\qquad
340 \le S_{ut} \le 1500 \text{ MPa}
""")

st.info(
    "\(K_t\) depends only on geometry and loading. "
    "\(K_f\) accounts for finite notch sensitivity of real materials. "
    "Therefore, usually \(K_f \\le K_t\)."
)

st.divider()


# ----------------------------
# Calculation details
# ----------------------------
st.header("Calculation Details")

st.latex(
    rf"""
    K_f
    =
    1 + \frac{{{Kt:.3f} - 1}}{{1 + {sqrt_a:.4f}/\sqrt{{{r:.4f}}}}}
    =
    {Kf:.3f}
    """
)

if q < 0.33:
    interpretation = "The notch sensitivity is low."
elif q < 0.67:
    interpretation = "The notch sensitivity is moderate."
else:
    interpretation = "The notch sensitivity is high."

st.write(
    f"For the selected case, \(K_f = {Kf:.3f}\). "
    f"The corresponding notch sensitivity is \(q = {q:.3f}\). "
    f"{interpretation}"
)

st.divider()


# ----------------------------
# Plots
# ----------------------------
st.header("Plots")

plot_col1, plot_col2 = st.columns(2)

with plot_col1:
    st.subheader("$K_f$ versus $S_{ut}$")

    Sut_values = np.linspace(Sut_min, Sut_max, 300)
    Kf_values_sut = [
        calculate_kf(Kt, s, r, loading, unit)[0]
        for s in Sut_values
    ]

    fig1, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(Sut_values, Kf_values_sut, linewidth=2)
    ax1.scatter([Sut], [Kf], s=60)
    ax1.set_xlabel(f"$S_{{ut}}$ ({unit})")
    ax1.set_ylabel("$K_f$")
    ax1.set_title("$K_f$ versus $S_{ut}$")
    ax1.grid(True)
    st.pyplot(fig1)

with plot_col2:
    st.subheader("$K_f$ versus notch radius, $r$")

    r_values = np.linspace(r_min, r_max, 300)
    Kf_values_r = [
        calculate_kf(Kt, Sut, rr, loading, unit)[0]
        for rr in r_values
    ]

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.plot(r_values, Kf_values_r, linewidth=2)
    ax2.scatter([r], [Kf], s=60)
    ax2.set_xlabel(f"$r$ ({r_unit})")
    ax2.set_ylabel("$K_f$")
    ax2.set_title("$K_f$ versus notch radius")
    ax2.grid(True)
    st.pyplot(fig2)

st.divider()


# ----------------------------
# Summary table and download
# ----------------------------
st.header("Summary Table")

summary_data = {
    "Quantity": [
        "Loading type",
        "Unit system",
        "Sut",
        "r",
        "Kt",
        "√a",
        "q",
        "Kf"
    ],
    "Value": [
        loading,
        unit_label,
        f"{Sut:.3f} {unit}",
        f"{r:.4f} {r_unit}",
        f"{Kt:.3f}",
        f"{sqrt_a:.4f} {r_unit}^0.5",
        f"{q:.3f}",
        f"{Kf:.3f}"
    ]
}

st.table(summary_data)

csv_text = (
    "Quantity,Value\n"
    f"Loading type,{loading}\n"
    f"Unit system,{unit_label}\n"
    f"Sut,{Sut:.3f} {unit}\n"
    f"r,{r:.4f} {r_unit}\n"
    f"Kt,{Kt:.3f}\n"
    f"sqrt_a,{sqrt_a:.4f} {r_unit}^0.5\n"
    f"q,{q:.3f}\n"
    f"Kf,{Kf:.3f}\n"
)

st.download_button(
    label="Download results as CSV",
    data=csv_text,
    file_name="kf_results.csv",
    mime="text/csv"
)

st.divider()

st.caption(
    "MEEN 368: Solid Mechanics in Mechanical Design | Texas A&M University | "
    "Questions/comments: zubaer@tamu.edu"
)

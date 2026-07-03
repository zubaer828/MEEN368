import math
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="MEEN 368 Kf Coach",
    page_icon="⚙️",
    layout="wide"
)

st.title("MEEN 368: Fatigue Stress Concentration Factor Coach")

st.write("""
This app calculates the fatigue stress concentration factor, \(K_f\), using the notch sensitivity relation.
Students can change material strength, notch radius, loading type, unit system, and theoretical stress concentration factor.
""")

st.divider()

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
    "Here, \(K_t\) depends only on geometry and loading. "
    "\(K_f\) accounts for the finite notch sensitivity of real materials. "
    "Usually, \(K_f \\le K_t\)."
)

st.divider()


def sqrt_a_bending_axial(Sut, unit):
    if unit == "kpsi":
        return (
            0.246
            - 3.08e-3 * Sut
            + 1.51e-5 * Sut**2
            - 2.67e-8 * Sut**3
        )

    return (
        1.24
        - 2.25e-3 * Sut
        + 1.60e-6 * Sut**2
        - 4.11e-10 * Sut**3
    )


def sqrt_a_torsion(Sut, unit):
    if unit == "kpsi":
        return (
            0.190
            - 2.51e-3 * Sut
            + 1.35e-5 * Sut**2
            - 2.67e-8 * Sut**3
        )

    return (
        0.958
        - 1.83e-3 * Sut
        + 1.43e-6 * Sut**2
        - 4.11e-10 * Sut**3
    )


def calculate_kf(Kt, Sut, r, loading, unit):
    if loading == "Bending or axial":
        sqrt_a = sqrt_a_bending_axial(Sut, unit)
    else:
        sqrt_a = sqrt_a_torsion(Sut, unit)

    if sqrt_a <= 0:
        return None, sqrt_a, None

    q = 1.0 / (1.0 + sqrt_a / math.sqrt(r))
    Kf = 1.0 + q * (Kt - 1.0)

    return Kf, sqrt_a, q


with st.sidebar:
    st.header("Inputs")

    unit_label = st.selectbox(
        "Unit system",
        ["MPa and mm", "kpsi and in"]
    )

    unit = "MPa" if unit_label == "MPa and mm" else "kpsi"

    loading = st.selectbox(
        "Loading type",
        ["Bending or axial", "Torsion"]
    )

    Kt = st.slider(
        "Theoretical stress concentration factor, Kt",
        min_value=1.00,
        max_value=5.00,
        value=2.00,
        step=0.01
    )

    if unit == "MPa":
        if loading == "Bending or axial":
            Sut_min, Sut_max, Sut_default = 340, 1700, 600
        else:
            Sut_min, Sut_max, Sut_default = 340, 1500, 600

        Sut = st.slider(
            "Ultimate tensile strength, Sut (MPa)",
            min_value=Sut_min,
            max_value=Sut_max,
            value=Sut_default,
            step=10
        )

        r = st.slider(
            "Notch radius, r (mm)",
            min_value=0.1,
            max_value=20.0,
            value=2.0,
            step=0.1
        )

        r_unit = "mm"

    else:
        if loading == "Bending or axial":
            Sut_min, Sut_max, Sut_default = 50, 250, 90
        else:
            Sut_min, Sut_max, Sut_default = 50, 220, 90

        Sut = st.slider(
            "Ultimate tensile strength, Sut (kpsi)",
            min_value=Sut_min,
            max_value=Sut_max,
            value=Sut_default,
            step=1
        )

        r = st.slider(
            "Notch radius, r (in)",
            min_value=0.005,
            max_value=1.0,
            value=0.100,
            step=0.005
        )

        r_unit = "in"


Kf, sqrt_a, q = calculate_kf(Kt, Sut, r, loading, unit)

st.header("Calculated Results")

if Kf is None:
    st.error("The selected input produced an invalid value of √a. Please adjust the inputs.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Kt", f"{Kt:.3f}")

with col2:
    st.metric("√a", f"{sqrt_a:.4f} {r_unit}^0.5")

with col3:
    st.metric("q", f"{q:.3f}")

with col4:
    st.metric("Kf", f"{Kf:.3f}")

st.write("For the current input values:")

st.latex(
    rf"""
    K_f
    =
    1 + \frac{{{Kt:.3f} - 1}}{{1 + {sqrt_a:.4f}/\sqrt{{{r:.4f}}}}}
    =
    {Kf:.3f}
    """
)

st.subheader("Physical Interpretation")

st.write(
    f"For the selected case, the fatigue stress concentration factor is "
    f"**Kf = {Kf:.3f}**. Since the selected theoretical stress concentration "
    f"factor is **Kt = {Kt:.3f}**, the material experiences only part of the "
    f"ideal elastic stress concentration under fatigue loading."
)

if q < 0.33:
    st.write("The notch sensitivity is low. The material is relatively insensitive to the notch.")
elif q < 0.67:
    st.write("The notch sensitivity is moderate.")
else:
    st.write("The notch sensitivity is high. The material is strongly affected by the notch.")

st.divider()

st.header("Plots")

col_plot1, col_plot2 = st.columns(2)

with col_plot1:
    st.subheader("$K_f$ versus $S_{ut}$")

    Sut_values = np.linspace(Sut_min, Sut_max, 300)

    Kf_values_sut = []
    for s in Sut_values:
        kf_temp, _, _ = calculate_kf(Kt, s, r, loading, unit)
        Kf_values_sut.append(kf_temp)

    fig1, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(Sut_values, Kf_values_sut, linewidth=2)
    ax1.scatter([Sut], [Kf], s=60)
    ax1.set_xlabel(f"$S_{{ut}}$ ({unit})")
    ax1.set_ylabel("$K_f$")
    ax1.set_title("$K_f$ versus $S_{ut}$")
    ax1.grid(True)
    st.pyplot(fig1)

with col_plot2:
    st.subheader("$K_f$ versus notch radius, $r$")

    if unit == "MPa":
        r_values = np.linspace(0.1, 20.0, 300)
    else:
        r_values = np.linspace(0.005, 1.0, 300)

    Kf_values_r = []
    for rr in r_values:
        kf_temp, _, _ = calculate_kf(Kt, Sut, rr, loading, unit)
        Kf_values_r.append(kf_temp)

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.plot(r_values, Kf_values_r, linewidth=2)
    ax2.scatter([r], [Kf], s=60)
    ax2.set_xlabel(f"$r$ ({r_unit})")
    ax2.set_ylabel("$K_f$")
    ax2.set_title("$K_f$ versus notch radius")
    ax2.grid(True)
    st.pyplot(fig2)

st.divider()

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

st.caption("MEEN 368 | Solid Mechanics in Mechanical Design | send questions to zubaer@tamu.edu")

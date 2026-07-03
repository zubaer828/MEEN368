import math
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Fatigue Stress Concentration Factor Coach",
    page_icon="⚙️",
    layout="wide"
)

st.title("Fatigue Stress Concentration Factor, $K_f$")

st.write("""
This app calculates the fatigue stress concentration factor using

$K_f = 1 + \\frac{K_t - 1}{1 + \\sqrt{a}/\\sqrt{r}}$

where $K_t$ is the theoretical stress concentration factor, $S_{ut}$ is the ultimate tensile strength, and $r$ is the notch radius.
""")

def sqrt_a_bending_axial(Sut, unit):
    if unit == "kpsi":
        return (
            0.246
            - 3.08e-3 * Sut
            + 1.51e-5 * Sut**2
            - 2.67e-8 * Sut**3
        )
    else:
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
    else:
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

    Kf = 1 + (Kt - 1) / (1 + sqrt_a / math.sqrt(r))
    return Kf, sqrt_a

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
        Sut = st.slider(
            "Ultimate tensile strength, Sut (MPa)",
            min_value=340,
            max_value=1700,
            value=600,
            step=10
        )

        r = st.slider(
            "Notch radius, r (mm)",
            min_value=0.1,
            max_value=20.0,
            value=2.0,
            step=0.1
        )

    else:
        Sut = st.slider(
            "Ultimate tensile strength, Sut (kpsi)",
            min_value=50,
            max_value=250,
            value=90,
            step=1
        )

        r = st.slider(
            "Notch radius, r (in)",
            min_value=0.005,
            max_value=1.0,
            value=0.10,
            step=0.005
        )

Kf, sqrt_a = calculate_kf(Kt, Sut, r, loading, unit)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Kf", f"{Kf:.3f}")

with col2:
    st.metric("√a", f"{sqrt_a:.4f}")

with col3:
    q = (Kf - 1) / (Kt - 1) if Kt > 1 else 0
    st.metric("Notch sensitivity, q", f"{q:.3f}")

st.subheader("Interpretation")

st.write(f"""
For the selected input values, the calculated fatigue stress concentration factor is

$K_f = {Kf:.3f}$.

Since $K_f$ is lower than or equal to $K_t$, the material does not fully experience the theoretical elastic stress concentration under fatigue loading.
""")

st.subheader("$K_f$ versus $S_{ut}$")

if unit == "MPa":
    Sut_values = np.linspace(340, 1700, 200)
else:
    Sut_values = np.linspace(50, 250, 200)

Kf_vs_Sut = [
    calculate_kf(Kt, s, r, loading, unit)[0]
    for s in Sut_values
]

fig1, ax1 = plt.subplots()
ax1.plot(Sut_values, Kf_vs_Sut)
ax1.scatter([Sut], [Kf])
ax1.set_xlabel(f"$S_{{ut}}$ ({unit})")
ax1.set_ylabel("$K_f$")
ax1.set_title("$K_f$ versus $S_{ut}$")
ax1.grid(True)
st.pyplot(fig1)

st.subheader("$K_f$ versus notch radius, $r$")

if unit == "MPa":
    r_values = np.linspace(0.1, 20.0, 200)
    r_unit = "mm"
else:
    r_values = np.linspace(0.005, 1.0, 200)
    r_unit = "in"

Kf_vs_r = [
    calculate_kf(Kt, Sut, rr, loading, unit)[0]
    for rr in r_values
]

fig2, ax2 = plt.subplots()
ax2.plot(r_values, Kf_vs_r)
ax2.scatter([r], [Kf])
ax2.set_xlabel(f"$r$ ({r_unit})")
ax2.set_ylabel("$K_f$")
ax2.set_title("$K_f$ versus notch radius")
ax2.grid(True)
st.pyplot(fig2)

st.info("""
Use this app to explore how material strength and notch radius affect fatigue notch sensitivity.
For very small notch radii, the notch effect is reduced because the material becomes less sensitive to very sharp microscopic notches.
""")
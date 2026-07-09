# Bolted Connection Equation Explorer

A Streamlit app for teaching bolted connections in machine design / mechanics of materials.

## Features

- Tension joint calculator
- Fatigue in preloaded tension joint
- Bolt shear and bearing FOS
- Equation interdependence map
- AI tutor prompt builder

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload `app.py`, `requirements.txt`, and this `README.md`.
3. Go to Streamlit Community Cloud.
4. Select the GitHub repository.
5. Set the main file path to:

```text
app.py
```

6. Deploy.

## Notes

Use consistent units. For example:

- N, MPa, mm, mm²
- or lb, psi/ksi, in, in²

The app does not perform automatic unit conversion.
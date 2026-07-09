# Spring Design AI Tutor

A Streamlit app for helical and conical compression spring design.

## Features

- Equation Explorer
- Design Summary
- Parametric Plots
- What-if Analysis
- AI Tutor using Google Gemini
- Guided worked example

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Enable Gemini AI Tutor

Create a file:

```text
.streamlit/secrets.toml
```

Add:

```toml
GEMINI_API_KEY = "your_google_api_key_here"
```

For Streamlit Community Cloud, add the same line under app Secrets.

The app still works without an API key using built-in tutoring responses.

## Deploy

Upload these files to GitHub:

- app.py
- requirements.txt
- README.md

Then deploy using Streamlit Community Cloud with `app.py` as the main file.

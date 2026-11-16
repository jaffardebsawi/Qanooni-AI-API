# Qanooni AI API

A legal-advisor AI backend. It answers legal questions in English and Arabic, reads attached files (with OCR for
scans), and drafts documents such as NDAs as DOCX/PDF. Chat history is stored in Azure SQL.

It has no screen of its own. You use it through the built-in **Swagger page** (`/docs`) or from the .NET app.

## Run it on Windows

You need two things: **Python 3.12** and the **`.env` file** that Jaffar sends you.

1. **Install Python 3.12** from <https://www.python.org/downloads/>. In the installer, tick **"Add python.exe to PATH"**.
2. **Download this project**: click the green **Code** button on GitHub, then **Download ZIP**, and unzip it.
3. **Put the `.env` file** you were sent into the unzipped folder, next to `run-server.bat`.
4. **Double-click `run-server.bat`.**
   - The first run installs everything and takes a few minutes. Later runs start in seconds.
   - Your browser opens the docs page at <http://127.0.0.1:8000/docs>.

**To stop the server, close the black window.** The server stops with it.

## Project layout

```
run-server.bat       starts the server (Windows)
app/                 the API code
  main.py            all endpoints
  chat.py            streamed AI answers
  generate.py        document drafting
fonts/               Arabic fonts used when making PDFs
.env.example         the settings the API needs
```

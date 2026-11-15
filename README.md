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

## Try it in the docs page

1. Click **Authorize** (top right) and paste the `API_KEY` from your `.env`, then **Authorize**.
2. Open any endpoint, click **Try it out**, fill it in, and click **Execute**.

To chat: run `POST /v1/chats` with a real `user_id` to get a `chat_id`, then `POST /v1/chats/{chat_id}/messages`
with the same `user_id` and your `message`.
The full flow is in [CHAT_CONTRACT.md](CHAT_CONTRACT.md).

## If something goes wrong

| What you see | What to do |
|---|---|
| "Python was not found" | Install Python 3.12 and tick "Add to PATH", then run `run-server.bat` again. |
| "The .env file is missing" | Put the `.env` file in the same folder as `run-server.bat`. |
| `Client with IP address ... is not allowed to access the server` | The database only lets approved computers in. Send Jaffar the IP address from the message so it can be added. |
| `Field required` or a settings error | A value is missing in `.env`. Compare it with `.env.example`. |
| `address already in use` | Another copy is already running. Close the other window. |

## Project layout

```
run-server.bat       starts the server (Windows)
app/                 the API code
  main.py            all endpoints
  chat.py, chatdb.py chat logic and the Azure SQL chat storage
  generate.py        document drafting
fonts/               Arabic fonts used when making PDFs
scripts/create_chat_tables.py   creates the chat tables in SQL (already done once)
.env.example         the settings the API needs
```

## Notes

- `.env` holds passwords. Do not commit it or post it anywhere public.
- Source citations in chat answers are switched off for now (commented out in `app/chat.py`).

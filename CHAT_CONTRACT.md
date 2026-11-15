# Chat contract (.NET <-> Python AI API)

SQL Server (`Qannoni`) is the single source of truth for chat history. Tables `dbo.Chats` and `dbo.ChatMessages`
already exist (created with `scripts/create_chat_tables.py`). **.NET: add matching entities but do NOT generate a
migration that creates them again.**

## Flow
1. New chat page -> `POST /v1/chats` with `{"user_id": "<AppUsers.Id>", "title": "optional"}` returns `{chat_id, ...}`
   (it inserts the row in `dbo.Chats`; .NET may insert the row itself instead, with a new guid as `Id`).
2. User sends a message (optionally with files) -> .NET uploads the files as usual (`dbo.Attachments`), then calls
   `POST /v1/chats/{chat_id}/messages` with header `X-API-Key`:
   ```json
   { "user_id": "<AppUsers.Id>", "message": "text", "attachment_ids": ["<Attachments.Id>"] }
   ```
3. Python loads the last 20 `ChatMessages` plus the chat's attachments as context, calls the AI, then **writes both the
   user message and the AI reply** to `dbo.ChatMessages` (together, or neither). .NET must NOT insert messages.
4. Response (show it immediately; it is already saved):
   ```json
   { "chat_id": "...", "action": "answer" | "generation", "answer": "text", "disclaimer": "...",
     "generation": { "status": "needs_info|complete|revised", "missing": [...], "deliverable": { "download": {...} } } }
   ```
   `generation` is present only when `action` is `generation` (the user asked for a document).
5. Refresh / reopen -> .NET reads `dbo.ChatMessages` for the `ChatId` ordered by `CreatedDate`.

## Errors
`404` chat not found / not owned by `user_id` / deleted. `422` unknown attachment id or file missing on the file server.
Nothing is saved when a call fails, so it is safe to retry.

## ChatMessages columns
`Id`, `ChatId`, `Role` (`user`|`assistant`), `Content`, `AttachmentIds` (JSON array of guids, user messages),
`Extra` (JSON on assistant messages that are document actions: `{"generation": {"generation_id", "status",
"deliverable": {"deliverable_id","title","version","download":{"docx","pdf"}}}}`), `CreatedDate`.
Download links are relative to the Python API and need the `X-API-Key` header, so fetch them server-side.

## Not in the demo
Source citations (code kept, commented out in `app/chat.py`). Tenant handling: everything is `default`.

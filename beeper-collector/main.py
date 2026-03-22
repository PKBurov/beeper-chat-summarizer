import asyncio
import websockets
import json
import psycopg2
import requests

DB_URL = ""
BEEPER_WS = ""
BEEPER_TOKEN = ""
ALLOWED_CHATS = [""]
IGNORED_SENDERS = [""]
N8N_WEBHOOK = ""

IGNORED_BODY_PREFIXES = [
    "m.room.redaction",
    "**Overview",
    "**Summary",
    "*AI Summary",
    "[Media/Attachment]",
    "<p><strong>Overview",
    "<p><strong>Summary",
    "This message has been",
]

processed_summarize_ids = set()

def get_db():
    return psycopg2.connect(DB_URL)

def save_message(conn, chat_id, sender, text, msg_id):
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_logs (chat_id, sender, body, message_id) VALUES (%s, %s, %s, %s) ON CONFLICT (message_id) DO NOTHING",
            (chat_id, sender, text, msg_id)
        )
        conn.commit()
        cur.close()
    except Exception as db_e:
        print(f"Database Error: {db_e}")
        conn.rollback()
        raise

async def listen():
    headers = {"Authorization": f"Bearer {BEEPER_TOKEN}"}

    while True:
        conn = None
        try:
            conn = get_db()
            print("Database connected.")

            print(f"Connecting to Beeper at {BEEPER_WS}...")
            async with websockets.connect(BEEPER_WS, additional_headers=headers) as ws:

                await ws.send(json.dumps({
                    "type": "subscriptions.set",
                    "chatIDs": ALLOWED_CHATS
                }))
                print(f"Connected! Listening to: {ALLOWED_CHATS}")

                async for message in ws:
                    data = json.loads(message)

                    if data.get("type") == "message.upserted":
                        for entry in data.get("entries", []):
                            chat_id = entry.get("chatID")
                            raw_sender = entry.get("sender", "")
                            sender = entry.get("senderName", "User")
                            msg_id = entry.get("id") or entry.get("event_id") or "UNKNOWN"
                            text = entry.get("text", "").strip()

                            if chat_id not in ALLOWED_CHATS:
                                continue
                            if not text:
                                continue
                            if raw_sender in IGNORED_SENDERS:
                                print(f"[IGNORED - own account]: {text[:50]}")
                                continue
                            if any(text.startswith(p) for p in IGNORED_BODY_PREFIXES):
                                print(f"[IGNORED - junk]: {text[:50]}")
                                continue

                            print(f"[{sender}]: {text}")

                            if text.lower() == "/summarize":
                                if msg_id in processed_summarize_ids:
                                    print(f"[IGNORED - duplicate /summarize]: {msg_id}")
                                    continue
                                processed_summarize_ids.add(msg_id)
                                print(f"Triggering n8n for chat: {chat_id}")
                                try:
                                    requests.post(N8N_WEBHOOK, json={"chatID": chat_id})
                                except Exception as req_e:
                                    print(f"Failed to ping n8n webhook: {req_e}")
                            else:
                                try:
                                    save_message(conn, chat_id, sender, text, msg_id)
                                except Exception:
                                    # Reconnect DB if it dropped
                                    conn = get_db()
                                    save_message(conn, chat_id, sender, text, msg_id)

        except Exception as e:
            print(f"Connection Error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    asyncio.run(listen())
# Beeper AI Chat Summarizer (Local MCP Edition)

This project transforms your local machine into a private AI assistant for your Beeper chats. Built on top of the Self-Hosted AI Starter Kit, it utilizes Beeper's local Model Context Protocol (MCP) to securely stream chat messages into a local Postgres database. When a user types `/summarize`, an n8n automation pipeline fetches the recent chat history, processes it through a local LLM (Ollama / Llama 3.2), and beams a formatted summary directly back into the chat. 

100% self-hosted. Zero cloud APIs. Absolute privacy.

## Key Features
* **Total Privacy:** Uses Beeper's local Developer Bridge and Ollama. Your chat logs never touch OpenAI, Google, or any external cloud.
* **On-Demand Summaries:** Just type `/summarize` in your selected Beeper chat to trigger the AI pipeline.
* **Smart Caching:** Maintains a persistent Postgres connection to log messages efficiently and avoid duplicate summaries.
* **Advanced Networking Solutions:** Includes built-in Windows network proxies and registry tweaks to solve common Docker-to-Host communication blocks and socket exhaustion (`WinError 10055`).

---

## Architecture
* **Beeper Local MCP Server:** Enabled via Beeper Developer Options. Exposes a local WebSocket and HTTP API for direct, standard-compliant access to chat streams.
* **Self-Hosted AI Starter Kit:** The Dockerized foundation providing our database, automation engine, and LLM.
* **Python Collector (`main.py`):** Runs natively on Windows. Listens to the Beeper MCP WebSocket, maintains a persistent Postgres connection, and triggers the n8n webhook via API calls.
* **Postgres (Docker):** Stores the chat history and prevents duplicate messages.
* **n8n (Docker):** The automation engine. Grabs chat logs, sends them to Ollama, and POSTs the summary back to Beeper.
* **Ollama (Docker):** Runs the local LLM (`llama3.2:latest`) for sentiment analysis and summarization.

---

## Prerequisites
* Windows OS (Instructions heavily feature Windows networking/PowerShell).
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* The **Self-Hosted AI Starter Kit** cloned and running (`docker-compose up -d`).
* Beeper Desktop installed with **Developer Options / Local Bridge enabled** (Find your Port and Token in Beeper Settings).
* Python 3.x installed.

---

## Step 1: Python MCP Collector Setup

The Python script (`main.py` included in this repo) acts as the middleman between the Beeper MCP server and your Starter Kit. It uses `websockets`, `psycopg2`, and `requests` to listen for messages. 

It specifically maintains a **persistent database connection** to avoid Windows socket exhaustion and ignores the AI's own summary messages (HTML tags) so they don't loop endlessly.

**1. Install dependencies:**
`pip install websockets psycopg2 requests`

**2. Configure `main.py`:**
Open the script and update the configuration variables at the top of the file with your specific credentials:
* `BEEPER_WS` (Ensure the port matches your Beeper settings, e.g., 23375)
* `BEEPER_TOKEN`
* `ALLOWED_CHATS`
* `IGNORED_SENDERS`

**3. Run the script:**
`python main.py`

---

## Step 2: n8n Workflow Configuration

Instead of building the automation from scratch, you can simply import the included workflow into your AI Starter Kit n8n instance!

1. Open your local n8n instance (`http://localhost:5678`).
2. Go to **Workflows** -> **Add Workflow**.
3. Click the **... (Options)** menu in the top right and select **Import from File**.
4. Upload the `workflow.json` file provided in this repository.
5. Update your credentials for Postgres and Ollama inside the nodes.
6. Toggle the workflow to **Publish/Active**.

### Critical Beeper MCP HTTP Request Node Note
Beeper's local API rejects requests originating from Docker containers. The included workflow bypasses this using a `Host: localhost` header spoof. If your Beeper MCP changes ports (e.g., from `23373` to `23375`), make sure to update the URL in the final HTTP Request node.

---

## Step 3: Windows Networking & Docker Fixes

Because n8n runs inside Docker and the Beeper MCP server runs on the Windows host, Docker needs permission to talk to the host machine's `localhost`.

**1. Create a Port Proxy (Run in PowerShell as Administrator):**
This forces Windows to route Docker traffic to the local Beeper API.
`netsh interface portproxy add v4tov4 listenport=23375 listenaddress=0.0.0.0 connectport=23375 connectaddress=127.0.0.1`

**2. Open the Firewall:**
`New-NetFirewallRule -DisplayName "Allow Beeper for n8n" -Direction Inbound -LocalPort 23375 -Protocol TCP -Action Allow`

---

## Step 4: Fixing Windows Socket Exhaustion (WinError 10055)

If you experience network crashes or `WinError 10055`, Windows has likely run out of socket buffer space due to holding old connections to the database and Beeper in a `TIME_WAIT` state for too long.

**Run these registry tweaks in PowerShell as Administrator to fix socket exhaustion permanently:**

```powershell
# Reduce TIME_WAIT duration from 4 minutes to 30 seconds
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "TcpTimedWaitDelay" -Value 30 -Type DWord

# Increase the port range so Windows has more ports to work with
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "MaxUserPort" -Value 65534 -Type DWord

# Allow port reuse faster
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "StrictPortReuse" -Value 1 -Type DWord
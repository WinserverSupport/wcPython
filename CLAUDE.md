# CLAUDE.md -- wcat-agent (WSA) Project Workspace

This file provides guidance to Claude Code when working on the
Wildcat! AI Support Agent (WSA / wcat-agent.py) project.

## Project Overview

**wcat-agent.py** is the Wildcat! AI Support Agent -- a Python script that
monitors configured mailing-list conferences on a Wildcat! BBS, reads new
support messages, calls the Claude API (Anthropic), and posts replies under
a dedicated agent account.  It runs as a scheduled task on NTBBS (the live
production Wildcat! server), cycling every ~20 seconds via Wait32.

Version tag: `500.2` (aligned with Platinum Xpress 500.2 release cycle).

---

## Key Paths

| Path | Purpose |
|------|---------|
| `c:\local\wcPython\wcat-agent.py` | Main source (609 lines, 500.2) |
| `c:\local\wcPython\wcat-agent.ini` | Runtime config (accounts, confs, KB, cogs) |
| `c:\local\wcPython\wcat-agent.log` | Rolling run log (appended each run) |
| `c:\local\wcPython\wcat-agent-last.log` | Last run only (overwritten each run) |
| `c:\local\wcPython\run-wcat-agent.cmd` | Launcher: sets API key, runs, waits 20s |
| `c:\local\wcPython\wcat-agent-status.cmd` | Status check: `py wcat-agent.py --status` |
| `c:\local\wcPython\kb\` | Knowledge base files (see below) |
| `c:\local\wcPython\wcPapi\` | wcPAPI Python SDK (compiled ctypes bindings) |
| `c:\local\wcPython\wcPostMsg.py` | Standalone CLI message poster utility |

**Production location (NTBBS):** `d:\local\wcpython\`

---

## GitHub Repository

`https://github.com/WinserverSupport/wcPython`

Covers both the wcPAPI SDK and wcat-agent.py.

---

## wcPAPI SDK

wcPAPI is the Wildcat! Python API -- ctypes bindings to the native WC server
DLLs.  Installed as a Python package from `c:\local\wcPython\`.

Key modules used by wcat-agent.py:

| Module | Purpose |
|--------|---------|
| `wcpapi.wcserver_h` | Core server API: Login, GetNextMessage, AddMessage, etc. |
| `wcpapi.wcserror_h` | Error code constants |
| `wcpapi.wctype_h` | Struct definitions: TMsgHeader, TUserInfo, TUser, TConfDesc |
| `wcpapi.wctype_constants_h` | Flag constants: mfMimeSaved, etc. |

Required call sequence for any wcPAPI script:
```python
WildcatServerConnectSpecific(None, server)  # connect to named WC server
WildcatServerCreateContext()                # create per-thread context
LoginUser(agent_id, password, ...)          # authenticate
# ... do work ...
WildcatServerDeleteContext()                # always clean up in finally block
```

`LookupName(account, byref(uinfo))` resolves a display name to TUserInfo
without a login context -- used to get agent_id before LoginUser.

---

## Architecture

### Message Processing Loop

For each configured conference:
1. `GetLastRead(cnum)` -- per-account server-side pointer (no local state file)
2. Seed `GetNextMessage` cursor to last-read id
3. Walk messages; skip: own posts, cog replies, threads (unless follow_threads),
   already-answered (ReplyCount > 0), private, addressed to specific user
4. **Layer 1**: keyword check against `[no_wsa]` patterns (free, no API call)
5. **Layer 2**: `ask_claude()` -- posts to Claude API; `[NO-REPLY]` token = skip
6. `post_reply()` -- `AddMessage()` + `IncrementReplyCount(original)`
7. `SetLastRead(cnum, new_last)` -- advance pointer

### MIME vs Local Messages

- MIME (internet mail via wcListServe): `mfMimeSaved` flag set; body via
  `GetText("wc:\\conf(N)\\message(id)")`, decoded as RFC822; thread parent
  found via RFC `In-Reply-To: <digits@msgid_domain>` header.
- Local BBS messages: plain cp437 body; `msg.Reference` = immediate parent Id.

### System Prompt Construction (`build_system_prompt`)

- Base identity: "technical support assistant for Wildcat! BBS platform"
- KB text prepended (base.txt + per-conference supplement)
- Cognizant engineers (cog) block appended when cogs defined for conference
- Signed with `agent_name` (per-conference From.Name from INI)
- Ends with `[NO-REPLY]` instruction for non-answerable / human-only messages

---

## Configuration (wcat-agent.ini)

```ini
[agent]
account       = WinServer Support Agent   # WC user account
password      = ...
server        = NTBBS
name          = Winserver Support Agent <...@winserver.com>
model         = claude-sonnet-4-6
max_response  = 2000                      # max chars posted as reply body
max_input     = 4000                      # max chars sent to Claude
follow_threads = yes                      # reply to follow-ups of agent posts
msgid_domain  = winserver.com             # for In-Reply-To RFC matching

[kb]
base = kb/base.txt
137  = kb/137-pxwin.txt
121  = kb/121-winserver.txt
125  = kb/125-developers.txt, kb/wcbasic-lang.txt
35   = kb/35-wcbasic.txt

[conferences]
137 = wcListServe Platinum Xpress          | Winserver Support Agent <...>
121 = winserver@winserver.com              | Winserver Support Agent <...>
125 = developers@winserver.com             | Winserver Support Agent <...>
35  = WIN Server wcBasic - Developers      | Winserver Support Agent

[no_wsa]
base = resolved, no wsa, no ai, humans only, wsa: stop, ...

[cog]
121 = Michael Purdy
125 = Michael Purdy
35  = Michael Purdy

[cog_bios]
Michael Purdy = Senior 3rd-party developer; wcWeb User Editor author; ...
```

## Knowledge Base Files

| File | Conference |
|------|-----------|
| `kb/base.txt` | All conferences (Wildcat! platform overview) |
| `kb/137-pxwin.txt` | Conf 137 -- Platinum Xpress support |
| `kb/121-winserver.txt` | Conf 121 -- WinServer general |
| `kb/125-developers.txt` | Conf 125 -- Developers |
| `kb/wcbasic-lang.txt` | Conf 125 -- wcBASIC language reference |
| `kb/35-wcbasic.txt` | Conf 35 -- local wcBASIC forum |

---

## CLI Usage

```
py wcat-agent.py [options]

--config <f>       INI file (default: wcat-agent.ini)
--conf <n>         Process only conference N
--dry-run          Placeholder reply, no post, no last-read advance
--no-post          Call Claude but do not post or advance last-read
--status           Show conference message pointers and exit
--reset            Set last-read to high for all conferences and exit
--reset-last [n]   Set last-read to high-N (leave last N unread)
--from-msg <n>     Start from message Number (no state change)
--limit <n>        Stop after N replies per conference
--verbose          Print all scanned message headers
/?                 Help (alias for --help)
```

---

## Current Status (2026-03-11)

- **LIVE on NTBBS** (`d:\local\wcpython\`) -- running as scheduled task
- Monitoring confs 137 (PX), 121 (WinServer), 125 (Developers), 35 (wcBasic)
- `IncrementReplyCount(original)` fix applied 2026-03-09 -- threading correct
- `follow_threads = yes` -- agent replies to follow-ups on its own posts
- cog deferral working -- Michael Purdy active on confs 35, 121, 125
- MIME thread-following via RFC `In-Reply-To` header parsing -- working
- Model: `claude-sonnet-4-6`

---

## Known Issues / TODOs

1. **FleaTrack AI Triage Integration** -- New feature. Poll the FleaTrack
   MySQL database for new issues (ai_status IS NULL) and post AI triage
   responses back via wcBASIC CLI scripts.

   wcBASIC side is COMPLETE and tested on MAIN4/HDEV20 (2026-05-18).
   Source: c:\local\wc10\wcFleaTrack\  GitHub: WinserverSupport/wcFleaTrack

   Three CLI scripts in wc:\code\fleatrack\ (c:\wc10beta32\fleatrack\):

     ft-ai-poll.wcx
       - SELECT issues WHERE ai_status IS NULL ORDER BY edate
       - Output: XML (sqlresult-xml.wct), CDATA-wrapped fields
       - No arguments needed

     ft-ai-claim.wcx  id={id}
       - UPDATE issues SET ai_status='processing' WHERE id=N AND ai_status IS NULL
       - Atomic race guard -- only one agent instance wins per issue

     ft-ai-writeback.wcx  id={id}&respfile=wc:\fleatrack\ai_resp_{id}.tmp[&status=done|error]
       - Reads response text from file via GetText()
       - UPDATE issues SET ai_status=done, ai_response=text WHERE id=N
       - Use status=error + error detail in file if AskClaude call fails

   Python agent loop to implement:

     ```python
     # 1. Poll
     xml = run_wcx("c:\\wc10beta32\\fleatrack\\ft-ai-poll.wcx")
     issues = parse_poll_xml(xml)   # {id, title, description, component, type, os, username}

     # 2. Process each issue
     for issue in issues:
         # Claim (atomic)
         run_wcx("c:\\wc10beta32\\fleatrack\\ft-ai-claim.wcx", f"id={issue['id']}")

         # Call AskClaude with triage system prompt
         response = ask_claude_triage(issue)

         # Write response to temp file
         resp_file = f"c:\\wc10beta32\\fleatrack\\ai_resp_{issue['id']}.tmp"
         write_file(resp_file, response)

         # Write back
         run_wcx("c:\\wc10beta32\\fleatrack\\ft-ai-writeback.wcx",
                 f"id={issue['id']}&respfile=wc:\\fleatrack\\ai_resp_{issue['id']}.tmp")
     ```

   Invoking wcx scripts from Python:
     - Use PHYSICAL path: c:\wc10beta32\fleatrack\ft-ai-claim.wcx
     - NOT wc:\ path -- wc:\ path goes interactive with wcrun.exe
     - Working directory must be c:\wc10beta32
     - Pattern: subprocess with wcrun.exe -r "physical_path" "nv_args"

   System prompt for triage mode (suggested):
     "You are a Wildcat! platform technical support triage agent. Analyze
      the submitted bug report and provide: (1) acknowledgement, (2) likely
      root cause, (3) suggested fix or workaround, (4) priority assessment.
      Be concise. Sign as 'AI Triage Agent'."

   Polling schedule: add to existing wcat-agent run cycle or run as a
   separate scheduled task. No schema changes needed -- MySQL is on HDEV20
   only (shared by MAIN4 + NTBBS). alter-add-ai-columns.sql already run
   2026-05-18.

2. **SMTP Ticket Filter (smtpfilter-ticket.wcc)** -- New feature. Monitor
   incoming email at the SMTP DATA state for sales-related, paid Platinum
   Support, or ETS (Electronic Technical Support) messages and auto-create
   Support or Sales tickets. Implemented as a wcBASIC SMTPFILTER hook
   deployed as `smtpfilter-ticket.wcc` (standalone .wcx, does not modify
   stock WC sources per PX plug-and-play rule). Hook fires at SMTP DATA
   state via wcsmtp\ filter chain. See `c:\local\wc10\wcbasic\` for
   SMTPFILTER hook pattern and `smtpfilter-*.wcc` examples.

   To notify the active "WSA Wildcat! Support Agent" CC session about this
   task, either:
   a) Switch to that terminal and type the request directly, or
   b) Resume the last session from the project directory:
         cd c:\local\claude\wcat-agents
         claude --resume
      then describe the smtpfilter-ticket.wcc task at the prompt.
   The CLAUDE.md TODO entry above will orient the resumed session.

2. **KB content staleness** -- KB files are static text; no mechanism to
   auto-refresh from live WC docs or GitHub.  Manual update required.
2. **No reply to agent follow-ups from non-agent originals** -- if a human
   posts a follow-up to a thread the agent didn't start, `follow_threads`
   does not cause the agent to re-engage. By design (avoid spam) but may
   miss legitimate question chains.
3. **ANTHROPIC_API_KEY** must be set before running (`set-cc-api-key.cmd`
   on NTBBS reads it from a local file; not committed to git).
4. **Single-login per run** -- agent logs in once per invocation. Long runs
   (many conferences, many messages) could hit WC session timeouts.
   Current scheduled task cycle (20s via Wait32) keeps runs short.
5. **No retry on transient API errors** -- if Claude API fails mid-conference,
   last-read is advanced to just before the failing message and the run stops.
   Next scheduled run will retry from that point.
6. **cp437 encoding** -- all WC BBS message bodies decoded as cp437.  High-byte
   characters in user messages may render as replacement chars in Claude input.
7. **`/?' alias** for `--help` -- works via sys.argv rewrite; only catches bare
   `/?`, not `/? extra args`.

---

## Related Projects

- **BinkP / pxonline context**: `c:\local\claude\wcBinkP\` -- see CLAUDE.md
  there for the Platinum Xpress 500.2 BinkP mailer and pxonline.exe work.
  KB file `kb/137-pxwin.txt` should be kept in sync with BinkP feature changes.
- **wcPostMsg.py**: standalone CLI message poster at `c:\local\wcPython\wcPostMsg.py`
  -- shares wcPAPI connection/login patterns; useful reference for new scripts.
- **wcPAPI SDK source**: `c:\local\wcPython\wcPapi\` -- Python ctypes bindings
  built from WC SDK headers.  Rebuild: `wcpapi-make.cmd`.

---

## Restart Instructions

Start Claude Code from the local path (UNC paths break cmd.exe on MAIN3/MAIN4):

```
cd c:\local\claude\wcat-agents
claude
```

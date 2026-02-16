# peon-ping

Audio alerts for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) using Warcraft II peon voice lines. Plays sounds when Claude finishes work, needs permission, or is idle — so you never forget about a waiting session.

## Install

```bash
claude plugin marketplace add DanSoQt/peon-ping
claude plugin install peon-ping@peon-ping
```

Requires Python 3 and an audio player:
- **macOS** — `afplay` (built-in)
- **Windows** — `ffplay` ([FFmpeg](https://ffmpeg.org/download.html)) or falls back to `winsound`
- **Linux** — `paplay`, `pw-play`, `aplay`, or `ffplay`

## What it does

| Hook event | Sound category | Meaning |
|---|---|---|
| `SessionStart` | session.start | "Ready to work" |
| `UserPromptSubmit` | task.acknowledge | "Yes" / "Okey dokey" / ... |
| `Stop` | task.complete | "Job's done" / "Something need doing?" |
| `Notification` (permission) | input.required | "What?" / "Hmm?" |
| `Notification` (idle) | task.complete | "Job's done" |
| Rapid prompts | user.spam | "Stop poking me!" |

Also sets the terminal tab title and shows desktop notifications when the terminal is not focused.

## Commands

- `/peon-ping-toggle` — pause or resume sounds
- `/peon-status` — show current pack, volume, and pause state

## Configuration

User config lives at `~/.claude/peon-ping/config.json` (seeded from `config.default.json` on first run):

```json
{
  "active_pack": "peon",
  "volume": 0.5,
  "enabled": true,
  "desktop_notifications": true,
  "categories": {
    "session.start": true,
    "task.complete": true,
    "input.required": true,
    "user.spam": true
  },
  "annoyed_threshold": 3,
  "annoyed_window_seconds": 10
}
```

## Legal

Warcraft II audio samples are property of Blizzard Entertainment and are included for non-commercial fan-content purposes only. They are **not** covered by this project's MIT license. See [NOTICE](NOTICE) for the full copyright statement.

## License

MIT — applies to source code only. See [LICENSE](LICENSE).

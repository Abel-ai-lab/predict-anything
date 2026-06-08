# Installing trade-anything for Claude Code

Enable Abel strategy discovery workflows in Claude Code via skill symlinks.

Ask user to choose one install scope:

- Global: available in every Claude Code session on this machine
- Project-level: available only inside the current repo via `.claude/skills/`

## Prerequisites

- Git
- Claude Code with skills enabled

## Global Install

1. Clone the repository:

```bash
git clone https://github.com/Abel-ai-causality/trade-anything.git ~/.claude/trade-anything
```

2. Register the Abel strategy research skills in Claude's personal skills directory:

```bash
mkdir -p ~/.claude/skills
ln -s ~/.claude/trade-anything/skills/abel ~/.claude/skills/abel
ln -s ~/.claude/trade-anything/skills/abel-ask ~/.claude/skills/abel-ask
ln -s ~/.claude/trade-anything/skills/abel-auth ~/.claude/skills/abel-auth
ln -s ~/.claude/trade-anything/skills/abel-invest ~/.claude/skills/abel-invest
```

3. Optional before restart: persist Abel auth now if you already have a key.

Canonical shared auth file:

```text
~/.claude/skills/abel-auth/.env.skill
```

Example:

```dotenv
ABEL_API_KEY=abel_xxx
```

## Project-Level Install

Run these commands from the project root:

```bash
mkdir -p .claude
git clone https://github.com/Abel-ai-causality/trade-anything.git .claude/trade-anything
mkdir -p .claude/skills
ln -s ../trade-anything/skills/abel .claude/skills/abel
ln -s ../trade-anything/skills/abel-ask .claude/skills/abel-ask
ln -s ../trade-anything/skills/abel-auth .claude/skills/abel-auth
ln -s ../trade-anything/skills/abel-invest .claude/skills/abel-invest
```

Optional project-local auth file:

```text
.claude/skills/abel-auth/.env.skill
```

## Existing Installs

Existing installs under `~/.claude/abel-skills` or `.claude/abel-skills` can keep their local folder name. To migrate, update the git remote:

```bash
cd ~/.claude/abel-skills
git remote set-url origin https://github.com/Abel-ai-causality/trade-anything.git
```

## After Either Install

Important: after installation, prompt the user to restart opencode or open a new session and tell them that they can try following queries with Abel (show the full list!):

- "Abel, find a strategy for AMZN."
- "Abel, research strategies for META."
- "Can Abel look for an ORCL strategy?"
- "Abel, help me search for a tradable TSLA strategy."
- "Which companies benefit from AI datacenter expansion?"

# Pi Skills Repository

This repository contains custom skills for [pi-coding-agent](https://github.com/earendil-works/pi-coding-agent).

## Skills

### unattended-dev-system

A complete unattended development system that enables AI agents to work autonomously on long-term software engineering tasks with automatic recovery, progress tracking, and resource management.

**Version**: v1.1.0

**Features**:
- ✅ Environment validation (git, python3, curl, pi CLI)
- ✅ Security checks (path validation, command injection prevention)
- ✅ Cross-platform support (Linux/macOS/Windows)
- ✅ Improved error handling (trap, tracing)
- ✅ Complete documentation (QUICKSTART, ADRs, glossary, architecture)
- ✅ Test suite (11 tests, all passing)

**Installation**:
```bash
# In your project directory
/unattended-dev-system

# Or directly
bash ~/.pi/agent/skills/unattended-dev-system/install.sh
```

**Documentation**:
- [README.md](unattended-dev-system/README.md) - Complete usage guide
- [SKILL.md](unattended-dev-system/SKILL.md) - Skill specification
- [QUICKSTART.md](unattended-dev-system/docs/QUICKSTART.md) - Quick start guide
- [ARCHITECTURE.md](unattended-dev-system/docs/ARCHITECTURE.md) - System architecture
- [ADR](unattended-dev-system/docs/adr/) - Architecture Decision Records
- [GLOSSARY.md](unattended-dev-system/docs/glossary.md) - Term definitions
- [CODE_REVIEW_FINDINGS.md](unattended-dev-system/docs/CODE_REVIEW_FINDINGS.md) - Code review results

**Based on**: AI-FanYi v7 (commit ed81d91)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/stflj2022/skill-j.git
cd skill-j
```

2. Copy skills to pi skills directory:
```bash
cp -r unattended-dev-system ~/.pi/agent/skills/
```

3. Make scripts executable:
```bash
chmod +x ~/.pi/agent/skills/unattended-dev-system/*.sh
```

## Usage

### Using unattended-dev-system

```bash
# In your project directory
cd /path/to/your/project
/unattended-dev-system
```

The skill will:
1. Detect your project type and configuration
2. Generate configuration files
3. Set up the driver, watchdog, and orchestrator
4. Configure AI providers
5. Validate the installation

### matt-pocock-skills (Git Submodule)

Official Matt Pocock engineering/productivity skills, referenced as a **git submodule** pointing at the upstream repo:

- **Upstream**: https://github.com/mattpocock/skills
- **Categories**: engineering/ (18), productivity/ (7), in-progress/ (6), misc/ (4)

**First-time setup**:
```bash
git submodule update --init --recursive
cd matt-pocock-skills
# then run in each project: /setup-matt-pocock-skills
```

**Auto-update to latest** (in skill-j root):
```bash
bash scripts/update-matt-skills.sh
# or manually:
git submodule update --remote matt-pocock-skills
```

See [docs/MATT_SKILLS_UPDATE.md](docs/MATT_SKILLS_UPDATE.md) for full details.

## Contributing

Feel free to submit issues and pull requests!

## License

This repository follows the license of pi-coding-agent.

## Credits

- Based on pi-coding-agent by earendil-works
- unattended-dev-system based on AI-FanYi project

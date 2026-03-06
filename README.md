# 🌈 Bifrost 2.0

**Multi-AI Collaborative Coding System for Termux**

Bifrost is an intelligent orchestration system that harnesses the power of multiple AI models (Claude, Gemini, GPT-4) 
working together as a "brain council" via **Monica.im multi-chat**, achieving consensus on the best solutions, 
and then having **GitHub Copilot CLI** implement them as the "worker."

---

## 📚 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Modes](#usage-modes)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [API & Data Flow](#api--data-flow)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## 📖 Overview

### The Problem
Traditional AI-assisted coding suffers from:
- **Single model bias** — One AI perspective may miss edge cases
- **No iteration** — No debate or refinement between perspectives
- **Manual implementation** — Requires human to build, test, and debug

### The Solution: Bifrost

Bifrost creates a **three-layer architecture**:

1. **🧠 Brain Council** (Monica.im Multi-Chat)
   - **Claude 4.5 Sonnet** — Architect role (clean, maintainable code)
   - **Gemini 3 Flash** — Creative role (innovative, optimized solutions)
   - **GPT-4o** — Critic role (edge cases, security, bugs)
   - All three debate in parallel, review each other, and reach consensus

2. **⚙️ Orchestrator**
   - Manages the debate workflow (multiple rounds)
   - Evaluates solutions using consensus scoring
   - Detects when tests fail and triggers fixes
   - Handles both **Coding** and **Security Simulation** modes

3. **🏗️ Worker** (GitHub Copilot CLI)
   - **MailboxWorker**: Communicates via JSON task queue (`queue/pending/` → `queue/results/`)
   - **InstructionWorker**: Generates detailed instructions for manual Copilot execution

### Key Features

✅ **Parallel Debate** — Three AI models discuss simultaneously (Monica.im multi-chat, 1 page, 3 panels)  
✅ **Consensus Algorithm** — Weighted scoring on code quality, innovation, and security  
✅ **Automated Testing** — Run tests, collect results, feed back to brain for fixes  
✅ **Security Simulation** — Red/Blue/Purple team exercise (attacker vs defender)  
✅ **Termux-Optimized** — Native Chromium binary, no glibc overhead  
✅ **Extensible** — Pluggable worker modes, configurable AI models  

## 🆕 Novinky

- 2026-03-06: Aktualizována dokumentace a přidána sekce "Novinky" se stručným přehledem změn a vylepšení.
- Hlavní body: aktualizovaný přehled architektury, zpřesněné instrukce pro MAILBOX worker a poznámky k bezpečnostnímu režimu.


---

## 🏗️ Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Input: Task                                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: BRAIN DEBATE (Monica.im Multi-Chat)               │
│                                                              │
│  Round 1: Independent Proposals                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Claude      │  │ Gemini      │  │ GPT-4o      │         │
│  │ Architect   │  │ Creative    │  │ Critic      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         ↓                ↓                 ↓                 │
│  Rounds 2+: Cross-Review & Refinement                      │
│         ↓                ↓                 ↓                 │
│  ┌──────────────────────────────────────────────┐          │
│  │ CONSENSUS (scored & weighted)                │          │
│  └──────────────────────────────────────────────┘          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: WORKER BUILD (GitHub Copilot CLI)                 │
│                                                              │
│  MailboxWorker:                                             │
│  1. Write task → queue/pending/task_001.json               │
│  2. Wait for Copilot to execute (CLI or copilot_executor) │
│  3. Read results ← queue/results/task_001.json              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: TESTING & FEEDBACK LOOP                           │
│                                                              │
│  Run tests → Collect results → Feed to brain              │
│  If FAIL: Trigger brain to FIX (max 5 iterations)         │
│  If PASS: Success!                                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Final Report   │
        │ (output/ dir)  │
        └────────────────┘
```

### Data Flow (Protocol)

All inter-component communication uses **BifrostMessage** (dataclass):
- `phase` — Workflow stage (BRAIN_ROUND, WORKER_BUILD, WORKER_TEST, etc.)
- `status` — SUCCESS, ERROR, PARTIAL, PENDING
- `source` — "claude", "gemini", "gpt-4o", "copilot", etc.
- `content` — Main payload (code, report, instructions)
- `test_results` — List of TestResult objects
- `files_created` / `files_modified` — Artifact tracking
- `metadata` — Extra info (model params, timing, etc.)

Messages are **JSON-serialized** and stored in `output/` for audit trails.

---

## 🚀 Installation

### Prerequisites

- **Python 3.11+**
- **Termux** (or Linux/macOS with Playwright support)
- **Monica.im account** (free tier sufficient)
- **GitHub Copilot CLI** (optional, for MailboxWorker)

### Step 1: Clone the Repository

```bash
git clone https://github.com/zombiegirlcz/Bifrost-multi-AI.git
cd Bifrost-multi-AI/bifrost_core
```

### Step 2: Set Up Cookies

1. **Export Monica.im cookies from your browser:**
   - Open [monica.im](https://monica.im)
   - Use browser extension **Cookie Editor** (or DevTools)
   - Export cookies as JSON
   - Save to `cookies/monica_cookies.json`

   For detailed instructions, see [`cookies/README.md`](bifrost_core/cookies/README.md)

2. **Verify cookie format:**
   ```bash
   python clean_cookies.py
   ```
   This validates and cleans up cookie structure.

### Step 3: Install Dependencies

```bash
chmod +x setup.sh
./setup.sh
```

Or manually:
```bash
pip install -r requirements.txt --upgrade
```

### Step 4: Verify Installation

```bash
python -m main --help
```

You should see the CLI help with all options.

---

## 📖 Quick Start

### Example 1: Simple Coding Task

```bash
python -m main --task "Vytvoř REST API pro správu úkolů s FastAPI"
```

**What happens:**
1. Brain Council (3 models on Monica.im) debates the design for 3 rounds
2. Orchestrator extracts consensus code
3. Mailbox Worker writes task to `queue/pending/task_001.json`
4. GitHub Copilot CLI (or `copilot_executor.py`) implements it
5. Tests run automatically
6. If tests fail, brain fixes the code (up to 5 iterations)
7. Final report saved to `output/<timestamp>_<task_name>/`

### Example 2: Security Simulation

```bash
python -m main --task "Simuluj SQL injection útok a obranné mechanismy" --mode security
```

**What happens:**
1. **Red Team** (Claude) — Proposes exploit code
2. **Blue Team** (Gemini) — Proposes defensive code
3. **Purple Team** (GPT) — Critiques both, looks for flaws
4. Rounds of cross-review and improvement
5. Consensus extracted (both attack + defense code)
6. Copilot implements and tests both
7. Security report generated

### Example 3: Instructions Mode (No Auto-Build)

```bash
python -m main --task "Vytvoř autentizační systém" --worker instructions
```

**What happens:**
1. Brain debates as normal
2. Instead of calling Copilot, orchestrator generates **detailed instructions**
3. Saves to `instructions_for_copilot.txt`
4. **Status = PARTIAL** (you must manually execute)
5. Great for review/audit before building

---

## 🎛️ Usage Modes

### Modes

#### `--mode coding` (default)
Typical development task: design, build, test, iterate.

#### `--mode security`
Red/Blue/Purple team simulation: attack vs defense scenarios.

### Workers

#### `--worker mailbox` (default)
**Recommended.** Uses file-based queue:
1. Orchestrator writes tasks to `queue/pending/`
2. You run `copilot_executor` or GitHub Copilot manually
3. Copilot writes results to `queue/results/`
4. Orchestrator reads and continues

```bash
# Terminal 1: Start brain debate + write task queue
python -m main --task "..." --worker mailbox

# Terminal 2: Run the worker (monitors queue, executes tasks)
python copilot_executor --watch
# OR manually with GitHub Copilot CLI
```

#### `--worker instructions`
Generates instructions for manual Copilot execution. Useful for:
- Review before building
- Compliance audits
- Detailed documentation

```bash
python -m main --task "..." --worker instructions
# Output: instructions_for_copilot.txt
```

### Other Options

```bash
python -m main \
  --task "Your task here" \
  --mode coding|security \
  --worker mailbox|instructions \
  --rounds 3 \              # Number of debate rounds (default: 3)
  --max-fix 5 \             # Max fix iterations if tests fail (default: 5)
  --verbose                 # Detailed logging
```

---

## 📂 Project Structure

```
bifrost_core/
├── main.py                      # CLI entrypoint (Click)
├── orchestrator.py              # Main workflow orchestrator
├── security_orchestrator.py     # Red/Blue/Purple mode
├── brain.py                     # BrainCouncil: debater logic
├── security_brain.py            # Security-specific brain
├── worker.py                    # Base Worker class
├── worker_mailbox.py            # File-queue worker (Copilot CLI)
├── instruction_worker.py        # Instruction generator
├── session_manager.py           # Monica.im Playwright automation
├── feedback_loop.py             # Test runner & feedback
├── protocol.py                  # Data models (BifrostMessage, Phase, Status)
├── config.py                    # Configuration & constants
├── copilot_executor.py          # CLI tool for executing queued tasks
├── auto_executor.py             # Autonomous execution loop
├── clean_cookies.py             # Cookie validation & cleanup
├── utils/
│   ├── logger.py               # Logging utilities
│   ├── file_manager.py         # Output directory management
│   ├── human_behavior.py       # Playwright delays & randomization
│   ├── diff_viewer.py          # Code diff analysis
│   └── rate_limiter.py         # Request throttling
├── templates/
│   ├── brain_round1.txt        # Round 1 prompt
│   ├── brain_review.txt        # Rounds 2+ prompt
│   ├── brain_consensus.txt     # Consensus extraction
│   ├── brain_security_*.txt    # Security mode prompts
│   ├── worker_build.txt        # Build instructions
│   └── worker_fix.txt          # Fix instructions
├── cookies/
│   ├── monica_cookies.json     # Monica.im auth (REQUIRED)
│   └── README.md               # Cookie export guide
├── queue/
│   ├── pending/                # Tasks waiting for Copilot
│   └── results/                # Task results from Copilot
├── output/                      # Project outputs & reports
├── tests/
│   ├── test_orchestrator.py
│   ├── test_mailbox.py
│   ├── test_protocol.py
│   ├── test_session.py
│   └── test_security.py
├── requirements.txt             # Dependencies
├── setup.sh                     # Installation script
└── README.md                    # This file
```

---

## ⚙️ Configuration

### Key Settings (`config.py`)

```python
# Monica.im multi-chat
MONICA_URL = "https://monica.im/cs/products/ai-chat"
MONICA_COOKIES = Path("cookies/monica_cookies.json")

# The three brains (customizable)
MONICA_PANELS = {
    "claude": {
        "role": "architekt",
        "model_label": "Claude 4.5 Sonnet",
        "panel_index": 0,
    },
    "gemini": {
        "role": "kreativní",
        "model_label": "Gemini 3 Flash",
        "panel_index": 1,
    },
    "gpt": {
        "role": "kritik",
        "model_label": "GPT-4o",
        "panel_index": 2,
    },
}

# Workflow
BRAIN_ROUNDS = 3              # Debate rounds
MAX_FIX_ITERATIONS = 5        # Max fix attempts
CONSENSUS_THRESHOLD = 0.7     # Scoring threshold
RESPONSE_MAX_WAIT = 360       # Timeout (seconds)

# Worker mode
WORKER_MODE = "mailbox"       # or "instructions"
SECURITY_MODE = False         # or True for Red/Blue/Purple
```

---

## 🔌 API & Data Flow

### BifrostMessage Protocol

```python
@dataclass
class BifrostMessage:
    phase: Phase                    # BRAIN_ROUND, WORKER_BUILD, etc.
    status: Status                  # SUCCESS, ERROR, PARTIAL, PENDING
    source: str                     # "claude", "gemini", "gpt-4o", "copilot"
    content: str                    # Main payload
    timestamp: str                  # ISO timestamp
    round_number: int               # Debate round (0 for worker)
    iteration: int                  # Fix iteration
    files_created: list[str]        # New files written
    files_modified: list[str]       # Changed files
    test_results: list[TestResult]  # Test outcomes
    metadata: dict                  # Extra info (model params, timing)
```

### Typical Workflow

```python
# 1. User task
msg = BifrostMessage(
    phase=Phase.TASK_INPUT,
    status=Status.PENDING,
    source="user",
    content="Create REST API"
)

# 2. Brain proposals (Round 1, independent)
msg = BifrostMessage(
    phase=Phase.BRAIN_ROUND,
    status=Status.SUCCESS,
    source="claude",
    content="<code>",
    round_number=1,
)

# 3. Consensus
msg = BifrostMessage(
    phase=Phase.BRAIN_CONSENSUS,
    status=Status.SUCCESS,
    source="orchestrator",
    content="<consensus code>",
    metadata={"score": 8.5}
)

# 4. Worker build
msg = BifrostMessage(
    phase=Phase.WORKER_BUILD,
    status=Status.SUCCESS,
    source="copilot",
    content="<build report>",
    files_created=["main.py", "requirements.txt"],
)

# 5. Tests
msg = BifrostMessage(
    phase=Phase.WORKER_TEST,
    status=Status.SUCCESS,
    source="orchestrator",
    test_results=[
        TestResult(test_name="test_api", passed=True),
        TestResult(test_name="test_db", passed=False, error_message="..."),
    ]
)
```

### File Outputs

All projects saved to `output/<timestamp>_<task_name>/`:

```
output/20260305_124114_postav_agenta/
├── BIFROST_REPORT.md              # Executive summary
├── instructions_for_copilot.txt   # (if --worker instructions)
├── iterations/
│   ├── iter_000/
│   │   ├── consensus.json         # Brain consensus
│   │   ├── build.json             # Worker build results
│   │   └── test.json              # Test results
│   ├── iter_001/                  # (if fixes applied)
│   │   ├── fix.json               # Fixup proposal
│   │   └── test.json
│   └── ...
├── code/
│   ├── main.py
│   ├── api/
│   └── ...
└── requirements.txt
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_mailbox.py::test_mailbox_worker_import -v
```

### Test Coverage

```bash
pytest tests/ --cov=. --cov-report=html
```

Tests cover:
- ✅ Protocol data models
- ✅ Mailbox queue mechanics
- ✅ Orchestrator initialization
- ✅ Session management (Monica.im)
- ✅ Security mode workflows

---

## 🐛 Troubleshooting

### Issue: "Monica.im cookies invalid"

**Solution:**
1. Ensure cookies are fresh (< 30 days)
2. Export again using **Cookie Editor** browser extension
3. Verify JSON format:
   ```bash
   python clean_cookies.py
   ```
4. Check `cookies/README.md` for detailed export steps

### Issue: "Playwright timeout"

**Solution:**
- Increase `RESPONSE_MAX_WAIT` in `config.py` (default: 360s)
- Check Monica.im load time (may be slow for complex prompts)
- Reduce `BRAIN_ROUNDS` to speed up

### Issue: "Task queue never completes"

**Solution:**
- Verify Copilot CLI is running: `python copilot_executor --watch`
- Check `queue/pending/` and `queue/results/` directories
- Look at task JSON files to verify format
- Manually place result in `queue/results/` if needed

### Issue: "Tests not recognized"

**Solution:**
- Edit `parse_test_output()` in `worker_mailbox.py` to match your test framework
- Ensure test output includes clear PASS/FAIL markers
- For custom formats, extend regex patterns

### Issue: "Out of memory (Termux)"

**Solution:**
- Reduce `BRAIN_ROUNDS` (default: 3 → try 2)
- Reduce `MAX_FIX_ITERATIONS` (default: 5 → try 2)
- Use `--worker instructions` mode (less intensive)
- Ensure browser is closed between runs

---

## 🚀 Advanced Usage

### Custom Brain Models

Edit `MONICA_PANELS` in `config.py`:

```python
MONICA_PANELS = {
    "custom": {
        "role": "domain expert",
        "model_label": "Your Model Name",
        "panel_index": 0,  # Which panel on Monica UI
    },
}
```

### Custom Prompts

Edit `templates/brain_*.txt`:

```
System: {system_prefix}

Task: {task}

Context: {previous_solutions}

Please propose your solution:
```

Variables: `{task}`, `{system_prefix}`, `{previous_solutions}`, `{round_number}`

### Extend Test Parsing

In `worker_mailbox.py`, update `parse_test_output()`:

```python
def parse_test_output(self, output: str) -> list[TestResult]:
    # Your regex here
    pattern = r"TEST:\s+(\w+)\s+(PASSED|FAILED)"
    # Parse and return list[TestResult]
```

---

## 📄 License

MIT — See LICENSE file

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit with clear messages
4. Submit a pull request

---

## 📞 Support

- **Documentation:** See [`bifrost_core/README.md`](bifrost_core/README.md)
- **Issues:** Open a GitHub issue
- **Discussions:** Use GitHub Discussions

---

**Built with ❤️ for Termux and collaborative AI**

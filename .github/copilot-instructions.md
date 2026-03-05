# Copilot Instructions for Bifrost 2.0

Bifrost 2.0 is a **Multi-AI Collaborative Coding System** for Termux. It orchestrates multiple AI models (via Monica.im multi-chat) as a "brain council" that debates and proposes code, while GitHub Copilot CLI acts as the "worker" that builds, tests, and refines the code.

## Quick Start

```bash
# Run the main orchestrator (brains debate via Monica.im)
python main.py --task "Vytvoř REST API pro správu úkolů"

# With options
python main.py --task "Snake game" --rounds 5 --max-fix 10 --worker mailbox --mode coding

# Run Copilot executor (worker processes tasks from queue)
python copilot_executor.py

# Watch for new tasks continuously
python copilot_executor.py --watch
```

## High-Level Architecture

### The Three Phases

1. **Phase 1: Brain Debate** (`BrainCouncil` → Monica.im)
   - Three AI models (Claude Architect, Gemini Creative, GPT Critic) propose solutions in parallel
   - Multiple debate rounds where models review and refine each other's code
   - Consensus algorithm selects the best solution

2. **Phase 2: Worker Build** (`MailboxWorker` or `PlaywrightWorker`)
   - Copilot takes consensus code and implements it
   - Files are created in `output/<project>/`
   - Tasks are written to `queue/pending/` for Copilot to pick up

3. **Phase 3: Worker Test** (`FeedbackLoop`)
   - Runs tests against built code
   - If failures, loops back to brain for fixes (max `MAX_FIX_ITERATIONS`)

### Dual Worker Modes

- **Mailbox Mode** (default, recommended): Copilot CLI reads from `queue/pending/` JSON, user manually runs Copilot and tells it to execute
- **Playwright Mode** (legacy): Automated web automation simulating Copilot's web chat interface

### Data Flow

```
main.py
  └─ Orchestrator.run(task)
      ├─ BrainCouncil.run_debate(task)
      │   └─ MonicaMultiSession (Playwright automation of Monica.im)
      │       └─ Saves consensus to output/<project>/iteration_0_consensus.json
      │
      ├─ MailboxWorker.build(consensus)
      │   └─ Writes to queue/pending/task_*.json
      │   └─ copilot_executor.py picks it up
      │   └─ User runs CLI Copilot, provides output to queue/results/
      │
      └─ FeedbackLoop.evaluate(test_results)
          └─ If failed: BrainCouncil.fix() → loop back
```

## Directory Structure

```
bifrost_core/               # (Legacy, largely unused now)
brain.py                    # BrainCouncil class
config.py                   # Monica selectors, API endpoints, credentials
copilot_executor.py         # CLI tool for managing task queue
main.py                     # CLI entry point (uses Click)
orchestrator.py             # Main Orchestrator class
protocol.py                 # Data models (BifrostMessage, Phase, Status, TestResult)
session_manager.py          # MonicaMultiSession (Playwright browser automation)
worker.py                   # Base Worker class
worker_mailbox.py           # MailboxWorker (reads queue, writes results)
requirements.txt            # Dependencies: playwright, click, rich, aiofiles
templates/                  # Prompt templates for brain phases
tests/                      # Unit tests (pytest)
queue/
  ├─ pending/               # Tasks waiting for Copilot
  └─ results/               # Task results from Copilot
output/                     # Project outputs (iterations, reports)
```

## Key Modules & Classes

### `config.py`
- **MONICA_URL**, **MONICA_COOKIES**: Web automation setup for Monica.im
- **MONICA_PANELS**: Defines 3 brain models and their panel indices
- **MONICA_SELECTORS**: CSS selectors for page elements (HTML structure of Monica.im)
- **WORKER_MODE**: "mailbox" or "playwright"
- **BRAIN_ROUNDS**, **MAX_FIX_ITERATIONS**: Tuning parameters

### `protocol.py` (Data Models)
- **BifrostMessage**: Core message type with `content`, `metadata`, `phase`, `status`
- **Phase**: enum (INITIAL, REVIEW, CONSENSUS, BUILD, TEST, REPORT)
- **Status**: enum (PENDING, IN_PROGRESS, SUCCESS, FAILURE)
- **TestResult**: Individual test outcome
- **BuildResult**: File creation metadata

### `session_manager.py` (MonicaMultiSession)
- Manages a single Playwright browser context with Monica.im
- Loads cookies, handles authentication
- Implements parallel panel interaction (send message to each of 3 panels separately)
- Uses `HumanBehavior` class for human-like interaction (delays, scrolls, random jitter)

### `brain.py` (BrainCouncil)
- **run_debate(task)**: Multi-round consensus-building
- **_round_independent()**: Each brain proposes code independently (round 1)
- **_round_review()**: Each brain reviews others' code and improves (rounds 2+)
- **Consensus algorithm**: Weighted scoring on code quality, innovation, security

### `worker_mailbox.py` (MailboxWorker)
- **build()**: Writes consensus to JSON task files in `queue/pending/`
- **test()**: Runs Python/JavaScript tests, parses output
- **parse_test_output()**: Regex-based test result extraction

### `copilot_executor.py` (CLI for workers)
- **list_pending()**: Show queued tasks
- **show_task(task_id)**: Display task details
- **write_result(task_id, files)**: Save Copilot's output to queue/results/

## Code Conventions

### Logging
- Use `utils.logger` functions: `log_phase()`, `log_banner()`, `log_code()`, `log_error()`
- **log_phase(phase, component, message)**: phase is one of: "worker_build", "worker_test", "brain_round", "complete", etc.
- Example: `log_phase("worker_build", "orchestrator", "Building project...")`

### Async/Await
- All I/O-bound operations use async/await
- Main entry point is `async def run_bifrost()`
- Use `asyncio.run()` to run async functions from sync CLI

### File I/O
- **FileManager** class in utils handles project directory structure
- All outputs go to `output/<project_name>/` with iteration tracking
- Save state as JSON files in `iteration_<N>_<phase>.json` format

### Message Protocol
- All inter-component communication uses **BifrostMessage** dataclass
- `content`: the actual code/text
- `metadata`: rich info (model name, debate round, test results, etc.)
- `phase` and `status` track workflow state

### Error Handling
- Use `try/except` blocks with `log_error()` for visibility
- `FeedbackLoop` catches test failures and triggers brain re-runs
- Max iterations configured to prevent infinite loops

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_mailbox.py -v

# Run a specific test
python -m pytest tests/test_mailbox.py::test_mailbox_worker_import -v
```

Tests use **pytest**. Key test files:
- `test_mailbox.py`: MailboxWorker queue mechanics
- `test_orchestrator.py`: Orchestrator initialization
- `test_protocol.py`: Message data models
- `test_session.py`: Monica session management
- `test_security.py`: Security mode tests

## Common Development Tasks

### Adding a New Brain Model
1. Add entry to `MONICA_PANELS` in `config.py` with panel index and model label
2. Update Monica CSS selectors in `MONICA_SELECTORS` if DOM changes
3. Test with `python main.py --task "test" --rounds 1`

### Fixing Test Parsing
- Modify `parse_test_output()` in `worker_mailbox.py`
- Update regex patterns to match your test framework's output
- Test with a simple project first

### Adding a New Worker Mode
1. Extend base `Worker` class from `worker.py`
2. Implement `build()`, `test()`, `report()` methods
3. Update `WORKER_MODE` choice in `main.py`
4. Register in `orchestrator.py`'s `initialize()` method

### Security Mode
- Run with `--mode security` to enable `SecurityOrchestrator` instead of regular `Orchestrator`
- Uses specialized prompts and threat modeling in brain debate
- Output structure is the same, but consensus focuses on security vulnerabilities

## Configuration & Credentials

### Cookies
- Each AI service requires browser cookies in `cookies/` directory:
  - `monica_cookies.json` (Monica.im multi-chat, mandatory)
  - Format: JSON array exported from browser (use Cookie Editor extension)
  - See `cookies/README.md` for detailed export instructions

### Environment
- Designed for **Termux on Android** (uses `/data/data/com.termux/...` paths)
- Browser path auto-detected via `shutil.which()` or defaults to Termux's chromium-browser
- Uses native Chromium binary (avoids glibc compatibility issues)

## Performance Notes

- **Monica.im automation** is I/O-bound and uses Playwright's async API
- Brain debate typically takes 1-3 minutes per round (depends on AI response time)
- Test parsing is regex-based (fast)
- Use `RESPONSE_POLL_INTERVAL` and `RESPONSE_MAX_WAIT` to tune timeouts
- Multiple rounds exponentially increase time (e.g., 3 rounds = ~9 minutes)

## Debugging Tips

- **Enable verbose logging**: `python main.py --task "..." -v`
- **Check Monica DOM**: Use Playwright inspector `python -m playwright codegen https://monica.im/`
- **Inspect queue files**: `python copilot_executor.py --list`
- **Check output folder**: Each project creates `output/<name>/` with iteration JSON files
- **Review test results**: Look at `iteration_<N>_test.json` for detailed test output

## Gotchas

1. **Monica.im selector changes**: If the web UI updates, you'll need to update `MONICA_SELECTORS` in `config.py`
2. **Cookie expiration**: Cookies expire after ~30 days; refresh them if authentication fails
3. **Rate limiting**: Monica.im may rate-limit rapid requests; use `HumanBehavior` delays
4. **Test framework detection**: `parse_test_output()` uses regex; may fail for unusual test formats—extend regex patterns as needed
5. **Playwright browser persistence**: Browser context is shared across all 3 panels; closing it will disconnect all

## Related Files

- **README.md** (project overview)
- **setup.sh** (installation script for Termux)
- **cookies/README.md** (detailed cookie export guide)

from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "notebooklm_export"


NB1_FILES = [
    ("PROJECT.md", False),
    ("CLAUDE.md", False),
    (".claude/handoff.md", False),
    ("docs/ROADMAP.md", False),
    ("requirements.txt", False),
    (".github/workflows/test.yml", False),
    ("docs/SRS_Robot_Bi.md", True),
    ("docs/ARCHITECTURE.md", True),
    ("docs/HARDWARE.md", True),
    ("docs/PERSONA.md", True),
    ("docs/API_CONTRACT.md", True),
    ("docs/BACKLOG_Robot_Bi_v2.md", True),
]


NB2_PYTHON_FILES = [
    "src/main.py",
    "src/ai/ai_engine.py",
    "src/ai/prompts.py",
    "src/safety/safety_filter.py",
    "src/api/server.py",
    "src/api/routers/auth_router.py",
    "src/api/routers/control_router.py",
    "src/api/routers/conversation_router.py",
    "src/api/routers/streaming_router.py",
    "src/api/routers/admin_router.py",
    "src/api/routers/ops_router.py",
    "src/api/routers/webrtc_router.py",
    "src/infrastructure/database/db.py",
    "src/infrastructure/auth/auth.py",
    "src/infrastructure/tasks/task_manager.py",
    "src/infrastructure/notifications/notifier.py",
    "src/infrastructure/sessions/state.py",
    "src/infrastructure/sessions/session_namer.py",
    "src/infrastructure/logging/log_config.py",
    "src/memory/rag_manager.py",
    "src/audio/input/ear_stt.py",
    "src/audio/output/mouth_tts.py",
    "src/audio/analysis/cry_detector.py",
    "src/vision/camera_stream.py",
    "src/education/homework_classifier.py",
    "tests/run_tests.py",
]


NB3_FIXED_FILES = [
    ("frontend/parent_app/package.json", "json"),
    ("frontend/parent_app/vite.config.js", "javascript"),
    ("frontend/parent_app/index.html", "html"),
    ("frontend/parent_app/src/main.jsx", "jsx"),
    ("frontend/parent_app/src/App.jsx", "jsx"),
    ("frontend/parent_app/src/styles.css", "css"),
    ("frontend/parent_app/src/services/api.js", "javascript"),
    ("frontend/parent_app/src/data/mockData.js", "javascript"),
]


SUMMARY = [
    ("NB1_project_core.md", "Notebook 1: Project Core"),
    ("NB2_backend_api.md", "Notebook 2: Backend API"),
    ("NB3_frontend.md", "Notebook 3: Frontend Parent App"),
    ("NB4_changelog_sessions.md", "Notebook 4: Changelog & Session History"),
]


def normalize_path(path):
    return path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")


def path_exists(relative_path):
    return (ROOT / relative_path).is_file()


def read_text(relative_path):
    display_path = normalize_path(relative_path)
    full_path = ROOT / relative_path
    if not full_path.is_file():
        return f"[FILE NOT FOUND: {display_path}]\n"

    try:
        return full_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"[FILE READ ERROR: {display_path}: {exc}]\n"


def add_block(parts, relative_path, fence=None, heading=None):
    display_path = normalize_path(relative_path)
    title = heading or display_path
    content = read_text(relative_path)

    parts.append(f"## {title}\n\n")
    if fence:
        parts.append(f"```{fence}\n")
        parts.append(content)
        if not content.endswith("\n"):
            parts.append("\n")
        parts.append("```\n\n")
    else:
        parts.append(content)
        if not content.endswith("\n"):
            parts.append("\n")
        parts.append("\n")


def write_output(filename, parts):
    output_path = OUTPUT_DIR / filename
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(parts))


def count_existing(paths):
    return sum(1 for path in paths if path_exists(path))


def build_nb1():
    included_paths = [
        relative_path
        for relative_path, optional in NB1_FILES
        if not optional or path_exists(relative_path)
    ]
    print(f"Building NB1_project_core.md - {count_existing(included_paths)} files found")

    parts = ["# Robot Bi \u2014 Project Core\n\n"]
    for relative_path in included_paths:
        add_block(parts, relative_path)
    write_output("NB1_project_core.md", parts)


def build_nb2():
    included_paths = list(NB2_PYTHON_FILES)
    if path_exists("docs/API_CONTRACT.md"):
        included_paths.append("docs/API_CONTRACT.md")

    print(f"Building NB2_backend_api.md - {count_existing(included_paths)} files found")

    parts = ["# Robot Bi \u2014 Backend API\n\n"]
    for relative_path in NB2_PYTHON_FILES:
        add_block(parts, relative_path, fence="python")
    if path_exists("docs/API_CONTRACT.md"):
        add_block(parts, "docs/API_CONTRACT.md")
    write_output("NB2_backend_api.md", parts)


def sorted_glob(relative_dir, pattern):
    base_dir = ROOT / relative_dir
    if not base_dir.is_dir():
        return []
    return sorted(
        (path.relative_to(ROOT) for path in base_dir.rglob(pattern) if path.is_file()),
        key=lambda path: normalize_path(path).lower(),
    )


def first_existing(paths):
    for path in paths:
        if path_exists(path):
            return path
    return None


def build_nb3():
    component_files = sorted_glob("frontend/parent_app/src/components", "*.jsx")
    page_files = sorted_glob("frontend/parent_app/src/pages", "*.jsx")
    robot_display = "frontend/robot_display/index.html"
    design_doc = first_existing(["docs/prompt_claude_code_v2.md", "prompt_claude_code_v2.md"])

    included_paths = [path for path, _fence in NB3_FIXED_FILES]
    included_paths.extend(component_files)
    included_paths.extend(page_files)
    if path_exists(robot_display):
        included_paths.append(robot_display)
    if design_doc:
        included_paths.append(design_doc)

    print(f"Building NB3_frontend.md - {count_existing(included_paths)} files found")

    parts = ["# Robot Bi \u2014 Frontend Parent App\n\n"]
    for relative_path, fence in NB3_FIXED_FILES:
        add_block(parts, relative_path, fence=fence)
    for relative_path in component_files:
        add_block(parts, relative_path, fence="jsx")
    for relative_path in page_files:
        add_block(parts, relative_path, fence="jsx")
    if path_exists(robot_display):
        add_block(parts, robot_display, fence="html")
    if design_doc:
        add_block(parts, design_doc)
    write_output("NB3_frontend.md", parts)


def build_nb4():
    changelog_dir = ROOT / "changelog"
    changelog_files = []
    if changelog_dir.is_dir():
        changelog_files = sorted(
            (
                path.relative_to(ROOT)
                for path in changelog_dir.glob("*.md")
                if path.is_file()
            ),
            key=lambda path: path.name,
            reverse=True,
        )

    included_paths = list(changelog_files)
    included_paths.append(".claude/handoff.md")
    if path_exists("data/docs/kehoach.md"):
        included_paths.append("data/docs/kehoach.md")

    print(f"Building NB4_changelog_sessions.md - {count_existing(included_paths)} files found")

    parts = ["# Robot Bi \u2014 Changelog & Session History\n\n"]
    for relative_path in changelog_files:
        add_block(parts, relative_path, heading=Path(relative_path).name)
    add_block(parts, ".claude/handoff.md", heading="HANDOFF \u2014 Current State")
    if path_exists("data/docs/kehoach.md"):
        add_block(parts, "data/docs/kehoach.md", heading="K\u1ebf ho\u1ea1ch g\u1ed1c")
    write_output("NB4_changelog_sessions.md", parts)


def print_summary():
    print()
    print("Summary:")
    for filename, notebook_name in SUMMARY:
        print(f"- notebooklm_export/{filename} -> {notebook_name}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    build_nb1()
    build_nb2()
    build_nb3()
    build_nb4()
    print_summary()


if __name__ == "__main__":
    main()

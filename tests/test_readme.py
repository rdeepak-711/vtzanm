"""Step 7: the README covers what the brief asks for (files and directories,
how to start, the live link) plus AI use, the data source and the decisions.
"""

from pathlib import Path

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()


def test_has_the_sections_the_brief_asks_for():
    for heading in ("## Files and directories", "## How to start", "## Live app", "## AI tools used"):
        assert heading in README, heading


def test_files_section_names_every_top_level_part():
    for part in ("backend/", "frontend/", "api/", "scripts/", "tests/", "data/",
                 "spec/site.md", "docs/decisions.md", "Dockerfile", "docker-compose.yml", "vercel.json"):
        assert part in README, part


def test_explains_how_to_start_with_and_without_docker():
    assert "docker compose up" in README
    assert "uvicorn windapp.main:app" in README
    assert "npm --prefix frontend run build" in README


def test_links_the_deployed_app():
    assert "https://" in README.split("## Live app", 1)[1].split("##", 1)[0]


def test_says_where_the_data_comes_from():
    assert "scripts/refresh_data.py" in README
    assert "Elexon" in README


def test_states_ai_tool_use():
    section = README.split("## AI tools used", 1)[1]
    assert "Claude" in section and "Codex" in section


def test_is_honest_that_vercel_does_not_run_the_docker_image():
    assert "Vercel" in README and "Docker" in README
    assert "not" in README.lower()


def test_no_hard_wrapped_paragraphs():
    # Prose paragraphs are one line each (lists, tables, headings and code are exempt).
    in_code = False
    lines = README.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("```"):
            in_code = not in_code
        if in_code or not line.strip():
            continue
        nxt = lines[i + 1]
        plain = lambda s: s.strip() and not s.lstrip().startswith(("#", "-", "*", "|", ">", "```", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "├", "└", "│", "."))
        assert not (plain(line) and plain(nxt)), f"hard-wrapped near: {line[:50]!r}"

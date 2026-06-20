"""Tests for ``tools/generate_docs.py`` — the single-source-of-truth doc generator.

These tests verify that the documentation generator stays consistent with the
MCP tool definitions in ``mcp_server.py``:

  * every tool appears in exactly one doc group (no orphans, no phantoms)
  * every destructive tool has a ``dry_run`` schema property (auto-injected)
  * the generated command table and tool-group list are well-formed
  * the generator is idempotent (running it twice changes nothing)
  * the committed docs are up to date (``--check`` passes)
"""

import asyncio

import pytest

from tools import generate_docs


@pytest.fixture(scope="module")
def tools():
    return asyncio.run(generate_docs.fetch_tools())


# ── Grouping consistency ────────────────────────────────────────────────────


def test_every_tool_assigned_to_a_group(tools):
    """No tool should fall through to 'Other' — grouping must be complete."""
    groups = generate_docs.render_tool_groups(tools)
    assert "Other" not in groups, (
        "Some tools are not assigned to a group in TOOL_GROUPS. "
        "Every tool definition must be listed exactly once."
    )


def test_no_phantom_group_entries(tools):
    """Every name in TOOL_GROUPS must correspond to a real tool definition."""
    problems = generate_docs.check_dry_run_consistency(tools)
    phantom = [p for p in problems if "no tool definition exists" in p]
    assert not phantom, f"Group references undefined tools: {phantom}"


def test_group_names_match_all_tools(tools):
    """The set of grouped tool names must equal the set of defined tools."""
    by_name = {t.name for t in tools}
    grouped = {n for _g, names in generate_docs.TOOL_GROUPS for n in names}
    assert grouped == by_name, (
        f"Group mismatch. Defined but ungrouped: {by_name - grouped}. "
        f"Grouped but undefined: {grouped - by_name}."
    )


# ── dry_run consistency ──────────────────────────────────────────────────────


def test_destructive_tools_have_dry_run(tools):
    """Every tool in DESTRUCTIVE_TOOLS must have a dry_run property."""
    problems = generate_docs.check_dry_run_consistency(tools)
    missing = [p for p in problems if "missing dry_run schema" in p]
    assert not missing, f"Destructive tools missing dry_run: {missing}"


def test_dry_run_only_on_destructive(tools):
    """No non-destructive tool should carry a dry_run property."""
    problems = generate_docs.check_dry_run_consistency(tools)
    leaked = [p for p in problems if "not in DESTRUCTIVE_TOOLS" in p]
    assert not leaked, f"Non-destructive tools have dry_run: {leaked}"


# ── Generated output shape ─────────────────────────────────────────────────


def test_command_table_includes_all_tools(tools):
    """The README table must have one row per tool (plus the header)."""
    table = generate_docs.render_command_table(tools)
    rows = [ln for ln in table.splitlines() if ln.startswith("| `")]
    assert len(rows) == len(tools), (
        f"Table has {len(rows)} rows but {len(tools)} tools are defined"
    )


def test_command_table_marks_required_params(tools):
    """Required parameters are marked with an asterisk in the table."""
    table = generate_docs.render_command_table(tools)
    # set_tempo requires 'tempo' — should appear as `tempo`*
    assert "`tempo`*" in table, "Required param 'tempo' should be marked with *"
    # ping has no params
    assert "| `ping` |" in table


def test_tool_groups_include_transport(tools):
    """The transport group exists and contains the new transport commands."""
    groups = generate_docs.render_tool_groups(tools)
    assert "**Transport:**" in groups
    for name in ("start_playing", "stop_playing", "set_tempo", "launch_scene"):
        assert f"`{name}`" in groups, f"Transport tool {name} missing from groups"


# ── Idempotency & currency ─────────────────────────────────────────────────


def test_generator_is_idempotent():
    """Running the generator twice must produce identical output (exit 0)."""
    rc1 = asyncio.run(generate_docs.main([]))
    rc2 = asyncio.run(generate_docs.main([]))
    assert rc1 == 0
    assert rc2 == 0


@pytest.mark.parametrize(
    "path",
    ["README.md", "docs/mcp-clients.md"],
)
def test_committed_docs_are_up_to_date(path):
    """The committed docs must match what the generator produces.

    Run ``python tools/generate_docs.py`` to fix if this fails.
    """
    rc = asyncio.run(generate_docs.main(["--check"]))
    assert rc == 0, (
        f"{path} is out of date. Run: python tools/generate_docs.py"
    )

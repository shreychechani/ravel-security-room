"""Unit tests for ravel_adapter.ravel — command parsing, mention stripping, formatting.

Mock subprocess.run so nothing runs Ravel or git for real.
"""
import sys
from pathlib import Path

import pytest

# Make sure the adapter package is importable without installing it.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ravel_adapter.ravel import strip_mention


# ── strip_mention ────────────────────────────────────────────────────

class TestStripMention:
    def test_removes_leading_at_ravel(self):
        assert strip_mention("@ravel check app.py:search") == "check app.py:search"

    def test_case_insensitive(self):
        assert strip_mention("@Ravel check x") == "check x"
        assert strip_mention("@RAVEL help") == "help"

    def test_with_colon_after_name(self):
        assert strip_mention("@ravel: help") == "help"

    def test_with_comma_after_name(self):
        assert strip_mention("@ravel, check x:y") == "check x:y"

    def test_no_mention_returns_text(self):
        assert strip_mention("check app.py:search") == "check app.py:search"

    def test_empty_string(self):
        assert strip_mention("") == ""

    def test_only_mention(self):
        assert strip_mention("@ravel") == ""

    def test_extra_whitespace(self):
        assert strip_mention("  @ravel   check x:y  ") == "check x:y"

    def test_custom_names(self):
        assert strip_mention("@bot help", names=("bot",)) == "help"
        assert strip_mention("@ravel help", names=("bot",)) == "@ravel help"

    def test_mention_mid_text_is_kept(self):
        """A mention in the middle is not stripped — only leading ones."""
        assert strip_mention("hello @ravel check") == "hello @ravel check"


# ── normalize_target ─────────────────────────────────────────────────

from ravel_adapter.ravel import normalize_target, RavelError


class TestNormalizeTarget:
    def test_basic(self):
        assert normalize_target("app.py:search") == ("app.py", "search")

    def test_strips_demo_app_prefix(self):
        assert normalize_target("demo-app/app.py:search") == ("app.py", "search")

    def test_strips_dot_slash(self):
        assert normalize_target("./app.py:search") == ("app.py", "search")

    def test_strips_trailing_parens(self):
        assert normalize_target("app.py:search()") == ("app.py", "search")

    def test_whitespace_is_stripped(self):
        assert normalize_target("  app.py : search  ") == ("app.py", "search")

    def test_nested_path(self):
        assert normalize_target("vendor/old_parser.py:parse") == ("vendor/old_parser.py", "parse")

    def test_no_colon_raises(self):
        with pytest.raises(RavelError, match="use <file>:<function>"):
            normalize_target("app.py")


# ── route parsing helpers ────────────────────────────────────────────

import ast
from ravel_adapter.ravel import _route_of, routes_in


class TestRouteParsing:
    def test_route_of_default_get(self):
        node = ast.parse('@app.route("/search")\ndef fn(): pass').body[0].decorator_list[0]
        assert _route_of(node) == "GET /search"

    def test_route_of_explicit_post(self):
        node = ast.parse('@app.route("/items", methods=["POST"])\ndef fn(): pass').body[0].decorator_list[0]
        assert _route_of(node) == "POST /items"

    def test_route_of_multiple_methods(self):
        node = ast.parse('@app.route("/items", methods=["GET", "POST"])\ndef fn(): pass').body[0].decorator_list[0]
        assert _route_of(node) == "GET/POST /items"

    def test_route_of_shorthand_post(self):
        node = ast.parse('@app.post("/submit")\ndef fn(): pass').body[0].decorator_list[0]
        assert _route_of(node) == "POST /submit"

    def test_route_of_unrelated_decorator(self):
        node = ast.parse('@login_required\ndef fn(): pass').body[0].decorator_list[0]
        assert _route_of(node) is None

    def test_routes_in_directory(self, tmp_path):
        app_file = tmp_path / "app.py"
        app_file.write_text(
            '@app.route("/api/search")\n'
            'def search_view(): pass\n\n'
            'def helper(): pass\n'
        )
        test_file = tmp_path / "tests" / "test_app.py"
        test_file.parent.mkdir()
        test_file.write_text(
            '@app.route("/test")\n'
            'def test_view(): pass\n'
        )
        bad_syntax = tmp_path / "broken.py"
        bad_syntax.write_text("def def invalid syntax :::")

        routes = routes_in(tmp_path)
        assert routes == {"app.py::search_view": "GET /api/search"}


# ── node helpers ─────────────────────────────────────────────────────

from ravel_adapter.ravel import node_file_and_name, node_line, real_findings, call_edges


class TestNodeHelpers:
    def test_node_file_and_name_full(self):
        assert node_file_and_name("app.py::search_view::L41") == ("app.py", "search_view")

    def test_node_file_and_name_no_line(self):
        assert node_file_and_name("app.py::search") == ("app.py", "search")

    def test_node_file_and_name_bare(self):
        assert node_file_and_name("search") == ("search", "search")

    def test_node_line_with_line(self):
        assert node_line("app.py::search::L34") == "34"

    def test_node_line_without_line(self):
        assert node_line("app.py::search") == "?"


class TestReportFiltering:
    def test_real_findings_excludes_tests(self):
        report = {"findings": [
            {"file": "app.py", "rule_id": "B608"},
            {"file": "tests/test_app.py", "rule_id": "B101"},
            {"file": "demo-app/tests/test_x.py", "rule_id": "B101"},
        ]}
        result = real_findings(report)
        assert len(result) == 1
        assert result[0]["file"] == "app.py"

    def test_call_edges_filters_by_kind(self):
        report = {"graph_view": {"edges": [
            {"kind": "calls", "src": "a", "dst": "b"},
            {"kind": "imports", "src": "c", "dst": "d"},
            {"kind": "calls", "src": "e", "dst": "f"},
        ]}}
        result = call_edges(report)
        assert len(result) == 2
        assert all(e["kind"] == "calls" for e in result)


# ── formatting helpers ───────────────────────────────────────────────

from ravel_adapter.ravel import path_text, fn_label, title, module_file


class TestFormattingHelpers:
    def test_path_text_with_route(self):
        routes = {"app.py::search_view": "GET /api/search"}
        path = ["app.py::search_view::L41", "app.py::search::L30"]
        result = path_text(path, routes)
        assert result == "GET /api/search → search_view() → search()"

    def test_path_text_without_route(self):
        result = path_text(["jobs.py::retry_job::L10", "payments.py::process_payment::L5"], {})
        assert result == "retry_job() → process_payment()"

    def test_path_text_empty(self):
        assert path_text([], {}) == ""

    def test_fn_label_with_route(self):
        routes = {"app.py::search_view": "GET /api/search"}
        assert fn_label("app.py::search_view::L41", routes) == "search_view() (GET /api/search)"

    def test_fn_label_without_route(self):
        assert fn_label("app.py::search::L30", {}) == "search()"

    def test_title_known_rule(self):
        assert title({"rule_id": "B608", "message": "anything"}) == "SQL injection"
        assert title({"rule_id": "B307", "message": "anything"}) == "eval"
        assert title({"rule_id": "B506", "message": "anything"}) == "unsafe yaml.load"

    def test_title_unknown_rule_uses_message(self):
        result = title({"rule_id": "B999", "message": "Something dangerous. More text."})
        assert result == "Something dangerous"

    def test_module_file_plain_name(self):
        assert module_file("app") == "app.py"

    def test_module_file_with_extension(self):
        assert module_file("app.py") == "app.py"

    def test_module_file_dotted(self):
        assert module_file("vendor.old_parser") == "vendor/old_parser.py"

    def test_module_file_strips_whitespace(self):
        assert module_file("  app  ") == "app.py"


# ── handle() — help / unknown commands ───────────────────────────────

from ravel_adapter.ravel import handle, HELP, Reply


class TestHandleHelpAndUnknown:
    def test_empty_input_returns_help(self):
        reply = handle("", sender="alice")
        assert isinstance(reply, Reply)
        assert reply.text == f"@alice {HELP}"
        assert reply.document is None

    def test_just_mention_returns_help(self):
        reply = handle("@ravel", sender="bob")
        assert reply.text == f"@bob {HELP}"

    def test_help_command(self):
        reply = handle("@ravel help", sender="user")
        assert reply.text == f"@user {HELP}"

    def test_unknown_command_returns_help(self):
        reply = handle("@ravel foobar x y", sender="user")
        assert reply.text == f"@user {HELP}"

    def test_check_missing_argument_returns_help(self):
        """'check' without a target is an arity mismatch → falls through to help."""
        reply = handle("@ravel check", sender="user")
        assert HELP in reply.text

    def test_verify_wrong_arity_returns_help(self):
        reply = handle("@ravel verify only-one-arg", sender="user")
        assert HELP in reply.text

    def test_who_calls_wrong_second_word(self):
        reply = handle("@ravel who knows search", sender="user")
        assert HELP in reply.text

    def test_reply_always_starts_with_at_sender(self):
        reply = handle("@ravel help", sender="sec-triager")
        assert reply.text.startswith("@sec-triager ")


# ── shared scan report fixture ───────────────────────────────────────

from unittest.mock import patch

DEMO_SCAN_REPORT = {
    "findings": [
        {
            "file": "app.py", "node_name": "search", "rule_id": "B608",
            "message": "Possible SQL injection.", "severity": "medium",
            "callers": ["app.py::search_view::L41"],
            "static_evidence": {
                "reachable": "reachable",
                "path": ["app.py::search_view::L41", "app.py::search::L30"],
            },
        },
        {
            "file": "legacy_utils.py", "node_name": "eval_expr", "rule_id": "B307",
            "message": "Use of eval detected.", "severity": "medium",
            "callers": [],
            "static_evidence": {"reachable": "unreachable", "path": []},
        },
        {
            "file": "vendor/old_parser.py", "node_name": "parse", "rule_id": "B506",
            "message": "Use of unsafe yaml.load.", "severity": "medium",
            "callers": [],
            "static_evidence": {"reachable": "unreachable", "path": []},
        },
        {   # noise: finding in tests/
            "file": "tests/test_app.py", "node_name": "test_search", "rule_id": "B101",
            "message": "Assert used.", "severity": "low",
            "callers": [],
            "static_evidence": {"reachable": "unreachable", "path": []},
        },
    ],
    "graph_view": {
        "edges": [
            {"kind": "calls", "src": "app.py::search_view::L41",
             "dst": "app.py::search::L30", "resolved": True},
            {"kind": "calls", "src": "app.py::checkout_view::L55",
             "dst": "payments.py::process_payment::L10", "resolved": True},
            {"kind": "calls", "src": "jobs.py::retry_job::L20",
             "dst": "payments.py::process_payment::L10", "resolved": True},
        ],
    },
}


def _mock_scan(target_dir):
    """Return the shared fake report (ignores the directory)."""
    return DEMO_SCAN_REPORT


# ── handle() — check command ────────────────────────────────────────


class TestHandleCheck:
    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_check_reachable(self, mock_scan):
        reply = handle("@ravel check app.py:search", sender="triager")
        assert reply.text.startswith("@triager ")
        assert "REACHABLE" in reply.text
        assert "🔴" in reply.text
        assert "B608" in reply.text
        assert "search_view()" in reply.text
        assert reply.document is None

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_check_unreachable(self, mock_scan):
        reply = handle("@ravel check legacy_utils.py:eval_expr", sender="triager")
        assert "UNREACHABLE" in reply.text
        assert "🟢" in reply.text
        assert "B307" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_check_unreachable_vendor(self, mock_scan):
        reply = handle("@ravel check vendor/old_parser.py:parse", sender="triager")
        assert "UNREACHABLE" in reply.text
        assert "B506" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_check_unknown_function(self, mock_scan):
        reply = handle("@ravel check app.py:nonexistent", sender="triager")
        assert "UNKNOWN" in reply.text
        assert "⚪" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_check_with_demo_app_prefix(self, mock_scan):
        reply = handle("@ravel check demo-app/app.py:search", sender="triager")
        assert "REACHABLE" in reply.text


# ── handle() — who calls command ────────────────────────────────────


class TestHandleWhoCalls:
    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_who_calls_two_callers(self, mock_scan):
        reply = handle("@ravel who calls process_payment", sender="dev")
        assert reply.text.startswith("@dev ")
        assert "2 callers" in reply.text
        assert "checkout_view()" in reply.text
        assert "retry_job()" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_who_calls_one_caller(self, mock_scan):
        reply = handle("@ravel who calls search", sender="dev")
        assert "1 caller" in reply.text
        assert "search_view()" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_who_calls_no_callers(self, mock_scan):
        reply = handle("@ravel who calls nonexistent", sender="dev")
        assert "No callers" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_who_calls_strips_parens(self, mock_scan):
        reply = handle("@ravel who calls process_payment()", sender="dev")
        assert "2 callers" in reply.text


# ── handle() — verify command ───────────────────────────────────────


class TestHandleVerify:
    def test_verify_invalid_branch_name(self):
        reply = handle("@ravel verify --bad-flag search", sender="fixer")
        assert "Ravel error: not a valid branch name" in reply.text

    @patch("subprocess.run")
    @patch("ravel_adapter.ravel._git")
    @patch("ravel_adapter.ravel.routes_in", return_value={})
    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_verify_nothing_to_verify(self, mock_scan, mock_routes, mock_git, mock_subproc):
        top = str(Path(__file__).resolve().parents[2])
        mock_git.side_effect = [top, "base-sha", ""]  # rev-parse, merge-base, worktree add (base)
        reply = handle("@ravel verify fix/something nonexistent", sender="fixer")
        assert "⚪ UNKNOWN · nothing to verify" in reply.text

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    @patch("ravel_adapter.ravel._git")
    def test_verify_branch_not_found(self, mock_git, mock_scan):
        mock_git.side_effect = [
            str(Path(__file__).resolve().parents[2]),  # rev-parse --show-toplevel
            RavelError("git merge-base failed"),        # merge-base: no such branch
        ]
        reply = handle("@ravel verify fix/missing search", sender="fixer")
        assert "Ravel error: branch fix/missing not found" in reply.text

    @patch("subprocess.run")
    @patch("ravel_adapter.ravel._git")
    @patch("ravel_adapter.ravel.routes_in", return_value={"app.py::search_view": "GET /api/search"})
    @patch("ravel_adapter.ravel.scan")
    def test_verify_success(self, mock_scan, mock_routes, mock_git, mock_subproc):
        top = str(Path(__file__).resolve().parents[2])
        mock_git.side_effect = [top, "base-sha", "", ""]  # rev-parse, merge-base, 2× worktree add
        # First scan = before (has B608), Second scan = after (fix verified)
        after_report = {
            "findings": [
                {"file": "legacy_utils.py", "node_name": "eval_expr", "rule_id": "B307",
                 "message": "eval", "severity": "medium",
                 "static_evidence": {"reachable": "unreachable", "path": []}},
            ],
            "graph_view": {
                "edges": [
                    {"kind": "calls", "src": "app.py::search_view::L41", "dst": "app.py::search::L30"},
                ],
            },
        }
        mock_scan.side_effect = [DEMO_SCAN_REPORT, after_report]

        reply = handle("@ravel verify fix/sqli-search search", sender="fixer")
        assert "✅ FIX VERIFIED on fix/sqli-search" in reply.text
        assert "B608 gone from search()" in reply.text
        assert "0 reachable findings" in reply.text
        assert "Callers of search(): search_view() (GET /api/search)" in reply.text

    @patch("subprocess.run")
    @patch("ravel_adapter.ravel._git")
    @patch("ravel_adapter.ravel.routes_in", return_value={"app.py::search_view": "GET /api/search"})
    @patch("ravel_adapter.ravel.scan")
    def test_verify_still_reachable(self, mock_scan, mock_routes, mock_git, mock_subproc):
        top = str(Path(__file__).resolve().parents[2])
        mock_git.side_effect = [top, "base-sha", "", ""]
        mock_scan.side_effect = [DEMO_SCAN_REPORT, DEMO_SCAN_REPORT]  # unchanged!

        reply = handle("@ravel verify fix/sqli-search search", sender="fixer")
        assert "❌ STILL REACHABLE on fix/sqli-search" in reply.text
        assert "B608" in reply.text
        assert "Path: GET /api/search → search_view() → search()" in reply.text

    @patch("subprocess.run")
    @patch("ravel_adapter.ravel._git")
    @patch("ravel_adapter.ravel.routes_in", return_value={})
    @patch("ravel_adapter.ravel.scan")
    def test_verify_compares_branch_start_not_current_checkout(self, mock_scan, mock_routes,
                                                               mock_git, mock_subproc):
        """sec-fixer leaves the fix branch checked out; 'before' must still be the unfixed code."""
        top = str(Path(__file__).resolve().parents[2])
        mock_git.side_effect = [top, "base-sha", "", ""]
        mock_scan.side_effect = [DEMO_SCAN_REPORT, {"findings": [], "graph_view": {"edges": []}}]

        reply = handle("@ravel verify fix/sqli-search search", sender="fixer")

        assert "✅ FIX VERIFIED" in reply.text
        merge_base = mock_git.call_args_list[1].args
        assert merge_base[1:] == ("merge-base", "main", "fix/sqli-search")
        worktree_refs = [c.args[-1] for c in mock_git.call_args_list[2:]]
        assert worktree_refs == ["base-sha", "fix/sqli-search"]   # before = base, after = branch


# ── handle() — wiki and attach wiki ──────────────────────────────────


class TestHandleWiki:
    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_wiki_generates_page(self, mock_scan):
        reply = handle("@ravel wiki app", sender="triager")
        assert reply.text.startswith("@triager ")
        assert "📄 Wiki · app.py" in reply.text
        assert "Functions:" in reply.text
        assert "search" in reply.text
        assert reply.document is None

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_attach_wiki_returns_document(self, mock_scan):
        reply = handle("@ravel attach wiki app", sender="triager")
        assert reply.text.startswith('@triager 📄 Attached wiki: app (room document "wiki-app")')
        assert reply.document is not None
        doc_name, doc_content = reply.document
        assert doc_name == "wiki-app"
        assert "📄 Wiki · app.py" in doc_content

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_attach_wiki_nested_module(self, mock_scan):
        reply = handle("@ravel attach wiki vendor.old_parser", sender="triager")
        assert 'room document "wiki-vendor-old_parser"' in reply.text
        assert reply.document[0] == "wiki-vendor-old_parser"

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_wiki_nonexistent_module(self, mock_scan):
        reply = handle("@ravel wiki nonexistent_xyz", sender="triager")
        assert "Ravel error: no module nonexistent_xyz" in reply.text

    @patch("ravel_adapter.ravel.wiki_page", side_effect=RavelError("scan down"))
    def test_wiki_fallback_to_cache(self, mock_wiki_page):
        # app.md exists in wiki_cache/
        reply = handle("@ravel wiki app", sender="dev")
        assert "(from cache)" in reply.text
        assert "📄 Wiki · app.py" in reply.text


# ── handle() — unexpected exception handling & git helper ────────────

from unittest.mock import MagicMock
from ravel_adapter.ravel import _git


class TestErrorHandlingAndGit:
    @patch("ravel_adapter.ravel.check", side_effect=RuntimeError("something crashed internally"))
    def test_handle_never_raises_on_unexpected_exception(self, mock_check):
        reply = handle("@ravel check app.py:search", sender="user")
        assert reply.text.startswith("@user Ravel error: RuntimeError: something crashed internally")
        assert reply.document is None

    @patch("subprocess.run")
    def test_git_success(self, mock_subproc):
        mock_subproc.return_value = MagicMock(returncode=0, stdout="main\n", stderr="")
        out = _git(Path("."), "rev-parse", "--abbrev-ref", "HEAD")
        assert out == "main"

    @patch("subprocess.run")
    def test_git_failure_raises_ravel_error(self, mock_subproc):
        mock_subproc.return_value = MagicMock(returncode=1, stdout="", stderr="fatal: not a git repo")
        with pytest.raises(RavelError, match="git rev-parse failed: fatal: not a git repo"):
            _git(Path("."), "rev-parse", "--show-toplevel")


# ── scan() error handling ────────────────────────────────────────────

import subprocess
from ravel_adapter.ravel import scan


class TestScanExecution:
    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_scan_uv_not_found(self, mock_subproc, tmp_path):
        with pytest.raises(RavelError, match="not found; install uv"):
            scan(tmp_path)

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["uv"], timeout=120))
    def test_scan_timeout(self, mock_subproc, tmp_path):
        with pytest.raises(RavelError, match="Ravel took longer than"):
            scan(tmp_path)

    @patch("subprocess.run")
    def test_scan_failure_nonzero_exit(self, mock_subproc, tmp_path):
        mock_subproc.return_value = MagicMock(returncode=1, stderr="Syntax error in repo\n")
        with pytest.raises(RavelError, match="ravel scan failed: Syntax error in repo"):
            scan(tmp_path)

    @patch("subprocess.run")
    def test_scan_success(self, mock_subproc, tmp_path):
        def fake_run(cmd, **kwargs):
            # The command specifies --json <out>
            json_out = Path(cmd[cmd.index("--json") + 1])
            json_out.write_text('{"findings": [], "graph_view": {"edges": []}}')
            return MagicMock(returncode=0, stderr="")

        mock_subproc.side_effect = fake_run
        data = scan(tmp_path)
        assert data == {"findings": [], "graph_view": {"edges": []}}


# ── wiki cache & helper functions ────────────────────────────────────

from ravel_adapter.ravel import _app_node, _caller_name, build_wiki_cache


class TestWikiInternals:
    def test_app_node_filtering(self):
        assert _app_node("app.py::search::L30") is True
        assert _app_node("vendor/old_parser.py::parse::L6") is True
        assert _app_node("tests/test_app.py::test_fn") is False
        assert _app_node("demo-app/tests/test_x.py::test_fn") is False
        assert _app_node("unknown::jsonify") is False

    def test_caller_name_module_level(self):
        assert _caller_name("app.py::<file>") == "app.py module code"
        assert _caller_name("app.py::search_view::L41") == "search_view()"

    @patch("ravel_adapter.ravel.scan", side_effect=_mock_scan)
    def test_build_wiki_cache_writes_files(self, mock_scan, tmp_path, monkeypatch):
        fake_cache = tmp_path / "wiki_cache"
        monkeypatch.setattr("ravel_adapter.ravel.WIKI_CACHE", fake_cache)
        written = build_wiki_cache()
        assert "app" in written
        assert (fake_cache / "app.md").exists()
        content = (fake_cache / "app.md").read_text()
        assert "📄 Wiki · app.py" in content


def test_only_the_first_line_is_the_command():
    reply = handle("@ravel attach wiki app\n@sec-fixer Fix B608 in demo-app/app.py", sender="sec-triager")
    assert reply.text.startswith("@sec-triager 📄 Attached wiki: app")
    assert reply.document[0] == "wiki-app"

"""Ravel side of the adapter: one chat command in, one chat reply out.

Every answer comes from one Ravel run (< 1 s on demo-app):
    uv run --project $RAVEL_DIR ravel scan <dir> --limit 0 --json <file>
and is formatted per the reply contract in docs/ARCHITECTURE.md §6.

Commands (after "@ravel"):
    check <file>:<function>      is this finding reachable from outside input?
    verify <branch> <function>   is the finding gone on a fix branch?
    who calls <function>         callers, from Ravel's call graph
    wiki <module>                a module page built from the call graph
    attach wiki <module>         the same page, saved as a room document
    help
"""
import ast
import json
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    from . import config
except ImportError:          # run as a plain script: python ravel_adapter/ravel.py
    import config

WIKI_CACHE = Path(__file__).resolve().parent / "wiki_cache"

HELP = (
    "Ravel commands:\n"
    "• check <file>:<function>  (e.g. check app.py:search)\n"
    "• verify <branch> <function>  (e.g. verify fix/sqli-search search)\n"
    "• who calls <function>\n"
    "• wiki <module>  ·  attach wiki <module>"
)

RULE_TITLES = {"B608": "SQL injection", "B307": "eval", "B506": "unsafe yaml.load"}
REACH_ORDER = {"reachable": 0, "unknown": 1, "unreachable": 2}


class RavelError(Exception):
    """A short, chat-safe reason why Ravel could not answer."""


@dataclass
class Reply:
    text: str
    document: tuple | None = None   # (name, markdown) for "attach wiki"; posted by the protocol side


# ---------- running Ravel ----------

def scan(target_dir):
    """Run Ravel on a directory and return its JSON report."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "scan.json"
        cmd = [config.UV_BIN, "run", "--quiet", "--project", str(config.RAVEL_DIR),
               "ravel", "scan", str(target_dir), "--limit", "0", "--json", str(out)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=config.RAVEL_TIMEOUT, cwd=config.ROOT)
        except FileNotFoundError:
            raise RavelError(f"'{config.UV_BIN}' not found; install uv") from None
        except subprocess.TimeoutExpired:
            raise RavelError(f"Ravel took longer than {config.RAVEL_TIMEOUT}s") from None
        if result.returncode != 0 or not out.exists():
            last = (result.stderr.strip().splitlines() or ["no output"])[-1]
            raise RavelError(f"ravel scan failed: {last[:200]}")
        return json.loads(out.read_text())


# ---------- reading the report ----------

def node_file_and_name(node_id):
    """'app.py::search_view::L41' -> ('app.py', 'search_view')."""
    parts = node_id.split("::")
    return parts[0], (parts[1] if len(parts) > 1 else parts[0])


def node_line(node_id):
    last = node_id.rsplit("::", 1)[-1]
    return last[1:] if last.startswith("L") else "?"


def real_findings(report):
    """Scanner findings outside tests/ (asserts in tests are noise)."""
    return [f for f in report["findings"]
            if not f["file"].startswith("tests/") and "/tests/" not in f["file"]]


def call_edges(report):
    return [e for e in report["graph_view"]["edges"] if e["kind"] == "calls"]


def routes_in(source_dir):
    """Map 'file::function' -> 'GET /api/search' by reading route decorators."""
    found = {}
    for path in Path(source_dir).rglob("*.py"):
        rel = path.relative_to(source_dir).as_posix()
        if rel.startswith("tests/") or "/." in "/" + rel:
            continue
        try:
            tree = ast.parse(path.read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            for deco in fn.decorator_list:
                route = _route_of(deco)
                if route:
                    found[f"{rel}::{fn.name}"] = route
    return found


def _route_of(deco):
    """'@app.route("/x", methods=["POST"])' -> 'POST /x'; also @app.get/post/..."""
    if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)):
        return None
    verb = deco.func.attr
    if not deco.args or not isinstance(deco.args[0], ast.Constant):
        return None
    url = deco.args[0].value
    if verb == "route":
        methods = ["GET"]
        for kw in deco.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = [m.value for m in kw.value.elts if isinstance(m, ast.Constant)]
        return f"{'/'.join(methods)} {url}"
    if verb in ("get", "post", "put", "patch", "delete"):
        return f"{verb.upper()} {url}"
    return None


def fn_label(node_id, routes):
    """'search_view()', or 'search_view() (GET /api/search)' for a route."""
    file, name = node_file_and_name(node_id)
    route = routes.get(f"{file}::{name}")
    return f"{name}() ({route})" if route else f"{name}()"


def path_text(path, routes):
    """['app.py::search_view::L41', 'app.py::search::L30'] -> 'GET /api/search → search_view() → search()'."""
    steps = [f"{node_file_and_name(n)[1]}()" for n in path]
    if path:
        file, name = node_file_and_name(path[0])
        route = routes.get(f"{file}::{name}")
        if route:
            steps.insert(0, route)
    return " → ".join(steps)


def title(finding):
    return RULE_TITLES.get(finding["rule_id"], finding["message"].split(".")[0][:40])


# ---------- commands ----------

def normalize_target(target):
    """'demo-app/app.py:search()' -> ('app.py', 'search')."""
    if ":" not in target:
        raise RavelError("use <file>:<function>, e.g. check app.py:search")
    file, _, function = target.rpartition(":")
    file = file.strip().removeprefix("./").removeprefix(config.DEMO_REPO_PATH.name + "/")
    return file, function.strip().removesuffix("()")


def check(target):
    file, function = normalize_target(target)
    report = scan(config.DEMO_REPO_PATH)
    routes = routes_in(config.DEMO_REPO_PATH)
    hits = [f for f in real_findings(report) if f["file"] == file and f["node_name"] == function]
    if not hits:
        return (f"⚪ UNKNOWN · {file}:{function}\n"
                f"Reason: Ravel has no scanner finding for {function}() in {file}.")
    hits.sort(key=lambda f: REACH_ORDER.get(f["static_evidence"]["reachable"], 1))
    return "\n".join(_verdict(f, routes) for f in hits)


def _verdict(f, routes):
    where = f"{f['file']}:{f['node_name']} ({f['rule_id']} {title(f)})"
    ev = f["static_evidence"]
    if ev["reachable"] == "reachable":
        return (f"🔴 REACHABLE · {f['severity'].upper()} · {where}\n"
                f"Path: {path_text(ev['path'], routes)}")
    if ev["reachable"] == "unreachable":
        callers = [fn_label(c, routes) for c in f.get("callers") or []]
        proof = (f"called only by {', '.join(callers)}; none is reachable from outside input."
                 if callers else "0 callers; not reachable from any route.")
        return f"🟢 UNREACHABLE · {where}\nProof: {proof}"
    return f"⚪ UNKNOWN · {where}\nReason: a call on the way could not be resolved; a human should look."


def who_calls(function):
    function = function.strip().removesuffix("()")
    report = scan(config.DEMO_REPO_PATH)
    routes = routes_in(config.DEMO_REPO_PATH)
    edges = [e for e in call_edges(report) if node_file_and_name(e["dst"])[1] == function]
    if not edges:
        return f"No callers of {function}() found in Ravel's call graph."
    lines = [f"{function}() has {len(edges)} caller{'s' if len(edges) != 1 else ''}:"]
    for e in sorted(edges, key=lambda e: e["src"]):
        file, _ = node_file_and_name(e["src"])
        note = "" if e.get("resolved", True) else " (unresolved call)"
        lines.append(f"• {fn_label(e['src'], routes)} · {file}:{node_line(e['src'])}{note}")
    return "\n".join(lines)


BASE_BRANCH = "main"


def _scan_at(top, inside, ref, label):
    """Scan the demo app as it is at a git ref, in a temporary worktree (never `git checkout`).

    sec-fixer works in the same clone and switches branches, so what is checked out
    right now says nothing about either side of the fix.
    """
    worktree = top / ".ravel-worktrees" / f"{label.replace('/', '_')}-{uuid.uuid4().hex[:6]}"
    _git(top, "worktree", "add", "--detach", str(worktree), ref)
    try:
        return scan(worktree / inside), routes_in(worktree / inside)
    finally:
        subprocess.run(["git", "-C", str(top), "worktree", "remove", "--force", str(worktree)],
                       capture_output=True)


def verify(branch, function):
    """Compare the commit the fix branch started from with the branch's tip."""
    function = function.strip().removesuffix("()")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch):
        raise RavelError(f"not a valid branch name: {branch!r}")

    demo = config.DEMO_REPO_PATH
    top = Path(_git(demo, "rev-parse", "--show-toplevel"))
    inside = demo.relative_to(top)
    try:
        base = _git(top, "merge-base", BASE_BRANCH, branch)
    except RavelError:
        raise RavelError(f"branch {branch} not found") from None

    before_report, _ = _scan_at(top, inside, base, "base")
    before = [f for f in real_findings(before_report) if f["node_name"] == function]
    if not before:
        return (f"⚪ UNKNOWN · nothing to verify: no finding for {function}() "
                f"where {branch} started from {BASE_BRANCH}")
    rules = sorted({f["rule_id"] for f in before})

    report, routes = _scan_at(top, inside, branch, branch)
    after = real_findings(report)
    still = [f for f in after if f["node_name"] == function and f["rule_id"] in rules]
    reachable = [f for f in after if f["static_evidence"]["reachable"] == "reachable"]
    callers = [fn_label(e["src"], routes) for e in call_edges(report)
               if node_file_and_name(e["dst"])[1] == function]
    callers_line = f"Callers of {function}(): {', '.join(callers) or 'none'}"

    if not still and not reachable:
        return (f"✅ FIX VERIFIED on {branch} · {', '.join(rules)} gone from {function}(); "
                f"0 reachable findings\n{callers_line}")
    bad = (still or reachable)[0]
    if bad["static_evidence"]["reachable"] == "reachable":
        return (f"❌ STILL REACHABLE on {branch} · {bad['rule_id']} · "
                f"Path: {path_text(bad['static_evidence']['path'], routes)}\n{callers_line}")
    return f"❌ NOT VERIFIED on {branch} · {bad['rule_id']} still reported in {bad['node_name']}()\n{callers_line}"


def _git(where, *args):
    result = subprocess.run(["git", "-C", str(where), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RavelError(f"git {args[0]} failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


# ---------- wiki ----------

def module_file(module):
    """'app' / 'app.py' / 'vendor.old_parser' -> 'app.py' / 'vendor/old_parser.py'."""
    module = module.strip().removesuffix(".py").replace(".", "/")
    return f"{module}.py"


def wiki_page(module, report=None, source_dir=None):
    """A module page built from Ravel's call graph (no LLM). Markdown, ~15 lines."""
    source_dir = Path(source_dir or config.DEMO_REPO_PATH)
    report = report or scan(source_dir)
    file = module_file(module)
    path = source_dir / file
    if not path.exists():
        raise RavelError(f"no module {module} (looked for {file})")

    tree = ast.parse(path.read_text())
    routes = routes_in(source_dir)
    # Only calls between the app's own functions: skip tests and unresolved library calls.
    edges = [e for e in call_edges(report) if _app_node(e["src"]) and _app_node(e["dst"])]
    findings = real_findings(report)
    summary = (ast.get_docstring(tree) or "").strip().splitlines()

    lines = [f"📄 Wiki · {file}"]
    if summary:
        lines.append(summary[0])
    imported_by = sorted({node_file_and_name(e["src"])[0] for e in edges
                          if node_file_and_name(e["dst"])[0] == file
                          and node_file_and_name(e["src"])[0] != file})
    lines.append(f"Used by: {', '.join(imported_by) or 'no other module'}")
    lines.append("Functions:")
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        args = ", ".join(a.arg for a in fn.args.args)
        bits = []
        route = routes.get(f"{file}::{fn.name}")
        if route:
            bits.append(f"HTTP route {route} (outside input)")
        callers = sorted({_caller_name(e["src"]) for e in edges
                          if node_file_and_name(e["dst"]) == (file, fn.name)})
        callees = sorted({node_file_and_name(e["dst"])[1] + "()" for e in edges
                          if node_file_and_name(e["src"]) == (file, fn.name)})
        if callers:
            bits.append("called by " + ", ".join(callers))
        elif not route:
            bits.append("no callers")
        if callees:
            bits.append("calls " + ", ".join(callees))
        for f in findings:
            if f["file"] == file and f["node_name"] == fn.name:
                bits.append(f"⚠️ {f['rule_id']} {title(f)} ({f['static_evidence']['reachable']})")
        lines.append(f"• {fn.name}({args}) — " + " · ".join(bits))
    return "\n".join(lines)


def _app_node(node_id):
    """True for the app's own code: a .py file outside tests/ (not 'unknown::jsonify')."""
    file = node_file_and_name(node_id)[0]
    return file.endswith(".py") and not file.startswith("tests/") and "/tests/" not in file


def _caller_name(node_id):
    """'app.py::<file>' is code at module level (e.g. under if __name__ == ...)."""
    file, name = node_file_and_name(node_id)
    return f"{file} module code" if name == "<file>" else f"{name}()"


def wiki(module):
    """Live page; falls back to the committed cache if Ravel can't run."""
    try:
        return wiki_page(module)
    except RavelError:
        cached = WIKI_CACHE / f"{module_file(module)[:-3].replace('/', '.')}.md"
        if cached.exists():
            return cached.read_text().strip() + "\n(from cache)"
        raise


def build_wiki_cache():
    """Write wiki_cache/<module>.md for every module in the demo app."""
    report = scan(config.DEMO_REPO_PATH)
    WIKI_CACHE.mkdir(exist_ok=True)
    written = []
    for path in sorted(config.DEMO_REPO_PATH.rglob("*.py")):
        rel = path.relative_to(config.DEMO_REPO_PATH).as_posix()
        if rel.startswith("tests/") or path.name == "__init__.py":
            continue
        module = rel[:-3].replace("/", ".")
        (WIKI_CACHE / f"{module}.md").write_text(wiki_page(module, report) + "\n")
        written.append(module)
    return written


# ---------- chat entry point ----------

def strip_mention(text, names=("ravel",)):
    """Drop a leading '@ravel' (or another of our names), any case."""
    text = text.strip()
    for name in names:
        match = re.match(rf"@{re.escape(name)}\b[:,]?\s*", text, re.IGNORECASE)
        if match:
            return text[match.end():].strip()
    return text


def handle(text, sender="you", names=("ravel",)):
    """One chat message -> one Reply. Never raises."""
    words = strip_mention(text, names).split()
    verb = words[0].lower() if words else "help"
    try:
        if verb == "check" and len(words) == 2:
            body = check(words[1])
        elif verb == "verify" and len(words) == 3:
            body = verify(words[1], words[2])
        elif verb == "who" and len(words) == 3 and words[1].lower() == "calls":
            body = who_calls(words[2])
        elif verb == "wiki" and len(words) == 2:
            body = wiki(words[1])
        elif verb == "attach" and len(words) == 3 and words[1].lower() == "wiki":
            page = wiki(words[2])
            name = f"wiki-{module_file(words[2])[:-3].replace('/', '-')}"
            return Reply(f"@{sender} 📄 Attached wiki: {words[2]} (room document \"{name}\")",
                         document=(name, page))
        else:
            body = HELP
    except RavelError as err:
        body = f"Ravel error: {err}"
    except Exception as err:   # keep the chat loop alive whatever happens
        body = f"Ravel error: {type(err).__name__}: {str(err)[:150]}"
    return Reply(f"@{sender} {body}")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--build-wiki"]:
        print("Wrote:", ", ".join(build_wiki_cache()))
    else:
        print(handle(" ".join(sys.argv[1:])).text)

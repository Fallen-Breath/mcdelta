"""Export a version range and its comparison inputs for analysis."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = "src/main/resources/version.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) or value.endswith("."):
        raise ValueError(f"Cannot use as a directory or report name: {value!r}")
    return value


def git(repo, *arguments, check=True):
    return subprocess.run(["git", "-C", str(repo), *arguments], check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_text(repo, *arguments):
    return git(repo, *arguments).stdout.decode("utf-8").strip()


def resolve(repo, query):
    result = git(repo, "rev-parse", "--verify", f"{query}^{{commit}}", check=False)
    if not result.returncode:
        return result.stdout.decode().strip()
    for history in (("--first-parent", "HEAD"), ("--all",)):
        matches = set()
        for entry in git_text(repo, "log", "--format=%H%x09%s", *history).splitlines():
            commit, subject = entry.split("\t", 1)
            if subject == query:
                matches.add(commit)
        if len(matches) == 1:
            return matches.pop()
        if len(matches) > 1:
            raise ValueError(f"Version {query!r} matches multiple commits; provide a Git reference.")
    raise ValueError(f"Cannot find version or commit: {query}")


def version(repo, commit):
    result = git(repo, "show", f"{commit}:{VERSION_FILE}", check=False)
    value = json.loads(result.stdout)["id"] if not result.returncode else git_text(repo, "show", "-s", "--format=%s", commit)
    return safe_name(value)


def plan(repo, start, end):
    baseline, target = resolve(repo, start), resolve(repo, end)
    git(repo, "merge-base", "--is-ancestor", baseline, target)
    commits = git_text(repo, "rev-list", "--reverse", "--topo-order", f"{baseline}..{target}").splitlines()
    names = {}

    def name(commit):
        if commit not in names:
            names[commit] = version(repo, commit)
        return names[commit]

    comparisons = []
    for commit in commits:
        parent = git_text(repo, "rev-parse", f"{commit}^1")
        comparisons.append({"baseline_commit": parent, "baseline_version": name(parent),
                            "target_commit": commit, "version": name(commit)})
    if len({item["version"] for item in comparisons}) != len(comparisons):
        raise ValueError("The range contains duplicate game version names.")
    return name(baseline), name(target), comparisons


def export_snapshot(repo, commit, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=destination.parent) as exported:
        subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit],
                       stdout=exported, check=True)
        exported.seek(0)
        with tarfile.open(fileobj=exported) as archive:
            for member in archive:
                path = (destination / member.name).resolve()
                if not path.is_relative_to(destination.resolve()):
                    raise ValueError(f"Archive path escapes snapshot: {member.name}")
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, path.open("wb") as output:
                        shutil.copyfileobj(source, output)
                elif member.issym():
                    link = path.parent / member.linkname
                    if not link.resolve().is_relative_to(destination.resolve()):
                        raise ValueError(f"Archive link escapes snapshot: {member.name}")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.symlink_to(member.linkname)
                else:
                    raise ValueError(f"Unsupported archive entry: {member.name}")
    print(json.dumps({"exported": commit}), flush=True)


def prepare(arguments):
    config = read_json(ROOT / "config.local.json")
    repo = Path(config["source_repo"]).expanduser()
    if not repo.is_absolute():
        repo = ROOT / repo
    repo = repo.resolve()
    start, end, comparisons = plan(repo, arguments.start, arguments.end)
    release = safe_name(arguments.release)
    work = ROOT / "work" / f"{start}_{end}"
    sources = {}
    analyses = []
    for item in comparisons:
        for commit in (item["baseline_commit"], item["target_commit"]):
            sources[commit] = work / "sources" / commit
        analyses.append({
            "baseline": {"version": item["baseline_version"], "commit": item["baseline_commit"],
                         "directory": str(sources[item["baseline_commit"]])},
            "target": {"version": item["version"], "commit": item["target_commit"],
                       "directory": str(sources[item["target_commit"]])},
            "work_directory": str(work / "analyses" / item["version"]),
            "report": str(ROOT / "reports" / release / f"{item['version']}.md"),
        })
    task = {
        "start_version": start, "end_version": end, "release": release,
        "work_directory": str(work),
        "source_github": config.get("source_github", "").rstrip("/").removesuffix(".git"),
        "prompt": str(ROOT / "prompts/snapshot_behavior_analysis.md"),
        "analyses": analyses,
    }
    if arguments.plan_only:
        print(json.dumps(task, ensure_ascii=False, indent=2))
        return
    for commit, directory in sources.items():
        export_snapshot(repo, commit, directory)
    for analysis in analyses:
        Path(analysis["work_directory"]).mkdir(parents=True, exist_ok=True)
        Path(analysis["report"]).parent.mkdir(parents=True, exist_ok=True)
    task_path = work / "task.json"
    write_json(task_path, task)
    print(json.dumps({"task_file": str(task_path), "analyses": len(analyses)}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", required=True)
    parser.add_argument("--to", dest="end", required=True)
    parser.add_argument("--release", required=True, help="Release directory for these reports")
    parser.add_argument("--plan-only", action="store_true", help="Print comparisons without exporting")
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3.9

# ========== configuration ==========
USERNAME = "tamuhey"
# ===================================

from dataclasses import dataclass
import json
import os
import subprocess
from subprocess import PIPE
import sys
from typing import Any, Callable, ClassVar, List, Optional, Union


@dataclass
class Repository:
    owner: str
    name: str

    @classmethod
    def from_api_resp(cls, dat: dict[str, Any]) -> "Repository":
        owner = dat["owner"]["name"]
        name = dat["name"]
        return cls(owner, name)

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass
class IssuePRBase:
    created_at: str
    title: str
    url: str
    repo: Repository
    typename: ClassVar[str] = ""

    @classmethod
    def from_resp(cls, dat: dict[str, Any]):
        created_at = dat["createdAt"]
        title = dat["title"]
        url = dat["url"]
        repo = Repository.from_api_resp(dat["repository"])
        return cls(created_at=created_at, title=title, url=url, repo=repo)

    def __str__(self) -> str:
        assert self.typename
        return f"""
Type       : {self.typename}
Title      : {self.title}
Repo       : {self.repo}
Created at : {self.created_at}
url        : {self.url}
"""


@dataclass
class Issue(IssuePRBase):
    typename: ClassVar[str] = "Issue"


@dataclass
class PullRequest(IssuePRBase):
    typename: ClassVar[str] = "PullRequest"


NodeType = Union[Issue, PullRequest]
nodes: list[NodeType] = []


def print_issues(issues: list[NodeType]):
    for i, t in enumerate(issues):
        record = f"""{i:<4}: {t.title:<30} ({str(t.repo)})"""
        print(record)


QUERY = """
query($target: String!) {
search(first: 100, type: ISSUE, query: $target) {
    issueCount
    pageInfo {
    hasNextPage
    endCursor
    }
    edges {
    node {
        ... on RepositoryNode {
            repository {
                owner {
                    ... on Organization {
                        name
                    }
                    ... on User {
                        name: login
                    }
                },
                name,
            },
        }
        ... on UniformResourceLocatable {
            url,
        }
        ... on Issue {
            createdAt
            title
            url,
            bodyText,
            __typename,
        }
        ... on PullRequest {
            createdAt
            title
            url,
            bodyText,
            __typename,
        }
    }
    }
}
}
"""


def _update_issues():
    target = f'"assignee:{USERNAME} is:open"'
    cmd = f"gh api graphql -f query='{QUERY}' -F target={target}"
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, check=True)
    dat = json.loads(ret.stdout.decode())

    nodes.clear()
    try:
        for edge in dat["data"]["search"]["edges"]:
            node = edge["node"]
            if not node:
                continue
            typename = node["__typename"]
            if typename == Issue.typename:
                kls = Issue
            elif typename == PullRequest.typename:
                kls = PullRequest
            else:
                raise ValueError(f"Unreachable: {edge}")
            nodes.append(kls.from_resp(node))
    except KeyError as e:
        raise ValueError(f"Unexpected response: {dat}") from e


# `cmd_{x}` defines the command `x`


def cmd_list():
    """(list) List all issues"""
    _update_issues()
    print_issues(nodes)


def cmd_close(index: Optional[int] = None):
    """(close {id}) Close an issue specified by index"""
    if index is None:
        index = int(input("Close which?: "))
    index = int(index)
    target = nodes[index]
    if not isinstance(target, Issue):
        print(f"{target.typename} cannot be closed")
        return
    print(str(target))
    if (rep := input("Close? (y/N): ").lower().strip()) and rep and rep[0] == "y":
        subprocess.run(["gh", "issue", "close", target.url])
    else:
        print("Aborted")


def cmd_detail(index: Optional[int] = None):
    """(detail {id}) Show details of an issue specified by index"""
    if index is None:
        index = int(input("Which issue to show detail? (number) "))
    index = int(index)
    print(str(nodes[index]))


def cmd_new():
    """(new) Create new issue"""
    user = os.environ["GITHUB_USERNAME"]
    repo = os.environ["TODO_REPO"]
    subprocess.run(
        ["gh", "--repo", repo, "issue", "create", "--assignee", user],
        check=True,
    )


def cmd_help(subcmd: Optional[str]):
    """(help (alias)?) Help command"""
    if subcmd.lower().strip() == "alias":
        for k, v in ALIASES.items():
            print(f"{k:<5} -> {v}")
    else:
        for k, f in CMDs.items():
            doc = f.__doc__
            print(f"{k:<20}: {doc}")


CMDs = {
    "list": cmd_list,
    "close": cmd_close,
    "detail": cmd_detail,
    "new": cmd_new,
    "help": cmd_help,
}
ALIASES = {"l": "list", "c": "close", "n": "new", "h": "help", "d": "detail"}


def read_cmd() -> Union[tuple[Callable, List[str]], str]:
    try:
        inputs = input("> ")
    except (EOFError, KeyboardInterrupt):
        exit(0)
    cmdl = inputs.split(" ")
    cmdstr, args = cmdl[0], cmdl[1:]
    if (cmd := CMDs.get(ALIASES.get(cmdstr, cmdstr))) is not None:
        return cmd, args
    else:
        try:
            index = int(cmdstr)
            return cmd_detail, [str(index)]
        except:
            return inputs


def main():
    cmd_list()
    while True:
        if isinstance((cmds := read_cmd()), tuple):
            try:
                cmds[0](*cmds[1])
            except Exception as e:
                print(e, file=sys.stderr)
        elif cmds:
            print("Unknown command: ", cmds, file=sys.stderr)


if __name__ == "__main__":
    main()

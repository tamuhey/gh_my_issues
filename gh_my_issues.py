#!/usr/bin/env python3.9
from dataclasses import dataclass
import json
import os
import pprint
import subprocess
from subprocess import PIPE
import sys
from typing import Any, Callable, List, Optional, Tuple, Union

import fire


@dataclass
class Repository:
    owner: str
    name: str

    @classmethod
    def from_resp(cls, dat: dict[str, Any]) -> "Repository":
        owner = dat["owner"]["name"]
        name = dat["name"]
        return cls(owner, name)

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass
class Issue:
    created_at: str
    title: str
    url: str
    repo: Repository

    @classmethod
    def from_resp(cls, dat: dict[str, Any]) -> "Issue":
        created_at = dat["createdAt"]
        title = dat["title"]
        url = dat["url"]
        repo = Repository.from_resp(dat["repository"])
        return Issue(created_at=created_at, title=title, url=url, repo=repo)

    def __str__(self) -> str:
        return f"""
Title      : {self.title}
Repo       : {self.repo}
Created at : {self.created_at}
url        : {self.url}
"""


def print_issues(issues: list[Issue]):
    for i, t in enumerate(issues):
        record = f"""# {i:<4}| {str(t.repo):<30}| {t.title:<30}"""
        print(record)


issues: list[Issue] = []


def _list():
    cmd = """
gh api graphql -f query='
        query {
        search(first: 100, type: ISSUE, query: "assignee:tamuhey is:open") {
            issueCount
            pageInfo {
            hasNextPage
            endCursor
            }
            edges {
            node {
                ... on Issue {
                createdAt
                title
                url,
                bodyText,
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
            }
            }
        }
        }'
    """
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, check=True)
    dat = json.loads(ret.stdout.decode())

    issues.clear()
    for issue in dat["data"]["search"]["edges"]:
        issues.append(Issue.from_resp(issue["node"]))


def cmd_list():
    _list()
    print_issues(issues)


def cmd_close(index: Optional[int] = None):
    if index is None:
        index = int(input("Close which?: "))
    index = int(index)
    target = issues[index]
    print(str(target))
    if ask("Are you ok to close? (y/N): "):
        subprocess.run(["gh", "issue", "close", target.url])
    else:
        print("Aborted")


def cmd_detail(index: Optional[int] = None):
    if index is None:
        index = int(input("Which issue to show detail? (number) "))
    index = int(index)
    print(str(issues[index]))


def cmd_new():
    user = os.environ["GITHUB_USERNAME"]
    repo = os.environ["TODO_REPO"]
    subprocess.run(
        ["gh", "--repo", repo, "issue", "create", "--assignee", user],
        check=True,
    )


def ask(msg: Optional[str] = None) -> bool:
    msg = msg or "Are you ok? (y/N): "
    rep = input(msg).lower()
    return bool(rep) and rep[0] == "y"


CMDs = {"list": cmd_list, "close": cmd_close, "detail": cmd_detail, "new": cmd_new}
ALIASES = {"l": "list", "c": "close", "n": "new"}


def read_cmd() -> Union[tuple[Callable, List[str]], str]:
    try:
        inputs = input("> ")
    except EOFError:
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
        else:
            print("Unknown command: ", cmds, file=sys.stderr)


if __name__ == "__main__":
    fire.Fire(main)
#  if [[ $subcmd == "list" ]]; then
#      gh api graphql -f query='
#      query {
#      search(first: 100, type: ISSUE, query: "assignee:tamuhey is:open") {
#          issueCount
#          pageInfo {
#          hasNextPage
#          endCursor
#          }
#          edges {
#          node {
#              ... on Issue {
#              createdAt
#              title
#              url,
#              }
#          }
#          }
#      }
#      }
#      ' |  jq -r '.data.search.edges | map(.node) | .[]  | [.title, .url]'
#  fi

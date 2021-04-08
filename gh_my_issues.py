#!/usr/bin/env python3.9

from dataclasses import dataclass
import json
import subprocess
from subprocess import PIPE

import fire


@dataclass
class Issue:
    created_at: str
    title: str
    url: str

    @classmethod
    def from_resp(cls, dat: dict[str, str]) -> "Issue":
        created_at = dat["createdAt"]
        title = dat["title"]
        url = dat["url"]
        return Issue(created_at=created_at, title=title, url=url)


def print_issues(issues: list[Issue]):
    for i, t in enumerate(issues):
        record = f"""# {i:<4}: {t.title}"""
        print(record)


def list() -> list[Issue]:
    cmd = """gh api graphql -f query='
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
                }
            }
            }
        }
        }'"""
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, check=True)
    dat = json.loads(ret.stdout.decode())
    issues = []
    for issue in dat["data"]["search"]["edges"]:
        issues.append(Issue.from_resp(issue["node"]))
    return issues


def main():
    issues = list()
    print_issues(issues)


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

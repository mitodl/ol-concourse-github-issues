"""
resources:
  - name: my-concourse-github-issues
    type: concourse-github-issues
    source:
      github_auth_token: ((github.auth_token))
      project_key: concourse
      repo: "mitodl/my-project"

"""
from concoursetools.additional import ConcourseResource  # type: ignore
from concoursetools.version import TypedVersion  # type: ignore
from github import Github  # type: ignore
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ConcourseGithubIssuesVersion(TypedVersion):
    issue_dt: datetime


class ConcourseGithubIssuesResource(ConcourseResource):
    def __init__(self, github_auth_token, repo, issue_title_prefix):
        super().__init__(ConcourseGithubIssuesVersion)
        self.gh = Github(auth=github_auth_token)
        self.repo = self.gh.get_repo(repo)
        self.issue_title_prefix = issue_title_prefix
        self.found_pipeline_issues = []

    def fetch_new_versions(self, previous_version=None):
        all_pipeline_issues = self.repo.get_issues(state="open", labels=["pipeline"])
        matching_issues = [
            issue
            for issue in all_pipeline_issues
            if issue.title.startswith(self.issue_title_prefix)
        ]
        if matching_issues in self.found_pipeline_issues:
            return [previous_version]
        else:
            self.found_pipeline_issues = matching_issues
            return self.found_pipeline_issues

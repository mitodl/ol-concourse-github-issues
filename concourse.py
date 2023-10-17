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
from github import Github, Auth, enable_console_debug_logging  # type: ignore
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ConcourseGithubIssuesVersion(TypedVersion):
    issue_dt: datetime


class ConcourseGithubIssuesResource(ConcourseResource):
    def __init__(self, access_token, repository, issue_prefix):
        enable_console_debug_logging()
        super().__init__(ConcourseGithubIssuesVersion)
        print(f"ConcourseGithubIssuesResource:init: {repository=}")
        print(f"ConcourseGithubIssuesResource:init: {issue_prefix=}")
        self.gh = Github(auth=Auth.Token(access_token))
        self.repo = self.gh.get_repo(repository)
        self.issue_prefix = issue_prefix
        self.found_pipeline_issues = []

    def fetch_new_versions(self, previous_version=None):
        all_pipeline_issues = self.repo.get_issues(state="open", labels=["pipeline"])
        matching_issues = [
            issue
            for issue in all_pipeline_issues
            if issue.title.startswith(self.issue_prefix)
        ]
        if matching_issues in self.found_pipeline_issues:
            return [previous_version]
        else:
            self.found_pipeline_issues = matching_issues
            return self.found_pipeline_issues

    def download_version(self, version, destination_dir, build_metadata):
        pass

    def publish_new_version(self, sources_dir, build_metadata):
        pass

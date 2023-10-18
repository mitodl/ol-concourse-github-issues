"""
resources:
  - name: my-concourse-github-issues
    type: concourse-github-issues
    source:
      github_auth_token: ((github.auth_token))
      project_key: concourse
      repo: "mitodl/my-project"

"""
from typing import Literal, Optional
from concoursetools import ConcourseResource
from concoursetools.version import Version, SortableVersionMixin
from github import Github, Auth, Issue


class ConcourseGithubIssuesVersion(Version, SortableVersionMixin):
    def __init__(
        self, issue_number: int, issue_title: str, issue_state, issue_created_at: str
    ):
        self.issue_number = issue_number
        self.issue_title = issue_title
        self.issue_created_at = issue_created_at
        self.issue_state = issue_state

    def __lt__(self, other: "ConcourseGithubIssuesVersion"):
        return self.issue_number < other.issue_number


class ConcourseGithubIssuesResource(ConcourseResource):
    def __init__(
        self,
        access_token: str,
        repository: str,
        issue_state: Literal["open", "closed"] = "closed",
        issue_prefix: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ):
        super().__init__(ConcourseGithubIssuesVersion)
        self.gh = Github(auth=Auth.Token(access_token))
        self.repo = self.gh.get_repo(repository)
        self.issue_state = issue_state
        self.issue_prefix = issue_prefix
        self.found_pipeline_issues: list[Issue] = []
        self.issue_labels = labels

    def _to_version(self, gh_issue: Issue):
        return ConcourseGithubIssuesVersion(
            issue_number=gh_issue.number,
            issue_title=gh_issue.title,
            issue_state=gh_issue.state,
            issue_created_at=gh_issue.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def _from_version(self, version: ConcourseGithubIssuesVersion):
        return self.repo.get_issue(version.issue_number)

    def fetch_new_versions(self, previous_version=None):
        all_pipeline_issues = self.repo.get_issues(
            state=self.issue_state, labels=self.issue_labels or []
        )
        matching_issues = [
            issue
            for issue in all_pipeline_issues
            if issue.title.startswith(self.issue_prefix)
        ]
        if matching_issues in self.found_pipeline_issues:
            return [previous_version]
        else:
            self.found_pipeline_issues = matching_issues
            return [self._to_version(issue) for issue in self.found_pipeline_issues]

    def download_version(self, version, destination_dir, build_metadata):
        pass

    def publish_new_version(self, sources_dir, build_metadata):
        pass

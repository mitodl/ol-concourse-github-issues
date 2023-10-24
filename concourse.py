"""
resources:
  - name: my-concourse-github-issues
    type: concourse-github-issues
    source:
      github_auth_token: ((github.auth_token))
      project_key: concourse
      repo: "mitodl/my-project"

"""
from pathlib import Path
import textwrap
import json
from datetime import datetime
from typing import Literal, Optional
from concoursetools import BuildMetadata, ConcourseResource
from concoursetools.version import Version, SortableVersionMixin
from github import Github, Auth
from github.Issue import Issue

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%S"


class ConcourseGithubIssuesVersion(Version, SortableVersionMixin):
    def __init__(
        self,
        issue_created_at: str,
        issue_closed_at: Optional[str],
        issue_number: int,
        issue_state: Literal["open", "closed"],
        issue_title: str,
        issue_url: str,
    ):
        self.issue_created_at = issue_created_at
        self.issue_number = issue_number
        self.issue_state = issue_state
        self.issue_title = issue_title
        self.issue_url = issue_url
        self.issue_closed_at = issue_closed_at

    def __lt__(self, other: "ConcourseGithubIssuesVersion"):
        if self.issue_state == "closed":
            return datetime.strptime(
                ISO_8601_FORMAT, self.issue_closed_at  # type: ignore[arg-type]
            ) < datetime.strptime(
                ISO_8601_FORMAT, other.issue_closed_at  # type: ignore[arg-type]
            )
        else:
            return datetime.strptime(
                ISO_8601_FORMAT, self.issue_created_at
            ) < datetime.strptime(ISO_8601_FORMAT, other.issue_created_at)


class ConcourseGithubIssuesResource(ConcourseResource):
    def __init__(
        self,
        access_token: str,
        repository: str,
        issue_state: Literal["open", "closed"] = "closed",
        issue_prefix: Optional[str] = None,
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None,
        issue_title_template: str = "[bot] Pipeline task completed",
        issue_body_template: str = textwrap.dedent(
            """\
        Pipeline: {BUILD_PIPELINE_NAME}
        Build ID: {BUILD_ID}
        Job: {BUILD_JOB_NAME}
        """
        ),
    ):
        super().__init__(ConcourseGithubIssuesVersion)
        self.gh = Github(auth=Auth.Token(access_token))
        self.repo = self.gh.get_repo(repository)
        self.issue_state = issue_state
        self.issue_prefix = issue_prefix
        self.found_pipeline_issues: list[Issue] = []
        self.issue_labels = labels
        self.assignees = assignees
        self.issue_title_template = issue_title_template
        self.issue_body_template = issue_body_template

    def _to_version(self, gh_issue: Issue) -> ConcourseGithubIssuesVersion:
        if gh_issue.state == "closed":
            issue_closed_time = gh_issue.closed_at.strftime(ISO_8601_FORMAT)
        else:
            issue_closed_time = None
        return ConcourseGithubIssuesVersion(
            issue_number=gh_issue.number,
            issue_title=gh_issue.title,
            issue_state=gh_issue.state,
            issue_created_at=gh_issue.created_at.strftime(ISO_8601_FORMAT),
            issue_url=gh_issue.url,
            issue_closed_at=issue_closed_time,
        )

    def _from_version(self, version: ConcourseGithubIssuesVersion) -> Issue:
        return self.repo.get_issue(int(version.issue_number))

    def get_all_issues(self):
        return self.repo.get_issues(
            state=self.issue_state, labels=self.issue_labels or []
        )

    def get_matching_issues(self):
        all_pipeline_issues = self.get_all_issues()

        return [
            issue
            for issue in all_pipeline_issues
            if issue.title.startswith(self.issue_prefix or "")
        ]

    def fetch_new_versions(self, previous_version=None):
        matching_issues = self.get_matching_issues()
        sorted_issues = sorted(matching_issues, key=lambda issue: issue.number)
        try:
            previous_issue_number = previous_version.number
        except AttributeError:
            previous_issue_number = 0
        new_versions = [
            self._to_version(issue)
            for issue in sorted_issues
            if issue.number > previous_issue_number
        ]
        return new_versions or [previous_version]

    def download_version(self, version, destination_dir, build_metadata):
        with Path(destination_dir).joinpath("gh_issue.json").open("w") as issue_file:
            issue_file.write(json.dumps(version.to_flat_dict()))
        return version, {}

    def publish_new_version(
        self,
        sources_dir,
        build_metadata: BuildMetadata,
        assignees: Optional[list[str]] = None,
        labels: Optional[list[str]] = None,
    ):
        new_issue = self.repo.create_issue(
            title=self.issue_title_template.format(**build_metadata.__dict__),
            assignees=assignees or [],
            labels=labels or [],
            body=self.issue_body_template.format(**build_metadata.__dict__),
        )
        return self._to_version(new_issue), {}

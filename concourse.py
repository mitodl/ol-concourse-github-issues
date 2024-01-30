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
import sys
from datetime import datetime
from typing import Literal, Optional, Tuple
from concoursetools import BuildMetadata
from concoursetools.additional import SelfOrganisingConcourseResource
from concoursetools.version import Version, SortableVersionMixin
from github import Github, Auth
from github.Issue import Issue

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%S"


def build_metadata_dict(build_metadata: BuildMetadata) -> dict[str, str]:
    return dict(
        BUILD_URL=build_metadata.build_url(),
        BUILD_ID=build_metadata.BUILD_ID,
        BUILD_TEAM_NAME=build_metadata.BUILD_TEAM_NAME,
        BUILD_NAME=build_metadata.BUILD_NAME,
        BUILD_JOB_NAME=build_metadata.BUILD_JOB_NAME,
        BUILD_PIPELINE_NAME=build_metadata.BUILD_PIPELINE_NAME,
        BUILD_PIPELINE_INSTANCE_VARS=build_metadata.BUILD_PIPELINE_INSTANCE_VARS,
        ATC_EXTERNAL_URL=build_metadata.ATC_EXTERNAL_URL,
    )


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
        if self.issue_state == other.issue_state == "closed":
            return datetime.strptime(
                self.issue_closed_at,  # type: ignore[arg-type]
                ISO_8601_FORMAT,
            ) < datetime.strptime(
                other.issue_closed_at,  # type: ignore[arg-type]
                ISO_8601_FORMAT,
            )
        else:
            return int(self.issue_number) < int(other.issue_number)


class ConcourseGithubIssuesResource(SelfOrganisingConcourseResource):
    def __init__(
        self,
        repository: str,
        access_token: Optional[str] = None,
        app_id: Optional[int] = None,
        app_installation_id: Optional[int] = None,
        assignees: Optional[list[str]] = None,
        issue_prefix: Optional[str] = None,
        labels: Optional[list[str]] = None,
        private_ssh_key: Optional[str] = None,
        auth_method: Literal["token", "app"] = "token",
        issue_state: Literal["open", "closed"] = "closed",
        issue_title_template: str = "[bot] Pipeline {BUILD_PIPELINE_NAME} task {BUILD_JOB_NAME} completed",
        issue_body_template: str = textwrap.dedent(
            """\
        The task {BUILD_JOB_NAME} in pipeline {BUILD_PIPELINE_NAME} has completed build number {BUILD_NAME}.
        Please refer to [the build log]({BUILD_URL}) for details of what changes this includes.
        Closing this issue will trigger the next job in the pipeline {BUILD_PIPELINE_NAME}.
        """
        ),
    ):
        super().__init__(ConcourseGithubIssuesVersion)
        if auth_method == "token":
            self.gh = Github(auth=Auth.Token(access_token))
        else:
            self.gh = Github(
                auth=Auth.AppAuth(app_id, private_ssh_key).get_installation_auth(
                    app_installation_id
                )
            )
        print(self.gh.get_rate_limit().core.remaining)
        if self.gh.get_rate_limit().core.remaining == 0:
            sys.exit(1)
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

    def get_all_issues(
        self, issue_state: Optional[Literal["open", "closed"]] = None
    ) -> list[Issue]:
        if not issue_state:
            issue_state = self.issue_state

        return self.repo.get_issues(state=issue_state, labels=self.issue_labels or [])

    def get_exact_title_match(
        self, title: str, state: Literal["open", "closed"]
    ) -> list[Issue]:
        all_pipeline_issues = self.get_all_issues(issue_state=state)

        unsorted = [
            issue
            for issue in all_pipeline_issues
            if (issue.title == title or "") and (issue.state == state)
        ]

        sorted_issues = sorted(unsorted, key=lambda issue: issue.number, reverse=True)
        return sorted_issues

    def get_matching_issues(self) -> list[Issue]:
        all_pipeline_issues = self.get_all_issues()

        matching_issues = [
            issue
            for issue in all_pipeline_issues
            if issue.title.startswith(self.issue_prefix or "")
        ]
        return matching_issues

    def fetch_all_versions(self) -> set[ConcourseGithubIssuesVersion]:
        matching_issues = self.get_matching_issues()
        versions = {self._to_version(issue) for issue in matching_issues}
        return versions

    def tombstone_version(
        self, version: ConcourseGithubIssuesVersion, build_metadata: BuildMetadata
    ):
        current_title = self.get_title_from_build(build_metadata)
        job_number = build_metadata.BUILD_NAME
        new_title = f"[CONSUMED #{job_number}]" + current_title
        issue = self.repo.get_issue(int(version.issue_number))

        if issue.state == "closed":
            issue.edit(title=new_title)

    def download_version(
        self,
        version: ConcourseGithubIssuesVersion,
        destination_dir: str,
        build_metadata: BuildMetadata,
    ) -> Tuple[ConcourseGithubIssuesVersion, dict[str, str]]:
        with Path(destination_dir).joinpath("gh_issue.json").open("w") as issue_file:
            issue_file.write(json.dumps(version.to_flat_dict() or {}))
        # We've triggered a deploy and consumed this issue. Set a tombstone in the title
        # so we'll ignore it in future and avoid duplicate triggering.
        self.tombstone_version(version, build_metadata)
        return version, {}

    def get_issue_body_from_build(self, build_metadata: BuildMetadata) -> str:
        return self.issue_body_template.format(**build_metadata_dict(build_metadata))

    def get_title_from_build(self, build_metadata: BuildMetadata) -> str:
        return self.issue_title_template.format(**build_metadata_dict(build_metadata))

    def publish_new_version(
        self,
        sources_dir,
        build_metadata: BuildMetadata,
        assignees: Optional[list[str]] = None,
        labels: Optional[list[str]] = None,
    ) -> Tuple[ConcourseGithubIssuesVersion, dict[str, str]]:
        # Assume that: title is enough uniqueness to discern whether the issue
        # already exists

        candidate_issue_title = self.get_title_from_build(build_metadata)

        already_exists = self.get_exact_title_match(candidate_issue_title, state="open")

        issue_labels = [self.repo.get_label(label) for label in labels or []]

        if len(already_exists) > 1:
            print("Warning: There are multiple matches for the desired issue title!")

        if not already_exists:
            working_issue = self.repo.create_issue(
                title=candidate_issue_title,
                assignees=assignees or [],
                labels=issue_labels,
                body=self.get_issue_body_from_build(build_metadata),
            )
            print(f"created issue: {working_issue=}")
        else:
            working_issue = already_exists[0]
            comment_body = self.get_issue_body_from_build(build_metadata)
            print(f"about to comment on {working_issue=} with {comment_body=}")
            working_issue.create_comment(comment_body)

        return self._to_version(working_issue), {}

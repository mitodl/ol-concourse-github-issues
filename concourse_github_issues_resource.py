from concoursetools.additional import ConcourseResource  # type: ignore
from github import Github, Auth  # type: ignore
from os import environ


class ConcourseGithubIssuesResource(ConcourseResource):
    def __init__(self):
        self.auth = Auth.Token(environ["GITHUB_AUTH_TOKEN"])
        self.gh = Github(auth=self.auth)
        self.repo = self.gh.get_repo("mitodl/pipeline_workflow_repo")
        self.issue_title_prefix = ""
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

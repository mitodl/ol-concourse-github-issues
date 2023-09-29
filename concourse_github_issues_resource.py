from concoursetools.additional import InOnlyConcourseResource  # type: ignore
from github import Github, Auth  # type: ignore
from os import environ


class ConcourseGithubIssuesResource(InOnlyConcourseResource):
    def __init__(self):
        auth = Auth.Token(environ["GITHUB_AUTH_TOKEN"])
        gh = Github(auth=auth)
        repo = gh.get_repo("mitodl/pipeline_workflow_repo")
        repo.get_issues(state="open", labels=["pipeline"])

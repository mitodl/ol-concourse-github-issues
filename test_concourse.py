import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from concourse import (
    ConcourseGithubIssuesResource,
    ConcourseGithubIssuesVersion,
    ISO_8601_FORMAT,
)
from concoursetools.testing import SimpleTestResourceWrapper
from github.Issue import Issue


# Helper function to create mock Issue objects
def create_mock_issue(
    number: int,
    title: str,
    state: str,
    created_at: datetime,
    closed_at: datetime | None = None,
    url: str = "http://example.com/issue",
    labels: list[str] | None = None,
) -> MagicMock:
    mock = MagicMock(spec=Issue)
    mock.number = number
    mock.title = title
    mock.state = state
    mock.created_at = created_at
    mock.closed_at = closed_at
    mock.url = url
    # Mock the labels attribute if needed, PyGithub returns Label objects
    mock_labels = []
    if labels:
        for label_name in labels:
            mock_label = MagicMock()
            mock_label.name = label_name
            mock_labels.append(mock_label)
    mock.labels = mock_labels
    return mock


# Sample datetimes for consistent testing
NOW = datetime.now()
T_MINUS_1 = NOW - timedelta(days=1)
T_MINUS_2 = NOW - timedelta(days=2)
T_MINUS_3 = NOW - timedelta(days=3)

# Mock Issues Data
MOCK_ISSUES_DATA = [
    {
        "number": 1,
        "title": "[bot] Issue 1",
        "state": "closed",
        "created_at": T_MINUS_3,
        "closed_at": T_MINUS_2,
        "labels": ["pipeline"],
    },
    {
        "number": 2,
        "title": "User Issue 2",
        "state": "closed",
        "created_at": T_MINUS_2,
        "closed_at": T_MINUS_1,
        "labels": ["bug"],
    },
    {
        "number": 3,
        "title": "[bot] Issue 3",
        "state": "open",
        "created_at": T_MINUS_1,
        "closed_at": None,
        "labels": ["pipeline", "urgent"],
    },
    {
        "number": 4,
        "title": "User Issue 4",
        "state": "open",
        "created_at": NOW,
        "closed_at": None,
        "labels": [],
    },
]

MOCK_ISSUES = [create_mock_issue(**data) for data in MOCK_ISSUES_DATA]  # type: ignore [arg-type]


@pytest.fixture
def mock_github():
    """Fixture to mock the Github API client and repository."""
    with patch("concourse.Github") as MockGithub:
        mock_gh_instance = MockGithub.return_value
        mock_repo = MagicMock()
        mock_gh_instance.get_repo.return_value = mock_repo
        # Set a default rate limit mock to avoid errors
        mock_rate_limit = MagicMock()
        mock_rate_limit.core.remaining = 5000
        mock_gh_instance.get_rate_limit.return_value = mock_rate_limit
        yield mock_gh_instance, mock_repo


@pytest.mark.parametrize(
    "config_state, config_prefix, expected_issue_numbers",
    [
        ("closed", "[bot]", {1}),  # Only closed issues with prefix
        ("closed", None, {1, 2}),  # All closed issues
        ("open", "[bot]", {3}),  # Only open issues with prefix
        ("open", None, {3, 4}),  # All open issues
    ],
)
def test_fetch_new_versions_no_previous(
    mock_github, config_state, config_prefix, expected_issue_numbers
):
    """Test fetching versions without a previous version."""
    mock_gh_instance, mock_repo = mock_github

    # Filter mock issues based on the expected state for the API call
    api_call_issues = [issue for issue in MOCK_ISSUES if issue.state == config_state]
    mock_repo.get_issues.return_value = api_call_issues

    resource = ConcourseGithubIssuesResource(
        repository="test/repo",
        access_token="dummy_token",
        issue_state=config_state,
        issue_prefix=config_prefix,
    )
    wrapper = SimpleTestResourceWrapper(resource)

    # We pass None as previous_version to fetch_new_versions
    versions = wrapper.fetch_new_versions(None)
    version_numbers = {v.issue_number for v in versions}

    assert version_numbers == expected_issue_numbers
    # Verify get_issues was called with the correct state and no 'since'
    mock_repo.get_issues.assert_called_once_with(
        state=config_state, labels=[], since=None
    )


def test_fetch_new_versions_with_previous_closed(mock_github):
    """Test fetching closed issues newer than a previous closed version."""
    mock_gh_instance, mock_repo = mock_github

    # Previous version corresponds to issue #1 (closed T_MINUS_2)
    previous_version = ConcourseGithubIssuesVersion(
        issue_number=1,
        issue_title="[bot] Issue 1",
        issue_state="closed",
        issue_created_at=T_MINUS_3.strftime(ISO_8601_FORMAT),
        issue_closed_at=T_MINUS_2.strftime(ISO_8601_FORMAT),
        issue_url="http://example.com/issue/1",
    )

    # API should be called with 'since' = closed_at + 1s
    # Replicate the resource logic: parse the string format which drops microseconds
    parsed_closed_at = datetime.strptime(
        previous_version.issue_closed_at,  # type: ignore [arg-type]
        ISO_8601_FORMAT,
    )
    expected_since = parsed_closed_at + timedelta(seconds=1)

    # Mock API to return only issues closed after 'since' (Issue #2)
    api_call_issues = [
        issue
        for issue in MOCK_ISSUES
        if issue.state == "closed" and issue.closed_at >= expected_since
    ]
    mock_repo.get_issues.return_value = api_call_issues

    resource = ConcourseGithubIssuesResource(
        repository="test/repo",
        access_token="dummy_token",
        issue_state="closed",
        issue_prefix=None,  # No prefix filtering for this test
    )
    wrapper = SimpleTestResourceWrapper(resource)

    versions = wrapper.fetch_new_versions(previous_version)
    version_numbers = {v.issue_number for v in versions}

    assert version_numbers == {2}  # Only issue #2 should be newer
    mock_repo.get_issues.assert_called_once_with(
        state="closed", labels=[], since=expected_since
    )


def test_fetch_new_versions_with_previous_open(mock_github):
    """Test fetching open issues newer than a previous open version."""
    mock_gh_instance, mock_repo = mock_github

    # Previous version corresponds to issue #3 (created T_MINUS_1)
    previous_version = ConcourseGithubIssuesVersion(
        issue_number=3,
        issue_title="[bot] Issue 3",
        issue_state="open",
        issue_created_at=T_MINUS_1.strftime(ISO_8601_FORMAT),
        issue_closed_at=None,
        issue_url="http://example.com/issue/3",
    )

    # API should be called with 'since' = created_at + 1s
    # Replicate the resource logic: parse the string format which drops microseconds
    parsed_created_at = datetime.strptime(
        previous_version.issue_created_at, ISO_8601_FORMAT
    )
    expected_since = parsed_created_at + timedelta(seconds=1)

    # Mock API to return only issues created after 'since' (Issue #4)
    api_call_issues = [
        issue
        for issue in MOCK_ISSUES
        if issue.state == "open" and issue.created_at >= expected_since
    ]
    mock_repo.get_issues.return_value = api_call_issues

    resource = ConcourseGithubIssuesResource(
        repository="test/repo",
        access_token="dummy_token",
        issue_state="open",
        issue_prefix=None,  # No prefix filtering
    )
    wrapper = SimpleTestResourceWrapper(resource)

    versions = wrapper.fetch_new_versions(previous_version)
    version_numbers = {v.issue_number for v in versions}

    assert version_numbers == {4}  # Only issue #4 should be newer
    mock_repo.get_issues.assert_called_once_with(
        state="open", labels=[], since=expected_since
    )


def test_fetch_new_versions_with_prefix_and_previous(mock_github):
    """Test fetching with prefix and previous version combined."""
    mock_gh_instance, mock_repo = mock_github

    # Previous version is issue #1 (closed T_MINUS_2)
    previous_version = ConcourseGithubIssuesVersion(
        issue_number=1,
        issue_title="[bot] Issue 1",
        issue_state="closed",
        issue_created_at=T_MINUS_3.strftime(ISO_8601_FORMAT),
        issue_closed_at=T_MINUS_2.strftime(ISO_8601_FORMAT),
        issue_url="http://example.com/issue/1",
    )
    # Replicate the resource logic: parse the string format which drops microseconds
    parsed_closed_at = datetime.strptime(
        previous_version.issue_closed_at,  # type: ignore [arg-type]
        ISO_8601_FORMAT,
    )
    expected_since = parsed_closed_at + timedelta(seconds=1)

    # Mock API returns issue #2 (closed, no prefix) and potentially others
    # if they existed and matched the 'since' criteria.
    # In our MOCK_ISSUES, only #2 is closed after #1.
    api_call_issues = [
        issue
        for issue in MOCK_ISSUES
        if issue.state == "closed" and issue.closed_at >= expected_since
    ]  # This will be just issue #2
    mock_repo.get_issues.return_value = api_call_issues

    resource = ConcourseGithubIssuesResource(
        repository="test/repo",
        access_token="dummy_token",
        issue_state="closed",
        issue_prefix="[bot]",  # Prefix filtering IS enabled
    )
    wrapper = SimpleTestResourceWrapper(resource)

    versions = wrapper.fetch_new_versions(previous_version)
    version_numbers = {v.issue_number for v in versions}

    # Issue #2 is returned by API (newer), but filtered out by prefix.
    assert version_numbers == set()
    mock_repo.get_issues.assert_called_once_with(
        state="closed", labels=[], since=expected_since
    )


def test_fetch_new_versions_limit_old(mock_github):
    """Test that limit_old_versions restricts the number of issues returned."""
    mock_gh_instance, mock_repo = mock_github

    # Create more mock issues to test limiting
    more_mock_issues = [
        create_mock_issue(
            number=i,
            title=f"[bot] Old Issue {i}",
            state="closed",
            created_at=NOW - timedelta(days=10 + i),
            closed_at=NOW - timedelta(days=5 + i),
        )
        for i in range(5, 10)  # Issues 5, 6, 7, 8, 9
    ] + MOCK_ISSUES  # Add existing mocks

    # Sort by closed_at ascending for predictable API return order (PyGithub usually sorts descending)
    # But our internal logic sorts by number ascending after filtering.
    api_call_issues = sorted(
        [issue for issue in more_mock_issues if issue.state == "closed"],
        key=lambda i: i.closed_at,
        reverse=True,  # Simulate typical GitHub API order (newest first)
    )
    mock_repo.get_issues.return_value = api_call_issues

    resource = ConcourseGithubIssuesResource(
        repository="test/repo",
        access_token="dummy_token",
        issue_state="closed",
        issue_prefix="[bot]",
        limit_old_versions=2,  # Limit to 2 oldest matching issues
    )
    wrapper = SimpleTestResourceWrapper(resource)

    versions = wrapper.fetch_new_versions(None)  # No previous version
    version_numbers = {v.issue_number for v in versions}

    # Expected: Issues 1, 5, 6, 7, 8, 9 match state and prefix.
    # get_matching_issues sorts by number ascending: 1, 5, 6, 7, 8, 9
    # limit_old_versions=2 takes the first 2: 1, 5
    assert version_numbers == {1, 5}
    mock_repo.get_issues.assert_called_once_with(state="closed", labels=[], since=None)


# TODO: Add tests for download_version (tombstoning) and publish_new_version (creation/commenting)
# These would require mocking issue.edit(), issue.create_comment(), repo.create_issue(), gh.search_issues() etc.

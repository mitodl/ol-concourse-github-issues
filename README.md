# ol-concourse-github-issues
A Concourse resource to manipulate Github Issues

# To install (TODO: MORE DETAIL NEEDED)

You can find the resource on [dockerhub](https://hub.docker.com/r/mitodl/ol-concourse-github-issues)

# To use:

Your pipeline should include a source block like:

```
access_token: Github access token
repository: Github repo in which to detect / create issues
issue_state: One of "open" or "closed". Defaults to "closed"
issue_prefix: prefix issue titles must contain to match.
labels: labels required to match.
assignees: optional assignees list to use when creating issues
```

You can find example pipeline definitions for:

- [Triggering a task when a Github issue is created](trigger_test_pipeline.yaml)
- [Creating a New Github Issue When A Task
Completes](issue_create_test_pipeline.yaml)

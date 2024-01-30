# ol-concourse-github-issues
A Concourse resource to manipulate Github Issues

## Install (TODO: MORE DETAIL NEEDED)

You can find the resource on [dockerhub](https://hub.docker.com/r/mitodl/ol-concourse-github-issues)

## Usage

Your pipeline should include a source block like:

```
auth_method: "app" or "token". Defaults to token if not specified
access_token: a personal Github access token. Required if auth method == app
app_id: a Github application ID. Required if auth method == app
app_installation_id: a Github application installation ID. Required if auth_method == app
private_ssh_key: The complete application RSA key generated for a Github application. Required if auth_method == app
repository: Github repo in which to detect / create issues
issue_state: One of "open" or "closed". Defaults to "closed"
issue_prefix: prefix issue titles must contain to match
labels: labels required to match
assignees: optional assignees list to use when creating issues
```

You can find example pipeline definitions for:

- [Triggering a task when a Github issue is created](trigger_test_pipeline.yaml)
- [Creating a New Github Issue When A Task
Completes](issue_create_test_pipeline.yaml)

## App / Token Permissions

- Token: `project, read:org, repo`
- Application Installation: `Repository->Contents->Read and Write`, `Respository->Issues->Read and Write`, `Repository->Metadata->Read-only` and `Repository->Pull requests->Read and Write`

Documentation on setting up a personal access token can be found [here](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app)
Documentation on setting up a github application can be found [here](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app), [here](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation) and [here](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps)

## Building

With Docker:
```
docker build --platform=linux/amd64 .
```

With Earthly:

On Apple Silicon, first follow instructions [here](https://docs.earthly.dev/docs/guides/multi-platform#apple-silicon-m1-and-m2-processors)
```
earthly --platform=linux/amd64 +build
```

## Testing

```
poetry install
poetry run python3 -m concoursetools . -r concourse.py
check < payload.json
```

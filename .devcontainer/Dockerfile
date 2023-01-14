# syntax=docker/dockerfile:1
# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.241.1/containers/ubuntu/.devcontainer/base.Dockerfile

# [Choice] Ubuntu version (use ubuntu-22.04 or ubuntu-18.04 on local arm64/Apple Silicon): ubuntu-22.04, ubuntu-20.04, ubuntu-18.04
# ARG VARIANT="jammy"
# FROM mcr.microsoft.com/vscode/devcontainers/base:0-${VARIANT}
# Change this dockerfile later, amazonlinux?
FROM mcr.microsoft.com/playwright:v1.28.0-focal

# [Optional] Uncomment this section to install additional OS packages.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends python3 python3-pip

RUN python3 -m pip install playwright pytest pytest-playwright beautifulsoup4 ffmpeg-python requests_mock pyyaml

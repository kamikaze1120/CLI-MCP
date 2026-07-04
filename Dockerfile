# =============================================================================
# cli-mcp-tools — Pre-built Docker image with all common CLI tools
# =============================================================================
# Build:   docker build -t cli-mcp-tools:latest .
#          (or from an installed package: cli-mcp --build-image)
# =============================================================================

FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=development
# Ubuntu 24.04 marks the system Python as externally managed (PEP 668);
# this image is a disposable sandbox, so global pip installs are fine.
ENV PIP_BREAK_SYSTEM_PACKAGES=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── Layer 1: Core system packages ────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    lsb-release \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 2: Dev tools & utilities ───────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Version control
    git \
    # Shell utilities
    bash \
    zsh \
    fish \
    tmux \
    vim \
    nano \
    less \
    # File tools
    tar \
    gzip \
    zip \
    unzip \
    # Network
    netcat-openbsd \
    dnsutils \
    iputils-ping \
    # Search
    ripgrep \
    fd-find \
    # Processing
    jq \
    yq \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    # Auth
    openssh-client \
    # SSL
    openssl \
    # Other
    time \
    tree \
    htop \
    && rm -rf /var/lib/apt/lists/* \
    # Ubuntu packages fd as 'fdfind'; expose it under its upstream name too
    && ln -s "$(command -v fdfind)" /usr/local/bin/fd

# ── Layer 3: Node.js 22 LTS ──────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g npm@latest

# ── Layer 4: Python 3 & tools ────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir \
        virtualenv \
        uv

# ── Layer 5: GitHub CLI ──────────────────────────────────────────────────────
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 6: AWS CLI v2 ──────────────────────────────────────────────────────
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp/aws \
    && /tmp/aws/aws/install \
    && rm -rf /tmp/aws /tmp/awscliv2.zip

# ── Layer 7: Google Cloud SDK ────────────────────────────────────────────────
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update \
    && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 8: Docker CLI ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    docker-compose-v2 \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 9: Additional language runtimes ────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    golang-go \
    rustc \
    cargo \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 10: Cleanup ────────────────────────────────────────────────────────
RUN apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/pip

WORKDIR /workspace
CMD ["sleep", "infinity"]

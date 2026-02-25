# Cursor Cloud Agent Dockerfile for Pro-Spectus
# Rails 8.1.1 + PostgreSQL + Redis + Node.js environment

FROM ruby:3.4.7-slim-bookworm

# Set environment variables
ENV RAILS_ENV=development \
    RACK_ENV=development \
    SENTRY_ENV=cursor-cloud-agent \
    BUNDLE_JOBS=4 \
    BUNDLE_RETRY=3 \
    NODE_MAJOR=20 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install base dependencies first (needed for adding repos)
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Add PostgreSQL 18 official repository
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list

# Install system dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    git \
    # PostgreSQL 18 server and client
    postgresql-18 \
    postgresql-contrib \
    libpq-dev \
    # Redis server
    redis-server \
    # For image processing (if needed)
    libvips-dev \
    # For nokogiri
    libxml2-dev \
    libxslt1-dev \
    # For psych (YAML parser)
    libyaml-dev \
    # Chrome for system tests
    chromium \
    chromium-driver \
    # Misc utilities
    jq \
    sudo \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Configure PostgreSQL 18 to allow local connections without password
RUN echo "local all all trust" > /etc/postgresql/18/main/pg_hba.conf && \
    echo "host all all 127.0.0.1/32 trust" >> /etc/postgresql/18/main/pg_hba.conf && \
    echo "host all all ::1/128 trust" >> /etc/postgresql/18/main/pg_hba.conf

# Install Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Set Chrome/Chromium environment for headless testing
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install bundler
RUN gem install bundler

# Create non-root user with sudo access
RUN useradd -m -s /bin/bash agent && \
    echo "agent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Make bundle directory writable by agent user
RUN chown -R agent:agent /usr/local/bundle

# Switch to non-root user
USER agent
WORKDIR /home/agent

# Default command
CMD ["bash"]
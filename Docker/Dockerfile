FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    bats \
    curl \
    git \
    jq \
    procps \
    python3-minimal \
    python3-pip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && apt-get clean \
    && useradd -m -u 1000 -s /bin/bash gandalf

USER gandalf
WORKDIR /app

COPY --chown=gandalf:gandalf gandalf/ gandalf/
COPY --chown=gandalf:gandalf zsh/ zsh/
COPY --chown=gandalf:gandalf scripts/ scripts/

RUN chmod +x gandalf/gandalf \
    && mkdir -p /home/gandalf/.local/bin \
    && ln -s /app/gandalf/gandalf /home/gandalf/.local/bin/gandalf \
    && echo '#!/bin/bash' > /home/gandalf/.local/bin/gdlf \
    && echo 'exec /app/gandalf/gandalf "$@"' >> /home/gandalf/.local/bin/gdlf \
    && chmod +x /home/gandalf/.local/bin/gdlf

# Install Python dependencies for MCP server
USER root
RUN cd /app/gandalf/server && pip3 install --no-cache-dir -e .
USER gandalf

ENV GANDALF_ROOT=/app/gandalf \
    PATH="/home/gandalf/.local/bin:$PATH" \
    TERM=xterm-256color \
    PYTHONPATH="/app/gandalf/server" \
    TZ=America/Los_Angeles

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["gdlf test --shell"] 
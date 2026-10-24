FROM docker.io/library/ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential clang lld flex bison gawk gcc-multilib g++-multilib \
    gettext git libncurses-dev libssl-dev python3 python3-setuptools \
    python3-pyelftools python3-yaml rsync swig unzip zlib1g-dev file wget \
    curl ca-certificates ccache cmake ninja-build pkgconf patch subversion \
    time xsltproc zstd libelf-dev libfuse-dev shellcheck jq \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 builder \
    && mkdir -p /work /workspace && chown builder:builder /work
COPY configs /workspace/configs
COPY scripts /workspace/scripts
COPY files /workspace/files
COPY package /workspace/package
COPY tests /workspace/tests
USER builder
WORKDIR /work
CMD ["sleep", "infinity"]

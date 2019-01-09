# Docker image for installing dependencies on Linux and running tests.
# Build with:
# docker build --tag=mapview-linux .
# Run with:
# docker run mapview-linux /bin/sh -c 'tox'
# Or for interactive shell:
# docker run -it --rm mapview-linux
FROM ubuntu:18.04

# configure locale
RUN apt update -qq > /dev/null && apt install --yes --no-install-recommends \
    locales && \
    locale-gen en_US.UTF-8
ENV LANG="en_US.UTF-8" \
    LANGUAGE="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8"

# install system dependencies
RUN apt update -qq > /dev/null && apt install --yes --no-install-recommends \
	python2.7-minimal libpython2.7-dev virtualenv make lsb-release pkg-config git build-essential \
    sudo libssl-dev tox

# install kivy system dependencies
# https://kivy.org/docs/installation/installation-linux.html#dependencies-with-sdl2
RUN apt install --yes --no-install-recommends \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

WORKDIR /app
COPY . /app

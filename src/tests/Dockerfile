ARG IMAGE=python:3.12.2-slim-bullseye
FROM $IMAGE

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /work
ENV HOME=/work

COPY tests/requirements.txt /work
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /work/requirements.txt

COPY spctrl /work/modules/spctrl/
COPY tests /work/tests
ENV PYTHONPATH=/work/modules

ARG BUILD_VERSION
RUN echo "${BUILD_VERSION}" > /build_version.txt

COPY tests/entrypoint /entrypoint
ENTRYPOINT [ "/entrypoint" ]

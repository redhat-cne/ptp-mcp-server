# PTP MCP Server Dockerfile
# Builds a container for running the PTP MCP Server in HTTP mode
# for integration with OpenShift Lightspeed

FROM registry.access.redhat.com/ubi9/python-312:latest

LABEL name="ptp-mcp-server" \
      version="1.0.0" \
      description="MCP Server for OpenShift PTP monitoring and analysis" \
      maintainer="Red Hat"

USER root

# Install OpenShift CLI (oc)
# The server uses 'oc' commands to query PTP configs, logs, and execute PMC queries
ARG OC_VERSION=4.20.0
RUN curl -sSL "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OC_VERSION}/openshift-client-linux.tar.gz" \
    | tar -xzf - -C /usr/local/bin oc kubectl && \
    chmod +x /usr/local/bin/oc /usr/local/bin/kubectl && \
    oc version --client

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Switch back to non-root user (default UID in UBI Python image)
USER 1001

# Environment variables with defaults
# Note: When running in OpenShift, the ServiceAccount token is automatically
# mounted at /var/run/secrets/kubernetes.io/serviceaccount/ and oc will use it
ENV PTP_MCP_PORT=8080 \
    PTP_MCP_HOST=0.0.0.0 \
    PTP_NAMESPACE=openshift-ptp \
    PTP_DAEMON_NAME=linuxptp-daemon \
    PTP_CONTAINER_NAME=linuxptp-daemon-container \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

# Expose the default port (can be overridden via PTP_MCP_PORT)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${PTP_MCP_PORT}/health')\"" || exit 1

# Run the server in HTTP mode
# Port can be configured via PTP_MCP_PORT environment variable
CMD ["python", "ptp_mcp_server.py", "--http"]

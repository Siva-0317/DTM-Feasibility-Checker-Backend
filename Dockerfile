FROM mambaorg/micromamba:1.5-bullseye-slim

# Copy environment file
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml

# Install dependencies using micromamba
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

# Copy the rest of the application
COPY --chown=$MAMBA_USER:$MAMBA_USER . /app
WORKDIR /app

# Expose port (Render sets PORT env variable, defaulting to 10000 if not set)
ENV PORT=8000
EXPOSE 8000

# Start Uvicorn using the conda environment
CMD ["micromamba", "run", "-n", "base", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

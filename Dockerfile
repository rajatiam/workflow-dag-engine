FROM python:3.13-slim
WORKDIR /app
COPY workflow_dag_engine ./workflow_dag_engine
RUN useradd --uid 10001 --create-home runner
USER runner
WORKDIR /workspace
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "workflow_dag_engine"]
CMD ["--help"]

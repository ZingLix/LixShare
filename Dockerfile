FROM python:3.9.5-slim
RUN pip install fastapi uvicorn pymongo pyyaml markdown jinja2
WORKDIR /project
COPY src /project
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]

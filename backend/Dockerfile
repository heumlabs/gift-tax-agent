# Lambda Container Image for Chalice App
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY app.py ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY .chalice ${LAMBDA_TASK_ROOT}/.chalice/

# Copy chalicelib directory
COPY chalicelib ${LAMBDA_TASK_ROOT}/chalicelib/

# Lambda handler for Chalice Container Image
CMD ["lambda_handler.handler"]


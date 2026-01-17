FROM astral/uv:python3.13-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

CMD ["uv", "run", "bot.py"]
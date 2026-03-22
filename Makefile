.PHONY: setup install run test clean ingest

# First-time setup
setup:
	python -m venv .venv
	@echo "Virtual environment created."
	@echo "Run: source .venv/bin/activate  (Linux/Mac)"
	@echo "Run: .venv\\Scripts\\activate   (Windows)"
	@echo "Then run: make install"

# Install all dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm
	@echo ""
	@echo "================================================"
	@echo "  Setup complete!"
	@echo "  1. Copy .env.example to .env"
	@echo "  2. Add your Gemini API key"
	@echo "  3. Run: make ingest"
	@echo "  4. Run: make run"
	@echo "================================================"

# Ingest clause library into vector store
ingest:
	python -m src.rag.store

# Run the Streamlit dashboard
run:
	streamlit run app/streamlit_app.py --server.port 8501

# Run tests
test:
	pytest tests/ -v --tb=short

# Clean generated files
clean:
	rm -rf data/vectorstore/*
	rm -rf data/outputs/*
	rm -rf __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
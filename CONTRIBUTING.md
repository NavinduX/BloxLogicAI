# Contributing to BloxLogicAI

First off, thank you for considering contributing to BloxLogicAI! It's people like you that make BloxLogicAI such a great tool for the Sri Lankan Tea Industry.

## How Can I Contribute?

### Reporting Bugs
If you find a bug in the source code, you can help us by submitting an issue to our GitHub Repository. Even better, you can submit a Pull Request with a fix. Please use the Bug Report template when opening an issue.

### Suggesting Enhancements
If you have a great idea for a new feature or an improvement to our AI models, submit an issue and tag it as an `enhancement`.

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests to the `tests/` directory.
3. If you've changed the UI or logic, please update the documentation.
4. Ensure the test suite passes (`pytest tests/`).
5. Make sure your code is clean and properly commented.
6. Submit that pull request!

## Local Development Setup

1. Clone the repository: 
   ```bash
   git clone https://github.com/nalantishantha/BloxLogicAI.git
   ```
2. Create a virtual environment: 
   ```bash
   python -m venv venv
   ```
3. Activate the environment and install dependencies: 
   ```bash
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```
4. Run the app: 
   ```bash
   streamlit run app/main.py
   ```

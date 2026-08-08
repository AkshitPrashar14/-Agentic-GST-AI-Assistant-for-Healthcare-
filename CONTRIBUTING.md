# Contributing to Agentic GST AI Assistant

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/agentic_ai.git
   cd agentic_ai
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

1. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up frontend**:
   ```bash
   cd frontend
   npm install
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your HuggingFace token
   ```

## Code Style

- **Python**: Follow PEP 8 style guide
- **JavaScript/React**: Follow ESLint configuration
- **Comments**: Add docstrings for functions and classes
- **Naming**: Use descriptive variable and function names

## Making Changes

1. **Make your changes** in a feature branch
2. **Test thoroughly**:
   - Test backend API endpoints
   - Test frontend UI components
   - Test agentic features (planning, tools, memory, reflection)
3. **Update documentation** if needed
4. **Commit with clear messages**:
   ```bash
   git commit -m "Add: Feature description"
   ```

## Commit Message Format

- `Add:` for new features
- `Fix:` for bug fixes
- `Update:` for updates to existing features
- `Refactor:` for code refactoring
- `Docs:` for documentation changes

## Pull Request Process

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub
3. **Describe your changes** clearly:
   - What changed?
   - Why did it change?
   - How was it tested?

4. **Wait for review** and address any feedback

## Areas for Contribution

- 🐛 **Bug fixes**: Report and fix issues
- ✨ **New features**: Add new agentic capabilities
- 📚 **Documentation**: Improve README, add examples
- 🎨 **UI/UX**: Enhance the React frontend
- ⚡ **Performance**: Optimize search, embeddings, or API calls
- 🧪 **Testing**: Add unit tests or integration tests

## ❓ Questions

Open an issue on GitHub for questions or discussions.

Thank you for contributing! 🎉


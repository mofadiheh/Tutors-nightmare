# Language-Learning Chatbot

A text-only chatbot web app for language learning with AI-powered tutoring, built to run on Replit.

## Current Status

**✓ Milestone A Complete** — Project Skeleton + Deployed "Hello"
- FastAPI backend with uvicorn
- `/health` endpoint returning `{ "ok": true }`
- Simple static page calling `/health`
- Replit configuration files ready

## Features (Planned)

- **Chat mode**: Interactive conversations with AI language tutor
- **Language toggle**: Switch display language with full chat history translation
- **Insights mode**: Track important words and sentence structures
- **Home page**: 5 topic starters to begin conversations

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Database**: SQLite (coming in Milestone C)
- **Hosting**: Replit (configured for free tier)

## Local Development

### Prerequisites

- Python 3.9 or higher
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/mofadiheh/Tutors-nightmare.git
   cd Tutors-nightmare
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

4. Open your browser to: `http://localhost:8000`

### Testing the Health Endpoint

Visit `http://localhost:8000/health` to see:
```json
{"ok": true}
```

## Deploying to Replit

1. Create a new Replit project
2. Push this repository to GitHub
3. Import the GitHub repository to Replit
4. Replit will automatically detect the configuration from `.replit` and `replit.nix`
5. Click "Run" - the app will start on port 8000
6. Replit will provide a public URL

## Project Structure

```
.
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── .replit             # Replit run configuration
├── replit.nix          # Replit environment setup
├── static/             # Static files (HTML, CSS, JS)
│   ├── index.html      # Main page
│   ├── style.css       # Styling
│   └── app.js          # Frontend JavaScript
├── dev_plan.md         # Detailed development roadmap
└── README.md           # This file
```

## Development Roadmap

See [dev_plan.md](dev_plan.md) for the complete development plan with milestones:

- [x] **Milestone A**: Project Skeleton + Deployed "Hello"
- [ ] **Milestone B**: Chat UI + Stubbed Backend
- [ ] **Milestone C**: Persistence with SQLite
- [ ] **Milestone D**: LLM Integration
- [ ] **Milestone E**: Language Toggle
- [ ] **Milestone F**: Insights Mode
- [ ] **Milestone G**: Home Page + Topic Starters
- [ ] **Milestone H**: Hardening + Beta Polish

## Contributing

This project is under active development. Feel free to open issues or submit pull requests.

## License

MIT

# PR Review Agent - Frontend

> **Part of**: [samay2504/PR-reviewer-Tool](https://github.com/samay2504/PR-reviewer-Tool)

A minimalist, production-ready static frontend for the PR Review Agent with a sleek black/white/red aesthetic. This single-page application allows users to analyze GitHub pull requests using AI-powered agents for security, performance, and style checks.

**Live Demo**: [https://samay2504.github.io/PR-reviewer-Tool/](https://samay2504.github.io/PR-reviewer-Tool/)

## ✨ Features

- **Multiple Input Methods**:
  - GitHub PR URL (e.g., `https://github.com/facebook/react/pull/31000`)
  - Repository + PR number (e.g., `django/django` + `20316`)
  - Raw diff text (paste git diff output)

- **Smart Analysis**:
  - Security vulnerability detection
  - Performance optimization suggestions
  - Style and readability improvements
  - Executive summaries with merge recommendations

- **Beautiful UI**:
  - Black/white/red color palette
  - Fully responsive (mobile, tablet, desktop)
  - Keyboard accessible (WCAG AA compliant)
  - Smooth animations and micro-interactions

- **Developer-Friendly**:
  - Configurable API endpoint
  - Demo mode with sample data
  - Download results as JSON
  - Copy markdown summaries
  - Client-side caching

## 🚀 Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   cd web-frontend
   npm install
   ```

2. **Configure API endpoint** (edit `public/config.json`):
   ```json
   {
     "API_BASE": "http://localhost:8000",
     "ALLOW_POST_FROM_UI": false,
     "DEMO_MODE": false
   }
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Open in browser**: http://localhost:3000

### Production Build

```bash
npm run build
```

The built files will be in the `dist/` directory, ready for deployment.

## 📦 Deployment to GitHub Pages

### Automatic Deployment

This project includes a GitHub Actions workflow that automatically deploys to GitHub Pages when you push to `main`.

#### Setup Steps:

1. **Enable GitHub Pages** in your repository:
   - Go to Settings → Pages
   - Source: "GitHub Actions"

2. **Update API base URL** in `public/config.json`:
   ```json
   {
     "API_BASE": "https://your-backend.example.com",
     "ALLOW_POST_FROM_UI": false
   }
   ```

3. **Push to main branch**:
   ```bash
   git add .
   git commit -m "Deploy frontend"
   git push origin main
   ```

4. **Access your site**: `https://[username].github.io/[repo-name]/`

### Manual Deployment

```bash
npm run deploy
```

This builds and deploys to the `gh-pages` branch.

## ⚙️ Configuration

### `public/config.json`

This file controls frontend behavior at runtime:

```json
{
  "API_BASE": "http://localhost:8000",
  "ALLOW_POST_FROM_UI": false,
  "DEMO_MODE": false
}
```

**Options**:
- `API_BASE`: Backend API URL (required)
- `ALLOW_POST_FROM_UI`: Enable comment posting (default: false)
- `DEMO_MODE`: Load sample data by default (default: false)

**Important**: Update `API_BASE` before deploying to production!

## 🔒 CORS Configuration

If you encounter CORS errors, you need to configure the backend to allow requests from your frontend origin.

### Backend CORS Setup

The backend (`src/pr_agent/api/main.py`) must whitelist your frontend URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-username.github.io"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Note**: This is a **backend-only** configuration. Do NOT attempt to modify CORS from the frontend.

### Common CORS Issues

**Error**: `Failed to fetch` or `NetworkError`

**Solution**: 
1. Verify backend is running
2. Check `API_BASE` in `config.json` is correct
3. Ensure backend CORS settings allow your frontend origin
4. Contact backend administrator to whitelist your domain

## 📖 API Contract

The frontend expects the backend to provide:

### POST /analyze

**Request**:
```json
{
  "repo": "facebook/react",        // optional
  "pr_number": 31000,               // optional
  "diff_text": "...",               // optional
  "use_cache": true                 // optional, default: true
}
```

**Response**:
```json
{
  "request_id": "...",
  "repo": "facebook/react",
  "pr_number": 31000,
  "diff_hash": "...",
  "cached": false,
  "provider": "groq_llama-3.1-8b-instant",
  "comments": [
    {
      "file": "src/component.js",
      "line_start": 10,
      "line_end": 15,
      "severity": "HIGH",
      "category": "SECURITY",
      "message": "...",
      "suggestion_patch": "...",
      "agent": "security"
    }
  ],
  "summary": {
    "total_comments": 5,
    "total_files": 3,
    "executive_summary": "...",
    "recommendation": "REQUEST_CHANGES",
    "statistics": {
      "severity_counts": {
        "critical": 0,
        "high": 2,
        "medium": 2,
        "low": 1
      }
    }
  }
}
```

## 🎨 Customization

### Color Palette

Edit `src/styles/main.css` CSS variables:

```css
:root {
  --bg: #000000;           /* Background */
  --fg: #ffffff;           /* Foreground text */
  --accent: #E10600;       /* Primary accent (red) */
  --accent-hover: #B10500; /* Hover state */
  --accent-active: #8F0400; /* Active state */
  --muted: #666666;        /* Muted text */
  --card-bg: #0a0a0a;      /* Card backgrounds */
  --card-border: #1a1a1a;  /* Borders */
}
```

### Severity Colors

```css
--severity-critical: #E10600; /* Critical issues */
--severity-high: #E10600;     /* High priority */
--severity-medium: #ffb020;   /* Medium priority */
--severity-low: #666666;      /* Low priority */
```

## 🧪 Testing

### Unit Tests

```bash
npm run test
```

Tests are written with Vitest and cover:
- Input parsing logic
- GitHub URL construction
- Storage utilities

### E2E Tests

```bash
npm run test:e2e
```

End-to-end tests with Playwright ensure critical user flows work correctly.

## 📁 Project Structure

```
web-frontend/
├── index.html                    # Entry point
├── public/
│   └── config.json              # Runtime configuration
├── samples/
│   └── sample_analysis.json     # Demo data
├── src/
│   ├── main.jsx                 # React entry
│   ├── App.jsx                  # Main application
│   ├── components/
│   │   ├── InputCard.jsx        # PR input form
│   │   ├── ResultsPanel.jsx     # Analysis results
│   │   ├── IssueItem.jsx        # Individual issue card
│   │   ├── CodeViewer.jsx       # Code diff viewer
│   │   ├── Spinner.jsx          # Loading spinner
│   │   └── Toast.jsx            # Toast notifications
│   ├── styles/
│   │   └── main.css             # Global styles
│   ├── api/
│   │   └── client.js            # Backend API calls
│   └── utils/
│       ├── parseInput.js        # Input parsing
│       ├── githubUrl.js         # GitHub URL builder
│       └── storage.js           # Session storage
├── package.json
├── vite.config.js
└── README.md
```

## 🚨 Important Notes

### Backend Integration

**This frontend does NOT modify any backend code**. It is designed to work with the existing PR Review Agent backend as-is.

If you need backend changes (like CORS configuration or new endpoints), contact the backend maintainer or create a separate backend issue.

### Security

- GitHub tokens are NEVER stored in localStorage
- Tokens are only kept in sessionStorage during active session
- All API calls use secure HTTPS in production
- Input is sanitized to prevent XSS

### Performance

- Lazy-loaded components
- Code-split vendor bundles
- Optimized for < 100KB initial bundle
- Responsive images and icons

## 🐛 Troubleshooting

### "Failed to fetch" Error

- **Check**: Backend is running and accessible
- **Check**: `API_BASE` in `config.json` is correct
- **Check**: CORS is configured on backend

### Blank Page After Deployment

- **Check**: `base` path in `vite.config.js`
- **Check**: GitHub Pages is enabled
- **Check**: Deployment workflow succeeded

### Demo Button Not Working

- **Check**: `samples/sample_analysis.json` exists
- **Check**: File is valid JSON
- **Check**: Browser console for errors

## 📝 License

MIT License - see root LICENSE file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes (frontend only!)
4. Test thoroughly
5. Submit a pull request

## 📞 Support

- **Repository**: [samay2504/PR-reviewer-Tool](https://github.com/samay2504/PR-reviewer-Tool)
- **Issues**: [GitHub Issues](https://github.com/samay2504/PR-reviewer-Tool/issues)
- **Discussions**: [GitHub Discussions](https://github.com/samay2504/PR-reviewer-Tool/discussions)
- **Live Frontend**: [https://samay2504.github.io/PR-reviewer-Tool/](https://samay2504.github.io/PR-reviewer-Tool/)

---

**Built with**: React 18, Vite 5, and ❤️ for clean code

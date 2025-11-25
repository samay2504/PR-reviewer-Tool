# Changelog

All notable changes to the frontend will be documented in this file.

## [1.0.0] - 2025-11-25

### Added
- Initial frontend release with black/white/red aesthetic
- Multiple input modes: PR URL, repo + PR number, raw diff
- Interactive analysis results with filtering and search
- Severity-based issue categorization (Critical, High, Medium, Low)
- Executive summaries with AI-generated insights
- Merge recommendation display
- GitHub file link generation for issues
- Copy-to-clipboard for patches and summaries
- Download results as JSON
- Demo mode with sample data
- Configurable API endpoint via public/config.json
- Fully responsive design (mobile, tablet, desktop)
- WCAG AA accessibility compliance
- Loading states with cancellable requests
- Toast notifications for user feedback
- GitHub Actions workflow for automatic deployment
- Comprehensive README with deployment instructions

### Backend Integration
- **No backend files were modified**
- Frontend adapts to existing backend API contract
- CORS requirements documented for backend administrator
- Session-only token storage for security

### Technical Stack
- React 18.2.0
- Vite 5.0.8 for build tooling
- Prism.js for syntax highlighting
- Zero external UI libraries (custom CSS)
- < 100KB initial bundle size

### Security
- No localStorage for sensitive data
- sessionStorage only for temporary tokens
- Input sanitization to prevent XSS
- Secure HTTPS in production

### Performance
- Code-split vendor bundles
- Lazy-loaded components
- Optimized asset loading
- Client-side caching support

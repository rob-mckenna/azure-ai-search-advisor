# Screenshot Placeholders

This directory contains UI screenshots for the user guide. To generate them:

## Required screenshots

| File | Description | How to capture |
|------|-------------|----------------|
| `chat-ui-overview.png` | Full UI with header, chat area, and quick actions visible | Open UI at localhost:5173 in Local API mode, capture full browser window |
| `chat-ui-layout.png` | Annotated layout showing header, chat area, and input bar | Same as above with annotation arrows |
| `quick-actions.png` | Close-up of the three quick action buttons | Crop the button area from the chat UI |
| `welcome-screen.png` | Initial state with assistant greeting message | Fresh page load before any interaction |
| `analysis-results.png` | Chat showing analysis response with findings | Click "Analyze sample service", capture the response |
| `recommendations.png` | Chat showing recommendation cards | Click "Get recommendations" after analysis |
| `cost-simulation.png` | Chat showing cost comparison (current vs. projected) | Click "Cost simulation" after analysis |
| `severity-scale.png` | Visual showing the 5 severity levels with colors | Create graphic or capture from a response with mixed severities |

## How to generate

1. Start the API: `python -m uvicorn azure_ai_search_advisor.main:app --reload`
2. Start the UI: `cd ui && npm run dev`
3. Open `http://localhost:5173` in a browser
4. Use browser DevTools to set viewport to 1280x800 for consistent sizing
5. Capture using your OS screenshot tool or a browser extension

## Tips

- Use a clean browser profile (no extensions visible)
- Set system theme to light mode for readability
- Ensure the terminal/other windows don't bleed through
- Crop to content — no unnecessary browser chrome

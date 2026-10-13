"""Enveloppe le fragment de cartes dans un conteneur HTML compatible mail."""
from datetime import datetime


_CSS = """
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.5;
      color: #1f2937;
      background-color: #f3f4f6;
      margin: 0;
      padding: 20px;
    }
    .wrapper {
      max-width: 680px;
      margin: 0 auto;
      background-color: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
    }
    .header {
      background-color: #0f172a;
      color: #ffffff;
      padding: 24px;
    }
    .header h1 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      letter-spacing: -0.025em;
    }
    .header p {
      margin: 4px 0 0;
      font-size: 13px;
      color: #94a3b8;
    }
    .content {
      padding: 24px;
    }
    .article-card {
      margin-bottom: 20px;
      padding: 16px;
      background-color: #f8fafc;
      border: 1px solid #e2e8f0;
      border-left: 4px solid #2563eb;
      border-radius: 4px;
    }
    .article-card:last-child {
      margin-bottom: 0;
    }
    .article-title {
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 8px;
    }
    .article-title a {
      color: #1d4ed8;
      text-decoration: none;
    }
    .article-title a:hover {
      text-decoration: underline;
    }
    ul {
      margin: 8px 0 0;
      padding-left: 20px;
    }
    li {
      margin-bottom: 4px;
      font-size: 13px;
      color: #334155;
    }
    li strong {
      color: #0f172a;
    }
    .footer {
      padding: 16px 24px;
      background-color: #f8fafc;
      border-top: 1px solid #e2e8f0;
      font-size: 11px;
      color: #64748b;
      text-align: center;
    }
"""


def render_cards(config: dict, body_content: str) -> str:
    """Construit le document HTML complet autour des cartes triées."""
    name = config.get("name", "Veille")
    date_str = datetime.now().strftime("%d/%m/%Y")

    return

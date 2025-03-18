# GitHub Copilot Metrics Dashboard

A Streamlit application that provides a visual dashboard for GitHub Copilot usage metrics across your organization and teams.

![Dashboard Screenshot](https://via.placeholder.com/800x450?text=GitHub+Copilot+Metrics+Dashboard)

## 🌟 Overview

This project addresses the lack of a dedicated interface for GitHub Copilot's metrics API. Organizations investing in GitHub Copilot need data to evaluate its adoption, effectiveness, and return on investment. This dashboard provides actionable insights on how developers are utilizing AI pair programming tools across your organization.

## ✨ Features

- **Organization and Team Level Metrics**: View metrics for your entire organization or specific teams
- **Time-based Filtering**: Filter data by month or specific days
- **Key Performance Indicators**:
  - Active and engaged users
  - IDE chat usage statistics
  - Code suggestions and acceptance rates
  - Language-specific metrics and trends
  - Editor-specific usage patterns
- **Interactive Visualizations**:
  - Daily chat usage trends
  - Daily code acceptance rates
  - Language usage and acceptance rates
  - Editor usage statistics

## 🚀 Getting Started

### Prerequisites

- A GitHub organization with Copilot enabled
- Admin access to the organization (to access Copilot metrics)
- GitHub Personal Access Token with `admin:org` scope

### Required Environment Variables

For all deployment methods, the following environment variables are required:

- `GITHUB_TOKEN`: Your GitHub Personal Access Token with `admin:org` scope
- `ORG_SLUG`: Your GitHub organization name

### Running with Docker

Run the dashboard using the pre-built Docker image:

```bash
docker run -p 8501:8501 \
  -e GITHUB_TOKEN="your_github_personal_access_token" \
  -e ORG_SLUG="your_organization_name" \
  -v /path/to/local/storage:/app/data \
  prima101112/github-copilot-report:latest
```

Access the dashboard at `http://localhost:8501`.

### Running on Kubernetes

1. Create a secret for your GitHub token:

```bash
kubectl create secret generic copilot-metrics-secret \
  --from-literal=GITHUB_TOKEN="your_github_personal_access_token"
```

2. Apply the existing Kubernetes configuration:

```bash
kubectl apply -f github-copilot-report.yaml
```

3. To access the dashboard, set up port forwarding:

```bash
kubectl port-forward service/github-copilot-report 8501:8501
```

Visit `http://localhost:8501` in your browser.

### Running Locally

If you prefer to run the application locally:

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/github-metrics-streamlit.git
   cd github-metrics-streamlit
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   export GITHUB_TOKEN="your_github_personal_access_token"
   export ORG_SLUG="your_organization_name"
   export DB_PATH="/path/to/database/directory"  # Optional, defaults to current directory
   ```

4. Launch the Streamlit app:
   ```bash
   streamlit run permonth.py
   ```

   The dashboard will be available at `http://localhost:8501`.

## 💾 Data Storage

The app uses SQLite to store metrics data locally. This allows for:
- Faster data retrieval after initial fetch
- Historical trend analysis
- Offline access to previously fetched data

The database is automatically created and managed by the application.

## 📊 Interpreting the Metrics

### Active vs. Engaged Users
- **Active Users**: Developers who logged in with access to Copilot
- **Engaged Users**: Developers who actively used Copilot features

### Acceptance Rate
- Higher acceptance rates indicate Copilot is providing useful suggestions
- The daily acceptance rate chart shows how this metric evolves over time

### IDE Chat Usage
- Monitor how teams are adopting Copilot Chat in their development environments
- Track the number of conversations and interactions per user

## 🔒 Security and Privacy

- No code content or prompt data is collected or stored
- Only aggregate metrics are fetched from the GitHub API
- Data is stored locally, not transmitted to any third-party services

## 🛠️ Troubleshooting

- If no data appears, use the "Refresh Data" button to fetch new metrics
- Teams with fewer than 5 members will not have team-specific metrics available due to GitHub's privacy protection
- The GitHub API has rate limits - if you encounter errors, wait a few minutes and try again

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

*Note: GitHub Copilot and associated trademarks are the property of GitHub, Inc. This is an unofficial tool and is not endorsed by or affiliated with GitHub.*

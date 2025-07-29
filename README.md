# WA Gas Market Dashboard

A real-time dashboard for Western Australian Gas Bulletin Board data using the official AEMO API.

## Features

- 🔄 **Real-time data** from WA GBB official API
- 📊 **Interactive visualizations** with Plotly
- 🏭 **Multiple data types**: Flows, Capacity, Consumption, Forecasts
- 📱 **Responsive design** works on all devices  
- ⚡ **Fast loading** with Streamlit caching
- 📥 **Data export** in CSV and JSON formats

## Data Sources

This dashboard uses the official WA Gas Bulletin Board API endpoints:

- **Actual Flows**: Real-time gas flow data
- **Capacity Outlook**: System capacity information  
- **Medium Term Capacity**: Constraint forecasts
- **Consumption Data**: End user and large user consumption
- **Forecast Flows**: Predicted gas flows
- **Transportation**: Trucked gas data

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`  
3. Run the app: `streamlit run app.py`

## Deployment

Deploy easily on Streamlit Community Cloud - no special configuration needed!

## API Usage

The dashboard automatically fetches live data from:
`https://gbbwa.aemo.com.au/api/v1/report/[reportName]/current.csv`

No authentication required - all endpoints are publicly accessible.

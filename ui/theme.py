"""
Clean, Professional UI Theme and CSS for Gradio.
Enforces restrained light background, dark slate text, subtle border lines,
and a single professional navy/indigo accent color.
"""

CUSTOM_CSS = """
/* Professional Dashboard Clean Styling */
body, .gradio-container {
    background-color: #f8fafc !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    color: #0f172a !important;
}

/* Metric Cards */
.metric-box {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.metric-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-bottom: 6px;
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #1e293b;
}

/* Professional Headers */
.app-header {
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 16px;
    margin-bottom: 20px;
}

.app-title {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
}

.app-subtitle {
    font-size: 14px;
    color: #475569;
    margin-top: 4px;
}

/* Clean Tables */
table {
    border-collapse: collapse !important;
    width: 100% !important;
    font-size: 13px !important;
}

th {
    background-color: #f1f5f9 !important;
    color: #334155 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #cbd5e1 !important;
    padding: 10px 14px !important;
    text-align: left !important;
}

td {
    border-bottom: 1px solid #e2e8f0 !important;
    padding: 10px 14px !important;
    color: #1e293b !important;
}

/* Badges */
.badge-strong {
    background-color: #ecfdf5;
    color: #065f46;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
}

.badge-potential {
    background-color: #eff6ff;
    color: #1e40af;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
}

.badge-explore {
    background-color: #f8fafc;
    color: #475569;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
}

/* Primary Button Styling */
button.primary-btn {
    background-color: #2563eb !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    border: none !important;
}

button.primary-btn:hover {
    background-color: #1d4ed8 !important;
}
"""

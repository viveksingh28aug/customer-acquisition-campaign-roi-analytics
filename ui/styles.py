"""Custom modern CSS styles and themes for Streamlit UI."""

CUSTOM_CSS = """
<style>
/* Modern Glassmorphic / Clean Executive Dashboard Theme */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Metric Card Container */
.metric-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
    border-color: rgba(30, 136, 229, 0.5);
}

.metric-title {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8892b0;
    margin-bottom: 6px;
}

.metric-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.02em;
    margin-bottom: 4px;
}

.metric-sub {
    font-size: 0.80rem;
    color: #94a3b8;
}

/* Delta Pills */
.pill-positive {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
    font-weight: 600;
    font-size: 0.75rem;
}

.pill-negative {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    font-weight: 600;
    font-size: 0.75rem;
}

.pill-neutral {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    background-color: rgba(148, 163, 184, 0.15);
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.75rem;
}

/* Strategic Recommendation Cards */
.rec-card {
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
    border-left: 5px solid;
    background: rgba(255, 255, 255, 0.03);
}

.rec-critical {
    border-left-color: #ef4444;
    background: rgba(239, 68, 68, 0.05);
}

.rec-high {
    border-left-color: #f59e0b;
    background: rgba(245, 158, 11, 0.05);
}

.rec-medium {
    border-left-color: #3b82f6;
    background: rgba(59, 130, 246, 0.05);
}

.badge-tag {
    font-size: 0.70rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
}

/* Data Disclaimer Banner */
.disclaimer-box {
    border: 1px solid rgba(245, 158, 11, 0.3);
    background-color: rgba(245, 158, 11, 0.08);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #fcd34d;
    margin-bottom: 20px;
}
</style>
"""

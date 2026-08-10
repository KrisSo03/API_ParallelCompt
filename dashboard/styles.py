"""Visual theme for the Streamlit dashboard."""


APP_CSS = """
<style>
  .stApp { background: #f4f5f0; }
  .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem; }
  [data-testid="stSidebar"] { background: #123c33; }
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label { color: #f6fbf8 !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.18); }
  .atlas-hero {
    padding: 1.65rem 1.9rem;
    border-radius: 1.25rem;
    background:
      radial-gradient(circle at 88% 15%, rgba(190,225,117,.32), transparent 13rem),
      linear-gradient(120deg, #123c33 0%, #236b57 72%, #69a775 100%);
    color: white;
    box-shadow: 0 18px 42px rgba(18, 60, 51, .15);
    margin-bottom: 1rem;
  }
  .atlas-hero h1 { margin: 0; color: white; font-size: clamp(2rem, 4vw, 3.2rem); }
  .atlas-hero p { margin: .55rem 0 0; color: #dcebe4; font-size: 1.05rem; }
  .atlas-run { margin-top: .8rem; color: #c7dfd3; font-size: .86rem; }
  .atlas-status {
    display: inline-block;
    margin-top: .8rem;
    padding: .35rem .72rem;
    border-radius: 999px;
    color: #194f40;
    background: #dff0e8;
    font-size: .78rem;
    font-weight: 750;
  }
  .filter-title {
    margin: .2rem 0 -.2rem;
    color: #647b74;
    font-size: .74rem;
    font-weight: 800;
    letter-spacing: .06em;
    text-transform: uppercase;
  }
  div[data-testid="stHorizontalBlock"]:has(.filter-title) {
    padding: .8rem 1rem .45rem;
    border: 1px solid #dce5df;
    border-radius: 1rem;
    background: white;
  }
  div[data-testid="stMetric"] {
    padding: 1rem 1.1rem;
    border: 1px solid #dce5df;
    border-radius: 1rem;
    background: white;
    box-shadow: 0 8px 22px rgba(25, 64, 54, .055);
  }
  div[data-testid="stMetric"] label { color: #617a72; }
  div[data-testid="stMetricValue"] { color: #173a31; }
  [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
    border: 1px solid #dce5df;
    border-radius: 1rem;
    overflow: hidden;
    background: white;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #dce5df;
    border-radius: 1.1rem;
    background: white;
    box-shadow: 0 8px 24px rgba(25, 64, 54, .055);
  }
  .profile-kicker { color: #6d817b; font-size: .8rem; }
  .profile-title { margin: .25rem 0 .55rem; color: #153a30; font-size: 1.45rem; font-weight: 800; }
  .profile-description { min-height: 3.7rem; color: #657a74; font-size: .9rem; line-height: 1.55; }
  .source-badge {
    display: inline-block;
    padding: .32rem .65rem;
    border-radius: 999px;
    background: #fff2cf;
    color: #7b5710;
    font-size: .78rem;
    font-weight: 700;
  }
</style>
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import requests

st.set_page_config(page_title="Interactive Budget Tool", page_icon="📊", layout="wide")

IRS_401K_LIMIT = 23500

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* ── Scrollable left panel ── */
    .scroll-panel {
        height: calc(100vh - 160px);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 10px;
        border-right: 1px solid #e8e8e8;
    }
    /* ── Chat panel ── */
    .chat-history-box {
        height: 260px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        background: #fafafa;
        margin-bottom: 8px;
    }
    .chat-bubble-user {
        background: #e3f2fd; border-radius: 12px 12px 3px 12px;
        padding: 8px 12px; margin: 6px 0 6px 20%; font-size: 0.88rem;
        color: #1a237e;
    }
    .chat-bubble-assistant {
        background: #f1f8e9; border-radius: 12px 12px 12px 3px;
        padding: 8px 12px; margin: 6px 20% 6px 0; font-size: 0.88rem;
        color: #1b5e20;
    }
    .chat-welcome {
        color: #888; font-size: 0.82rem; text-align: center;
        padding: 20px 10px; font-style: italic;
    }

    .section-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        color: white; padding: 0.4rem 0.8rem; border-radius: 6px;
        font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; letter-spacing: 0.02em;
    }
    .sub-header {
        background: #e8eaf6; color: #283593; padding: 0.3rem 0.7rem;
        border-radius: 5px; font-size: 0.88rem; font-weight: 700; margin-bottom: 0.3rem;
    }
    .pretax-badge {
        display: inline-block; background: #e8f5e9; color: #2e7d32;
        border: 1px solid #a5d6a7; border-radius: 4px;
        font-size: 0.72rem; font-weight: 700; padding: 1px 6px; margin-left: 6px;
    }

    /* ── KPI cards ── */
    .result-card {
        background: #f8f9fa; border-left: 4px solid #4CAF50;
        border-radius: 6px; padding: 0.6rem 1rem; margin-bottom: 0.5rem;
    }
    .result-card-red    { border-left-color: #e74c3c !important; }
    .result-card-blue   { border-left-color: #2b579a !important; }
    .result-card-gray   { border-left-color: #888 !important; }
    .result-card-orange { border-left-color: #e67e22 !important; }
    .result-card-teal   { border-left-color: #00897b !important; }
    .result-card-green  { border-left-color: #27ae60 !important; }
    .result-label { font-size: 0.78rem; color: #555; margin: 0; }
    .result-value { font-size: 1.15rem; font-weight: 800; margin: 0; }
    .result-value-green  { color: #27ae60; }
    .result-value-red    { color: #e74c3c; }
    .result-value-blue   { color: #2b579a; }
    .result-value-orange { color: #e67e22; }
    .result-value-teal   { color: #00897b; }
    .result-value-dark   { color: #222; }

    /* detail rows inside expanders */
    .tax-card {
        background: #fcfcfc; border: 1px solid #e0e0e0; border-radius: 6px;
        padding: 0.5rem 0.8rem; margin-bottom: 0.3rem; font-size: 0.85rem;
    }
    .tax-row { display: flex; justify-content: space-between; }
    .tax-label { color: #666; }
    .tax-value { font-weight: 700; color: #333; }
    .thin-divider { border-top: 1px solid #ddd; margin: 0.6rem 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 6px 14px; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS / DEFAULTS
# ─────────────────────────────────────────────
DEFAULT_INCOME = {
    "my_income": 100000.0, "Spouse_income": 100000.0,
    "my_emp_ret": 5.0, "my_vol_ret": 0.0,
    "Spouse_emp_ret": 5.0, "Spouse_vol_ret": 0.0,
    "years": 1,
}

DEFAULT_SAVINGS = {
    "my_sav_mode": "% of my gross", "my_sav_dollar": 500.0,
    "my_sav_pct": 10.0, "my_sav_yield": 3.3,
    "spouse_sav_mode": "% of my gross", "spouse_sav_dollar": 500.0,
    "spouse_sav_pct": 10.0, "spouse_sav_yield": 3.3,
}

SAV_MODES = ["$ amount", "% of my gross", "% of combined gross"]

DEFAULT_EXPENSES = {
    "insurance": {
        "Health Prem (Mine)": 0.0, "Health Prem (Spouse)": 0.0,
        "Dental Ins": 0.0, "Vision Ins": 0.0,
        "Life Ins": 0.0, "Homeowners Ins": 0.0, "Vehicle Ins": 0.0,
    },
    "housing": {
        "Rent": 0.0, "Storage Unit Rent": 0.0, "Electric Bill": 0.0,
        "Gas Bill": 0.0, "Water Bill": 0.0, "Trash Bill": 0.0,
    },
    "childcare": {"Babysitting": 0.0, "Preschool": 0.0},
    "services": {
        "Dropbox": 0.0, "Amazon": 0.0, "Spotify": 0.0, "iCloud": 0.0,
        "House Cleaners": 0.0, "Cell Service": 0.0, "Cable (Comcast)": 0.0,
    },
    "groceries_gas": {"Groceries": 0.0, "Gas": 0.0},
    "misc": {},   # starts empty; all items are custom
}

CATEGORY_LABELS = {
    "insurance":     "🛡️ Insurance",
    "housing":       "🏠 Housing Costs",
    "childcare":     "👶 Childcare",
    "services":      "⚙️ Services",
    "groceries_gas": "🛒 Groceries & Gas",
    "misc":          "📦 Miscellaneous",
}

CHART_COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4", "#795548", "#607D8B"]

# ─────────────────────────────────────────────
# WIDGET KEY HELPERS
# ─────────────────────────────────────────────
def income_key(k):        return f"w_inc__{k}"
def expense_key(cat, k):  return f"w_exp__{cat}__{k}"
def sav_key(k):           return f"w_sav__{k}"
def cval_key(cat, name):  return f"w_cval__{cat}__{name}"
def cptx_key(cat, name):  return f"w_cptx__{cat}__{name}"

# ─────────────────────────────────────────────
# SESSION STATE BOOTSTRAP
# ─────────────────────────────────────────────
if "_bootstrapped" not in st.session_state:
    st.session_state._bootstrapped  = True
    st.session_state._load_success   = False
    st.session_state.custom_items    = {cat: {} for cat in DEFAULT_EXPENSES}
    st.session_state.chat_history       = []   # [{role, content}]
    st.session_state._chat_clear_pending  = False
    for k, v in DEFAULT_INCOME.items():
        st.session_state[income_key(k)] = v
    for k, v in DEFAULT_SAVINGS.items():
        st.session_state[sav_key(k)] = v
    for cat, items in DEFAULT_EXPENSES.items():
        for k, v in items.items():
            st.session_state[expense_key(cat, k)] = v

# Clear chat input on the rerun AFTER send (before the widget renders)
if st.session_state.get("_chat_clear_pending"):
    st.session_state["_chat_input_value"] = ""
    st.session_state._chat_clear_pending  = False

# ─────────────────────────────────────────────
# LOAD / SAVE
# ─────────────────────────────────────────────
def apply_load(raw: str):
    data = json.loads(raw)

    rates = data.get("rates", {})
    for k, default in DEFAULT_INCOME.items():
        raw_val = rates.get(k, default)
        try:
            v = int(float(raw_val)) if k == "years" else float(raw_val)
        except (ValueError, TypeError):
            v = default
        st.session_state[income_key(k)] = v

    savings = data.get("savings", {})
    for k, default in DEFAULT_SAVINGS.items():
        raw_val = savings.get(k, default)
        if k in ("my_sav_mode", "spouse_sav_mode"):
            v = raw_val if raw_val in SAV_MODES else default
        else:
            try:
                v = float(raw_val)
            except (ValueError, TypeError):
                v = default
        st.session_state[sav_key(k)] = v

    saved_exp = data.get("expenses", {})
    for cat, items in DEFAULT_EXPENSES.items():
        cat_data = saved_exp.get(cat, {})
        for k in items:
            try:
                v = float(cat_data.get(k, 0))
            except (ValueError, TypeError):
                v = 0.0
            st.session_state[expense_key(cat, k)] = v

    saved_custom = data.get("custom_items", {})
    st.session_state.custom_items = {cat: {} for cat in DEFAULT_EXPENSES}
    for cat in DEFAULT_EXPENSES:
        for name, meta in saved_custom.get(cat, {}).items():
            val    = float(meta.get("value",  0))
            pretax = bool(meta.get("pretax", False))
            st.session_state.custom_items[cat][name] = {"value": val, "pretax": pretax}
            st.session_state[cval_key(cat, name)] = val
            st.session_state[cptx_key(cat, name)] = pretax

    st.session_state._load_success = True

def build_save_payload() -> str:
    rates    = {k: st.session_state.get(income_key(k), DEFAULT_INCOME[k]) for k in DEFAULT_INCOME}
    savings  = {k: st.session_state.get(sav_key(k), DEFAULT_SAVINGS[k])   for k in DEFAULT_SAVINGS}
    expenses = {
        cat: {k: st.session_state.get(expense_key(cat, k), 0.0) for k in items}
        for cat, items in DEFAULT_EXPENSES.items()
    }
    custom_items = {}
    for cat, items in st.session_state.custom_items.items():
        custom_items[cat] = {
            name: {
                "value":  st.session_state.get(cval_key(cat, name), 0.0),
                "pretax": st.session_state.get(cptx_key(cat, name), False),
            }
            for name in items
        }
    return json.dumps({
        "rates": rates, "savings": savings,
        "expenses": expenses, "custom_items": custom_items,
    }, indent=4)

# ─────────────────────────────────────────────
# SAVINGS DEPOSIT RESOLVER
# ─────────────────────────────────────────────
def resolve_sav_deposit(who, my_mo, spouse_mo):
    mode   = st.session_state.get(sav_key(f"{who}_sav_mode"), "% of my gross")
    dollar = float(st.session_state.get(sav_key(f"{who}_sav_dollar"), 0) or 0)
    pct    = float(st.session_state.get(sav_key(f"{who}_sav_pct"),    0) or 0)
    own    = my_mo if who == "my" else spouse_mo
    comb   = my_mo + spouse_mo
    if mode == "$ amount":        return dollar
    elif mode == "% of my gross": return own  * (pct / 100)
    else:                         return comb * (pct / 100)

# ─────────────────────────────────────────────
# CALCULATION ENGINE
# ─────────────────────────────────────────────
def calculate() -> dict:
    def gi(k):      return float(st.session_state.get(income_key(k),       0) or 0)
    def ge(cat, k): return float(st.session_state.get(expense_key(cat, k), 0) or 0)
    def gs(k):      return float(st.session_state.get(sav_key(k),          0) or 0)

    my_gross_annual     = gi("my_income")
    spouse_gross_annual = gi("Spouse_income")
    total_gross_annual  = my_gross_annual + spouse_gross_annual
    my_mo               = my_gross_annual  / 12
    spouse_mo           = spouse_gross_annual / 12

    my_ret_rate     = (gi("my_emp_ret")     + gi("my_vol_ret"))     / 100
    spouse_ret_rate = (gi("Spouse_emp_ret") + gi("Spouse_vol_ret")) / 100
    my_ret_mo       = my_mo     * my_ret_rate
    spouse_ret_mo   = spouse_mo * spouse_ret_rate

    pretax_custom_annual = 0.0
    for cat, items in st.session_state.custom_items.items():
        for name in items:
            if st.session_state.get(cptx_key(cat, name), False):
                pretax_custom_annual += float(
                    st.session_state.get(cval_key(cat, name), 0) or 0) * 12

    total_pretax_ret = (my_ret_mo + spouse_ret_mo) * 12
    taxable_income   = max(0, total_gross_annual - total_pretax_ret
                           - pretax_custom_annual - 30_000)

    brackets = [
        (23_200, .10), (94_300, .12), (201_050, .22),
        (383_900, .24), (487_450, .32), (609_350, .35), (float("inf"), .37),
    ]
    fed_tax, prev = 0.0, 0.0
    for limit, rate in brackets:
        if taxable_income > limit:
            fed_tax += (limit - prev) * rate; prev = limit
        else:
            fed_tax += (taxable_income - prev) * rate; break

    my_fica     = (min(my_gross_annual,     176_100) * .062) + (my_gross_annual     * .0145)
    spouse_fica = (min(spouse_gross_annual, 176_100) * .062) + (spouse_gross_annual * .0145)
    total_tax   = fed_tax + my_fica + spouse_fica
    monthly_tax = total_tax / 12
    after_tax_annual  = total_gross_annual - total_tax
    after_tax_monthly = after_tax_annual / 12
    eff_rate    = (total_tax / total_gross_annual * 100) if total_gross_annual else 0

    my_sav_dep     = resolve_sav_deposit("my",     my_mo, spouse_mo)
    spouse_sav_dep = resolve_sav_deposit("spouse", my_mo, spouse_mo)
    my_yield       = gs("my_sav_yield")     / 100
    spouse_yield   = gs("spouse_sav_yield") / 100
    years          = max(1, int(gi("years")))

    def fv_series(pmt, annual_yield, n_years):
        r, bal, out = annual_yield / 12, 0.0, []
        for _ in range(n_years * 12):
            bal = bal * (1 + r) + pmt; out.append(bal)
        return out

    my_series       = fv_series(my_sav_dep,     my_yield,     years)
    spouse_series   = fv_series(spouse_sav_dep, spouse_yield, years)
    combined_series = [a + b for a, b in zip(my_series, spouse_series)]

    def interest_stats(series, pmt):
        if not series: return 0.0, 0.0
        idx         = min(11, len(series) - 1)
        bal_prev    = series[idx - 1] if idx > 0 else 0.0
        mo_int      = max(0.0, series[idx] - bal_prev - pmt)
        ann_int     = max(0.0, series[-1] - pmt * len(series))
        return mo_int, ann_int

    my_mo_int,     my_ann_int     = interest_stats(my_series,     my_sav_dep)
    spouse_mo_int, spouse_ann_int = interest_stats(spouse_series, spouse_sav_dep)

    pie_data  = {}
    total_exp = 0.0
    for cat, items in DEFAULT_EXPENSES.items():
        cat_sum = sum(ge(cat, k) for k in items)
        for name in st.session_state.custom_items.get(cat, {}):
            cat_sum += float(st.session_state.get(cval_key(cat, name), 0) or 0)
        label = CATEGORY_LABELS.get(cat, cat)
        if cat_sum > 0:
            pie_data[label] = cat_sum
        total_exp += cat_sum

    combined_ret_mo = my_ret_mo + spouse_ret_mo
    combined_sav_mo = my_sav_dep + spouse_sav_dep
    total_savings   = combined_ret_mo + combined_sav_mo
    monthly_disc    = (my_mo + spouse_mo) - monthly_tax - total_savings - total_exp

    waterfall = {
        "Taxes":             monthly_tax,
        "Retirement":        combined_ret_mo,
        "Savings / Invest.": combined_sav_mo,
        **{k: v for k, v in pie_data.items()},
        "Discretionary":     max(0, monthly_disc),
    }

    return {
        # income
        "total_gross_monthly":  my_mo + spouse_mo,
        "total_gross_annual":   total_gross_annual,
        "after_tax_monthly":    after_tax_monthly,
        "after_tax_annual":     after_tax_annual,
        "my_mo":                my_mo,
        "spouse_mo":            spouse_mo,
        # retirement
        "my_ret_mo":            my_ret_mo,
        "spouse_ret_mo":        spouse_ret_mo,
        "combined_ret_mo":      combined_ret_mo,
        "my_annual_ret":        my_ret_mo * 12,
        "spouse_annual_ret":    spouse_ret_mo * 12,
        # tax
        "monthly_tax":          monthly_tax,
        "fed_tax_monthly":      fed_tax / 12,
        "my_fica_monthly":      my_fica / 12,
        "spouse_fica_monthly":  spouse_fica / 12,
        "eff_rate":             eff_rate,
        "pretax_custom_mo":     pretax_custom_annual / 12,
        # savings
        "my_sav_dep":           my_sav_dep,
        "spouse_sav_dep":       spouse_sav_dep,
        "combined_sav_mo":      combined_sav_mo,
        "my_sav_yield":         my_yield,
        "spouse_sav_yield":     spouse_yield,
        "my_mo_int":            my_mo_int,
        "spouse_mo_int":        spouse_mo_int,
        "my_ann_int":           my_ann_int,
        "spouse_ann_int":       spouse_ann_int,
        "my_sav_fv":            my_series[-1]     if my_series     else 0.0,
        "spouse_sav_fv":        spouse_series[-1] if spouse_series else 0.0,
        "combined_sav_fv":      (my_series[-1] if my_series else 0.0) +
                                (spouse_series[-1] if spouse_series else 0.0),
        "my_series":            my_series,
        "spouse_series":        spouse_series,
        "combined_series":      combined_series,
        # expenses / discretionary
        "total_monthly_exp":    total_exp,
        "monthly_disc":         monthly_disc,
        "pie_data":             pie_data,
        "waterfall":            waterfall,
        "years":                years,
    }


# ─────────────────────────────────────────────
# CHAT CONTEXT BUILDER
# ─────────────────────────────────────────────
def build_chat_context(res: dict) -> str:
    """Serialize current inputs + calculated outputs into a compact context block."""
    def gi(k): return st.session_state.get(income_key(k), 0)
    def gs(k): return st.session_state.get(sav_key(k), 0)

    # Expense snapshot
    expense_lines = []
    for cat, items in DEFAULT_EXPENSES.items():
        label = CATEGORY_LABELS[cat]
        for item in items:
            val = st.session_state.get(expense_key(cat, item), 0)
            if val:
                expense_lines.append(f"  {label} / {item}: ${val:,.2f}/mo")
        for name, meta in st.session_state.custom_items.get(cat, {}).items():
            val = st.session_state.get(cval_key(cat, name), 0)
            ptx = st.session_state.get(cptx_key(cat, name), False)
            if val:
                expense_lines.append(
                    f"  {label} / {name}: ${val:,.2f}/mo{'  [PRE-TAX]' if ptx else ''}")

    ctx = f"""
=== CURRENT BUDGET SNAPSHOT ===

INCOME
  Your gross annual:          ${gi('my_income'):>12,.2f}
  Spouse gross annual:        ${gi('Spouse_income'):>12,.2f}
  Combined gross monthly:     ${res['total_gross_monthly']:>12,.2f}
  Combined after-tax monthly: ${res['after_tax_monthly']:>12,.2f}
  Effective tax rate:         {res['eff_rate']:.1f}%

RETIREMENT (monthly contributions)
  Your contribution:          ${res['my_ret_mo']:>12,.2f}  ({gi('my_emp_ret')+gi('my_vol_ret'):.1f}% of your gross)
  Spouse contribution:        ${res['spouse_ret_mo']:>12,.2f}  ({gi('Spouse_emp_ret')+gi('Spouse_vol_ret'):.1f}% of spouse gross)
  Combined:                   ${res['combined_ret_mo']:>12,.2f}
  IRS 401(k) limit/person:    ${IRS_401K_LIMIT:>12,}
  Your headroom remaining:    ${max(0, IRS_401K_LIMIT - res['my_annual_ret']):>12,.2f}
  Spouse headroom remaining:  ${max(0, IRS_401K_LIMIT - res['spouse_annual_ret']):>12,.2f}

SAVINGS / INVESTMENT ACCOUNTS
  Your mode:                  {gs('my_sav_mode')}
  Your monthly deposit:       ${res['my_sav_dep']:>12,.2f}
  Your annual yield:          {res['my_sav_yield']*100:.1f}%
  Your monthly interest:      ${res['my_mo_int']:>12,.2f}
  Your {res['years']}-year balance:      ${res['my_sav_fv']:>12,.2f}
  Spouse mode:                {gs('spouse_sav_mode')}
  Spouse monthly deposit:     ${res['spouse_sav_dep']:>12,.2f}
  Spouse annual yield:        {res['spouse_sav_yield']*100:.1f}%
  Spouse monthly interest:    ${res['spouse_mo_int']:>12,.2f}
  Spouse {res['years']}-year balance:    ${res['spouse_sav_fv']:>12,.2f}
  Combined {res['years']}-year balance:  ${res['combined_sav_fv']:>12,.2f}

MONTHLY EXPENSES (non-zero only)
{chr(10).join(expense_lines) if expense_lines else "  (none entered)"}
  TOTAL:                      ${res['total_monthly_exp']:>12,.2f}

TAX BREAKDOWN (monthly)
  Federal income tax:         ${res['fed_tax_monthly']:>12,.2f}
  Your FICA:                  ${res['my_fica_monthly']:>12,.2f}
  Spouse FICA:                ${res['spouse_fica_monthly']:>12,.2f}
  Pre-tax custom deductions:  ${res['pretax_custom_mo']:>12,.2f}

SUMMARY
  Total monthly outflows:     ${res['total_gross_monthly'] - res['monthly_disc']:>12,.2f}
  Monthly remaining:          ${res['monthly_disc']:>12,.2f}  {'✅ surplus' if res['monthly_disc'] >= 0 else '⚠️ SHORTFALL'}
================================
"""
    return ctx.strip()


SYSTEM_PROMPT = """You are a friendly, knowledgeable financial assistant embedded inside a household budgeting tool. At the start of every message you receive a live snapshot of the user's current budget inputs and calculated outputs. Use these numbers directly when answering — never ask the user to re-state values you can already see.

Your job:
• Answer questions about the user's specific budget (taxes, savings, retirement, expenses, discretionary income, what-if scenarios).
• Explain financial concepts clearly (effective vs marginal tax rate, compound interest, 401k limits, FICA, etc.).
• Point out things the user might want to pay attention to (e.g. shortfall, low savings rate, 401k headroom, pre-tax opportunities).
• Give concrete numbers when helpful (e.g. "if you raise your retirement % by 2%, your monthly discretionary drops by ~$X").

Guidelines:
• Be concise. Bullet points are fine for multi-part answers.
• Don't give personalized investment advice or make specific stock/fund recommendations.
• If asked about realistic return assumptions, the long-run S&P 500 average is ~10% nominal, ~7% real (inflation-adjusted). 14%+ is optimistic for long-term planning.
• The tool uses 2025 US federal tax brackets, $30,000 standard deduction (married filing jointly), and a $176,100 Social Security wage base.
• Always refer to the live snapshot numbers rather than making up values."""


# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────
LAYOUT_BASE = dict(
    margin=dict(t=50, b=40, l=10, r=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12),
)

def chart_expense_pie(res):
    pie_data = {k: v for k, v in res["pie_data"].items() if v > 0}
    if not pie_data: return None
    fig = go.Figure(go.Pie(
        labels=list(pie_data.keys()), values=list(pie_data.values()),
        hole=0.38, textinfo="label+percent", textfont_size=12,
        marker=dict(colors=CHART_COLORS, line=dict(color="white", width=2)),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}/mo<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE, height=420,
        title=dict(text="Monthly Expense Breakdown", font_size=15, x=0.5),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    )
    return fig

def chart_savings_growth(res, display_years):
    if res["my_sav_dep"] == 0 and res["spouse_sav_dep"] == 0: return None
    def fv(pmt, yr, n):
        r, bal, out = yr / 12, 0.0, []
        for _ in range(n * 12):
            bal = bal * (1 + r) + pmt; out.append(bal)
        return out
    my_bal = fv(res["my_sav_dep"],     res["my_sav_yield"],     display_years)
    sp_bal = fv(res["spouse_sav_dep"], res["spouse_sav_yield"], display_years)
    co_bal = [a + b for a, b in zip(my_bal, sp_bal)]
    x      = [m / 12 for m in range(1, display_years * 12 + 1)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=my_bal,
        name=f"Your Acct ({res['my_sav_yield']*100:.1f}%)",
        mode="lines", line=dict(color="#2196F3", width=2),
        hovertemplate="Year %{x:.1f}<br>$%{y:,.0f}<extra>Your Acct</extra>"))
    fig.add_trace(go.Scatter(x=x, y=sp_bal,
        name=f"Spouse's Acct ({res['spouse_sav_yield']*100:.1f}%)",
        mode="lines", line=dict(color="#9C27B0", width=2),
        hovertemplate="Year %{x:.1f}<br>$%{y:,.0f}<extra>Spouse Acct</extra>"))
    fig.add_trace(go.Scatter(x=x, y=co_bal, name="Combined",
        mode="lines", line=dict(color="#4CAF50", width=3, dash="dot"),
        hovertemplate="Year %{x:.1f}<br>$%{y:,.0f}<extra>Combined</extra>"))
    fig.add_trace(go.Scatter(x=x + x[::-1], y=co_bal + [0]*len(x),
        fill="toself", fillcolor="rgba(76,175,80,0.07)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
    fig.update_layout(**LAYOUT_BASE, height=420,
        title=dict(text=f"Savings / Investment Growth Over {display_years} Year(s)", font_size=15, x=0.5),
        xaxis=dict(title="Years", gridcolor="#eee", zeroline=False),
        yaxis=dict(title="Balance ($)", tickprefix="$", tickformat=",.0f", gridcolor="#eee"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        hovermode="x unified",
    )
    return fig

def chart_income_waterfall(res):
    if res["total_gross_monthly"] == 0: return None
    wf     = res["waterfall"]
    labels, values = list(wf.keys()), list(wf.values())
    total  = res["total_gross_monthly"]
    clrs   = (["#e74c3c", "#e67e22", "#00897b"]
              + CHART_COLORS[:max(0, len(labels) - 4)]
              + ["#27ae60"])[:len(labels)]
    pcts   = [v / total * 100 for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=clrs,
        text=[f"${v:,.0f}  ({p:.1f}%)" for v, p in zip(values, pcts)],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>$%{x:,.2f}/mo<extra></extra>",
    ))
    fig.update_layout(**LAYOUT_BASE,
        height=max(380, 38 * len(labels) + 80),
        title=dict(text=f"Where Your ${total:,.0f}/mo Goes", font_size=15, x=0.5),
        xaxis=dict(title="Monthly Amount ($)", tickprefix="$", tickformat=",.0f", gridcolor="#eee"),
        yaxis=dict(autorange="reversed"), bargap=0.35,
    )
    return fig

def chart_cashflow(res):
    if res["total_gross_monthly"] == 0: return None
    disc  = res["monthly_disc"]
    cats  = ["Gross Income", "Taxes", "Retirement", "Savings / Invest.", "Bills", "Remaining"]
    vals  = [res["total_gross_monthly"], -res["monthly_tax"],
             -res["combined_ret_mo"], -res["combined_sav_mo"],
             -res["total_monthly_exp"], disc]
    clrs  = ["#27ae60","#e74c3c","#e67e22","#00897b","#9C27B0",
             "#27ae60" if disc >= 0 else "#e74c3c"]
    fig = go.Figure(go.Bar(
        x=cats, y=vals, marker_color=clrs,
        text=[f"${abs(v):,.0f}" for v in vals], textposition="outside",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="#333", line_width=1)
    fig.update_layout(**LAYOUT_BASE, height=420,
        title=dict(text="Monthly Cash Flow", font_size=15, x=0.5),
        xaxis=dict(gridcolor="#eee"),
        yaxis=dict(title="$ / Month", tickprefix="$", tickformat=",.0f", gridcolor="#eee"),
        showlegend=False,
    )
    return fig

def chart_retirement_gauge(res):
    limit = IRS_401K_LIMIT
    fig = make_subplots(rows=1, cols=2,
        subplot_titles=("Your 401(k) vs IRS Limit", "Spouse's 401(k) vs IRS Limit"),
        specs=[[{"type": "indicator"}, {"type": "indicator"}]])
    for col, val, name in [(1, res["my_annual_ret"], "You"), (2, res["spouse_annual_ret"], "Spouse")]:
        pct = min(val / limit * 100, 100) if limit else 0
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta", value=val,
            delta={"reference": limit, "valueformat": "$,.0f",
                   "increasing": {"color": "#e74c3c"}, "decreasing": {"color": "#27ae60"}},
            number={"prefix": "$", "valueformat": ",.0f"},
            gauge={
                "axis": {"range": [0, limit], "tickprefix": "$", "tickformat": ",.0f"},
                "bar":  {"color": "#27ae60" if pct < 80 else "#e67e22" if pct < 100 else "#e74c3c"},
                "steps": [
                    {"range": [0,        limit * .5], "color": "#e8f5e9"},
                    {"range": [limit*.5, limit * .8], "color": "#fff9c4"},
                    {"range": [limit*.8, limit],      "color": "#ffebee"},
                ],
                "threshold": {"line": {"color": "#c0392b", "width": 3},
                              "thickness": 0.85, "value": limit},
            },
            title={"text": f"{name}<br><span style='font-size:11px'>IRS limit ${limit:,}</span>"},
        ), row=1, col=col)
    fig.update_layout(**LAYOUT_BASE, height=340,
        title=dict(text="Annual Retirement Contributions vs IRS Limit", font_size=15, x=0.5))
    return fig


def send_chat_message(user_msg: str, res: dict):
    """Call Anthropic API with full budget context + conversation history."""
    context = build_chat_context(res)
    # Prepend fresh context to the user turn
    augmented_user = f"[BUDGET SNAPSHOT — auto-attached]\n{context}\n\n[USER QUESTION]\n{user_msg}"

    messages = []
    # Include prior turns (use original user text, not augmented, for prior turns)
    for turn in st.session_state.chat_history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": augmented_user})

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ""},
            json={
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "system":     SYSTEM_PROMPT,
                "messages":   messages,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data        = resp.json()
        reply       = data["content"][0]["text"]
        # Store original user text (not augmented) + assistant reply
        st.session_state.chat_history.append({"role": "user",      "content": user_msg})
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"⚠️ API error: {e}"


# ─────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────
def result_card(label, value, color="dark", card_class=""):
    st.markdown(f"""
    <div class="result-card {'result-card-' + card_class if card_class else ''}">
        <p class="result-label">{label}</p>
        <p class="result-value result-value-{color}">{value}</p>
    </div>""", unsafe_allow_html=True)

def tax_card(rows):
    inner = "".join(
        f'<div class="tax-row"><span class="tax-label">{l}</span>'
        f'<span class="tax-value">{v}</span></div>' for l, v in rows)
    st.markdown(f'<div class="tax-card">{inner}</div>', unsafe_allow_html=True)

def show_chart(fig, empty_msg="Enter data to see this chart."):
    if fig: st.plotly_chart(fig, width='stretch')
    else:   st.info(empty_msg)

def expense_section(category, title):
    st.markdown(f'<div class="section-header">{title} — Monthly $</div>', unsafe_allow_html=True)

    # Default items
    items = list(DEFAULT_EXPENSES[category].keys())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j, key in enumerate(items[i: i + 2]):
            with cols[j]:
                st.number_input(key, min_value=0.0, step=1.0, key=expense_key(category, key))

    # Custom items
    custom = st.session_state.custom_items.get(category, {})
    if custom:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
    for name in list(custom.keys()):
        is_pretax = st.session_state.get(cptx_key(category, name), False)
        c_amt, c_ptx, c_del = st.columns([3, 2, 1])
        with c_amt:
            st.number_input(
                f"{name}{' 🟢' if is_pretax else ''}",
                min_value=0.0, step=1.0, key=cval_key(category, name))
        with c_ptx:
            st.checkbox("Pre-tax", key=cptx_key(category, name))
        with c_del:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del__{category}__{name}", help=f"Remove {name}"):
                del st.session_state.custom_items[category][name]
                for wk in [cval_key(category, name), cptx_key(category, name)]:
                    st.session_state.pop(wk, None)
                st.rerun()

    # Add item expander
    short_label = CATEGORY_LABELS[category].split(" ", 1)[-1]
    with st.expander(f"➕ Add item to {short_label}"):
        n_col, a_col, p_col, b_col = st.columns([3, 2, 2, 1])
        with n_col:
            new_name = st.text_input("Name", key=f"new_name__{category}")
        with a_col:
            new_amt  = st.number_input("Amount ($)", min_value=0.0, step=1.0,
                                       key=f"new_amt__{category}")
        with p_col:
            new_ptx  = st.checkbox("Pre-tax?", key=f"new_ptx__{category}")
        with b_col:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("Add", key=f"add_btn__{category}"):
                name = new_name.strip()
                all_existing = (list(DEFAULT_EXPENSES[category].keys()) +
                                list(st.session_state.custom_items[category].keys()))
                if not name:
                    st.warning("Enter a name.")
                elif name in all_existing:
                    st.warning(f"'{name}' already exists.")
                else:
                    st.session_state.custom_items[category][name] = {
                        "value": new_amt, "pretax": new_ptx}
                    st.session_state[cval_key(category, name)] = new_amt
                    st.session_state[cptx_key(category, name)] = new_ptx
                    st.rerun()

def savings_input_block(who, label):
    st.markdown(f'<div class="sub-header">💰 {label}</div>', unsafe_allow_html=True)
    mode_key   = sav_key(f"{who}_sav_mode")
    dollar_key = sav_key(f"{who}_sav_dollar")
    pct_key    = sav_key(f"{who}_sav_pct")
    yield_key  = sav_key(f"{who}_sav_yield")
    col_mode, col_val, col_yield = st.columns([2, 1.5, 1.5])
    with col_mode:
        st.radio("Contribution input as", options=SAV_MODES, key=mode_key, horizontal=True)
    mode = st.session_state.get(mode_key, "% of my gross")
    with col_val:
        if mode == "$ amount":
            st.number_input("Monthly ($)", min_value=0.0, step=50.0, key=dollar_key)
        else:
            st.number_input("Contribution (%)", min_value=0.0, max_value=100.0,
                            step=0.5, key=pct_key)
    with col_yield:
        st.number_input("Annual Yield (%)", min_value=0.0, max_value=50.0,
                        step=0.1, key=yield_key)

# ─────────────────────────────────────────────
# TITLE & FILE CONTROLS  (outside columns — full width)
# ─────────────────────────────────────────────
st.title("📊 Interactive Budget Tool")

hdr_l, hdr_r = st.columns([3, 1])
with hdr_r:
    st.download_button("💾 Save Profile", data=build_save_payload(),
                       file_name="budget_data.json", mime="application/json",
                       width='stretch')
    uploaded = st.file_uploader("📁 Load Profile", type="json", label_visibility="collapsed")
    if uploaded is not None:
        fingerprint = f"{uploaded.name}__{uploaded.size}"
        if st.session_state.get("_last_loaded_file") != fingerprint:
            st.session_state["_last_loaded_file"] = fingerprint
            try:
                apply_load(uploaded.read().decode())
            except Exception as e:
                st.error(f"Could not parse file: {e}")

if st.session_state.get("_load_success"):
    st.success("✅ Profile loaded successfully!")
    st.session_state._load_success = False

# ─────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────
left_col, right_col = st.columns([2, 3], gap="large")

# ══════════════════════════════════════════════
# LEFT — scrollable input panel
# ══════════════════════════════════════════════
with left_col:
    st.markdown('<div class="scroll-panel">', unsafe_allow_html=True)
    # Income & Retirement
    st.markdown('<div class="section-header">💰 Income & Retirement</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Your Gross Annual ($)",      min_value=0.0, step=1000.0,
                        key=income_key("my_income"))
        st.number_input("Your Employee Ret. (%)",     min_value=0.0, max_value=100.0,
                        step=0.5, key=income_key("my_emp_ret"))
        st.number_input("Your Voluntary Ret. (%)",    min_value=0.0, max_value=100.0,
                        step=0.5, key=income_key("my_vol_ret"))
    with c2:
        st.number_input("Spouse Gross Annual ($)",    min_value=0.0, step=1000.0,
                        key=income_key("Spouse_income"))
        st.number_input("Spouse Employee Ret. (%)",   min_value=0.0, max_value=100.0,
                        step=0.5, key=income_key("Spouse_emp_ret"))
        st.number_input("Spouse Voluntary Ret. (%)",  min_value=0.0, max_value=100.0,
                        step=0.5, key=income_key("Spouse_vol_ret"))
    st.number_input("Savings Year Target (#)", min_value=1, max_value=50, step=1,
                    key=income_key("years"),
                    help="Default timespan for the savings growth chart.")

    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    # Savings / Investment
    st.markdown('<div class="section-header">🏦 Savings / Investment Accounts</div>',
                unsafe_allow_html=True)
    savings_input_block("my",     "Your Account")
    savings_input_block("spouse", "Spouse's Account")

    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    # All expense categories
    for cat in DEFAULT_EXPENSES:
        expense_section(cat, CATEGORY_LABELS[cat])
        st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # close scroll-panel

# ══════════════════════════════════════════════
# RIGHT — sticky dashboard
# ══════════════════════════════════════════════
with right_col:
    res = calculate()

    st.markdown('<div class="section-header">📊 Budget Dashboard</div>', unsafe_allow_html=True)

    # ── 5 KPI cards ──────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    disc = res["monthly_disc"]

    with k1:
        result_card(
            "💵 Combined Gross / After-tax",
            f"${res['total_gross_monthly']:,.0f} / ${res['after_tax_monthly']:,.0f}",
            "dark", "gray")
    with k2:
        result_card("🧾 Monthly Bills",      f"${res['total_monthly_exp']:,.0f}", "dark",   "gray")
    with k3:
        result_card("🏦 Monthly Savings",    f"${res['combined_sav_mo']:,.0f}",   "teal",   "teal")
    with k4:
        result_card("📈 Monthly Retirement", f"${res['combined_ret_mo']:,.0f}",   "orange", "orange")
    with k5:
        result_card(
            "✅ Remaining / mo" if disc >= 0 else "⚠️ Shortfall / mo",
            f"${disc:,.0f}",
            "green" if disc >= 0 else "red",
            "green" if disc >= 0 else "red")

    # ── Pre-tax banner ────────────────────────
    if res["pretax_custom_mo"] > 0:
        st.info(f"🟢 Pre-tax deductions: **${res['pretax_custom_mo']:,.2f}/mo** "
                f"(${res['pretax_custom_mo']*12:,.2f}/yr) — reducing your taxable income.")

    # ── Expandable detail panels ──────────────
    with st.expander("📋 Monthly Tax Breakdown"):
        tax_card([
            ("• Federal Income Tax",        f"${res['fed_tax_monthly']:,.2f}"),
            ("• Your FICA Tax",             f"${res['my_fica_monthly']:,.2f}"),
            ("• Spouse's FICA Tax",         f"${res['spouse_fica_monthly']:,.2f}"),
            ("• Pre-tax deductions",        f"−${res['pretax_custom_mo']:,.2f}/mo"),
            ("• Effective Tax Rate",        f"{res['eff_rate']:.1f}%"),
            ("• Combined After-tax / mo",   f"${res['after_tax_monthly']:,.2f}"),
        ])

    with st.expander("📈 Retirement Account Detail"):
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**🧑 Your Account**")
            tax_card([
                ("Employee contribution (%)", f"{st.session_state.get(income_key('my_emp_ret'), 0):.1f}%"),
                ("Voluntary contribution (%)", f"{st.session_state.get(income_key('my_vol_ret'), 0):.1f}%"),
                ("Monthly contribution",       f"${res['my_ret_mo']:,.2f}"),
                ("Annual contribution",        f"${res['my_annual_ret']:,.2f}"),
                ("IRS 401(k) limit",           f"${IRS_401K_LIMIT:,}"),
                ("Remaining headroom",         f"${max(0, IRS_401K_LIMIT - res['my_annual_ret']):,.2f}"),
            ])
        with r2:
            st.markdown("**👫 Spouse's Account**")
            tax_card([
                ("Employee contribution (%)", f"{st.session_state.get(income_key('Spouse_emp_ret'), 0):.1f}%"),
                ("Voluntary contribution (%)", f"{st.session_state.get(income_key('Spouse_vol_ret'), 0):.1f}%"),
                ("Monthly contribution",       f"${res['spouse_ret_mo']:,.2f}"),
                ("Annual contribution",        f"${res['spouse_annual_ret']:,.2f}"),
                ("IRS 401(k) limit",           f"${IRS_401K_LIMIT:,}"),
                ("Remaining headroom",         f"${max(0, IRS_401K_LIMIT - res['spouse_annual_ret']):,.2f}"),
            ])
        st.markdown("")
        tax_card([
            ("Combined monthly retirement",  f"${res['combined_ret_mo']:,.2f}"),
            ("Combined annual retirement",   f"${res['my_annual_ret'] + res['spouse_annual_ret']:,.2f}"),
        ])

    with st.expander("🏦 Savings Account Detail"):
        sa1, sa2 = st.columns(2)
        with sa1:
            st.markdown("**🧑 Your Account**")
            tax_card([
                ("Monthly contribution",     f"${res['my_sav_dep']:,.2f}"),
                ("Monthly interest earned",  f"${res['my_mo_int']:,.2f}"),
                ("Annual interest accrual",  f"${res['my_ann_int']:,.2f}"),
                (f"Balance at {res['years']} yr(s)", f"${res['my_sav_fv']:,.2f}"),
            ])
        with sa2:
            st.markdown("**👫 Spouse's Account**")
            tax_card([
                ("Monthly contribution",     f"${res['spouse_sav_dep']:,.2f}"),
                ("Monthly interest earned",  f"${res['spouse_mo_int']:,.2f}"),
                ("Annual interest accrual",  f"${res['spouse_ann_int']:,.2f}"),
                (f"Balance at {res['years']} yr(s)", f"${res['spouse_sav_fv']:,.2f}"),
            ])
        st.markdown("")
        tax_card([
            ("Combined monthly contributions",    f"${res['combined_sav_mo']:,.2f}"),
            ("Combined monthly interest",         f"${res['my_mo_int'] + res['spouse_mo_int']:,.2f}"),
            ("Combined annual interest accrual",  f"${res['my_ann_int'] + res['spouse_ann_int']:,.2f}"),
            (f"Combined balance at {res['years']} yr(s)", f"${res['combined_sav_fv']:,.2f}"),
        ])

    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🥧 Expense Breakdown", "📈 Savings Growth",
        "💧 Income Waterfall",  "📊 Cash Flow",
        "🎯 Retirement Limits",
    ])
    with tab1:
        show_chart(chart_expense_pie(res), "Enter non-zero expenses to see breakdown.")
    with tab2:
        sl_col, _ = st.columns([2, 1])
        with sl_col:
            display_years = st.slider("📅 View growth over (years)", 1, 40,
                                      max(res["years"], 1), key="growth_slider")
        show_chart(chart_savings_growth(res, display_years),
                   "Enter savings contributions and yield to see growth.")
    with tab3:
        show_chart(chart_income_waterfall(res), "Enter income and expenses to see the waterfall.")
    with tab4:
        show_chart(chart_cashflow(res), "Enter income and expenses to see cash flow.")
    with tab5:
        show_chart(chart_retirement_gauge(res), "Enter retirement percentages to see gauges.")

    # ── Budget Assistant (always visible below charts) ────────────────────
    st.markdown("<div class='thin-divider'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">💬 Budget Assistant</div>',
                unsafe_allow_html=True)
    st.caption("Ask anything — I always see your current inputs and calculated values.")

    # Render chat history as styled HTML bubbles (avoids st.chat_message tab bug)
    history = st.session_state.chat_history
    if history:
        bubbles = ""
        for turn in history:
            if turn["role"] == "user":
                bubbles += f'<div class="chat-bubble-user">🧑 {turn["content"]}</div>'
            else:
                # Convert newlines to <br> for HTML display
                content = turn["content"].replace("\n", "<br>")
                bubbles += f'<div class="chat-bubble-assistant">🤖 {content}</div>'
        st.markdown(f'<div class="chat-history-box">{bubbles}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="chat-history-box">'
            '<div class="chat-welcome">'
            "👋 Ask me anything about your budget!<br><br>"
            "<b>Try:</b> What is my effective savings rate? &nbsp;|&nbsp; "
            "How much does raising retirement by 2% affect my discretionary? &nbsp;|&nbsp; "
            "Which expense category is biggest?"
            "</div></div>",
            unsafe_allow_html=True,
        )

    # Input + Clear on same row using columns
    inp_col, clr_col = st.columns([5, 1])
    with inp_col:
        user_input = st.text_input(
            "Message", placeholder="Ask about your budget...",
            label_visibility="collapsed",
            value=st.session_state.get("_chat_input_value", ""),
            key="chat_text_input",
        )
        # Sync value store with current widget content
        st.session_state["_chat_input_value"] = user_input
    with clr_col:
        send_clicked = st.button("Send ➤", key="chat_send", use_container_width=True)
    
    clr_col2, _ = st.columns([1, 5])
    with clr_col2:
        if st.button("🗑️ Clear chat", key="chat_clear"):
            st.session_state.chat_history = []
            st.rerun()

    # Trigger on Send button OR Enter (non-empty input)
    if (send_clicked or user_input) and user_input.strip():
        with st.spinner("Thinking..."):
            send_chat_message(user_input.strip(), res)
        # Flag the input to clear on next rerun (can't set widget key mid-run)
        st.session_state._chat_clear_pending = True
        st.rerun()

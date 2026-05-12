from __future__ import annotations

from typing import Any


def enrich_valuation(case: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(case)
    ebitda = float(case.get("ebitda") or 0)
    multiple = float(case.get("terminal_multiple") or 0)
    ev = float(case.get("enterprise_value") or ebitda * multiple)
    net_debt = float(case.get("net_debt") or 0)
    shares = float(case.get("shares_outstanding") or 0)
    current_price = float(case.get("current_share_price") or 0)
    fcf = float(case.get("free_cash_flow") or 0)
    equity_value = ev - net_debt
    share_price = equity_value / shares if shares else 0
    market_cap = shares * current_price if shares and current_price else 0
    enriched["implied_enterprise_value"] = round(ev, 2)
    enriched["implied_equity_value"] = round(equity_value, 2)
    enriched["implied_share_price"] = round(share_price, 2)
    enriched["upside_downside_pct"] = round(((share_price / current_price) - 1) * 100, 1) if current_price else 0
    enriched["ev_ebitda"] = round(ev / ebitda, 2) if ebitda else 0
    enriched["fcf_yield"] = round((fcf / market_cap) * 100, 1) if market_cap else 0
    enriched["p_nav"] = round(market_cap / float(case.get("manual_npv")), 2) if market_cap and case.get("manual_npv") else 0
    return enriched


def sensitivity_table(case: dict[str, Any]) -> list[dict[str, float]]:
    base_revenue = float(case.get("revenue") or 0)
    base_margin = float(case.get("ebitda_margin") or 0) / 100
    multiples = [max(float(case.get("terminal_multiple") or 0) - 1, 0), float(case.get("terminal_multiple") or 0), float(case.get("terminal_multiple") or 0) + 1]
    rows = []
    for revenue_growth in [-10, 0, 10]:
        revenue = base_revenue * (1 + revenue_growth / 100)
        ebitda = revenue * base_margin
        row = {"growth": revenue_growth}
        for multiple in multiples:
            row[f"{multiple:.1f}x"] = round(ebitda * multiple, 1)
        rows.append(row)
    return rows

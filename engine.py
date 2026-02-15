from __future__ import annotations

def calc_scope12(
    electricity_kwh_year: float,
    natural_gas_m3_year: float,
    grid_factor_kg_per_kwh: float = 0.43,
    gas_factor_kg_per_m3: float = 2.0,
    carbon_price_eur_per_ton: float = 85.0,
) -> dict:

    scope2_ton = (electricity_kwh_year * grid_factor_kg_per_kwh) / 1000.0
    scope1_ton = (natural_gas_m3_year * gas_factor_kg_per_m3) / 1000.0

    total_ton = scope1_ton + scope2_ton
    risk_eur = total_ton * carbon_price_eur_per_ton

    return {
        "scope1_ton": scope1_ton,
        "scope2_ton": scope2_ton,
        "total_ton": total_ton,
        "risk_eur": risk_eur,
    }


def calc_hvac_savings_simple(
    electricity_kwh_year: float,
    delta_t_c: float,
    energy_sensitivity_per

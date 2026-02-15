def calc_scope12(electricity_kwh_year,
                 natural_gas_m3_year,
                 grid_factor_kg_per_kwh,
                 gas_factor_kg_per_m3,
                 carbon_price_eur_per_ton):

    scope2_ton = (electricity_kwh_year * grid_factor_kg_per_kwh) / 1000.0
    scope1_ton = (natural_gas_m3_year * gas_factor_kg_per_m3) / 1000.0

    total_ton = scope1_ton + scope2_ton
    risk_eur = total_ton * carbon_price_eur_per_ton

    return {
        "scope1_ton": scope1_ton,
        "scope2_ton": scope2_ton,
        "total_ton": total_ton,
        "risk_eur": risk_eur
    }

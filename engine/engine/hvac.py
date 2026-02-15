def calc_hvac_savings_simple(electricity_kwh_year,
                             delta_t_c,
                             energy_sensitivity_per_c,
                             beta,
                             grid_factor_kg_per_kwh,
                             carbon_price_eur_per_ton):

    external_energy_effect = delta_t_c * energy_sensitivity_per_c
    hvac_reduction = external_energy_effect * beta

    if hvac_reduction > 0.30:
        hvac_reduction = 0.30

    saved_kwh = electricity_kwh_year * hvac_reduction
    saved_co2_ton = (saved_kwh * grid_factor_kg_per_kwh) / 1000.0
    saved_eur = saved_co2_ton * carbon_price_eur_per_ton

    return {
        "saved_kwh": saved_kwh,
        "saved_co2_ton": saved_co2_ton,
        "saved_eur": saved_eur,
        "reduction_ratio": hvac_reduction
    }

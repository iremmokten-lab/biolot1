# engine/__init__.py

def calc_scope12(
    electricity_kwh_year,
    natural_gas_m3_year,
    grid_factor_kg_per_kwh=0.43,
    gas_factor_kg_per_m3=2.0,
    carbon_price_eur_per_ton=85.5
):
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


def calc_hvac_savings_simple(
    electricity_kwh_year,
    delta_t_c,
    energy_sensitivity_per_c,
    beta,
    grid_factor_kg_per_kwh=0.43,
    carbon_price_eur_per_ton=85.5
):
    external_energy_effect = delta_t_c * energy_sensitivity_per_c
    hvac_reduction = external_energy_effect * beta

    if hvac_reduction < 0:
        hvac_reduction = 0.0
    if hvac_reduction > 0.30:
        hvac_reduction = 0.30

    saved_kwh = electricity_kwh_year * hvac_reduction
    saved_co2_ton = (saved_kwh * grid_factor_kg_per_kwh) / 1000.0
    saved_eur = saved_co2_ton * carbon_price_eur_per_ton

    return {
        "hvac_reduction_ratio": hvac_reduction,
        "saved_kwh": saved_kwh,
        "saved_co2_ton": saved_co2_ton,
        "saved_eur": saved_eur
    }


def calc_water_savings(
    water_baseline_m3_year,
    water_actual_m3_year,
    pump_kwh_per_m3,
    grid_factor_kg_per_kwh=0.43,
    carbon_price_eur_per_ton=85.5
):
    saved_water_m3 = water_baseline_m3_year - water_actual_m3_year
    if saved_water_m3 < 0:
        saved_water_m3 = 0.0

    saved_pump_kwh = saved_water_m3 * pump_kwh_per_m3
    saved_co2_ton = (saved_pump_kwh * grid_factor_kg_per_kwh) / 1000.0
    saved_eur = saved_co2_ton * carbon_price_eur_per_ton

    return {
        "saved_water_m3": saved_water_m3,
        "saved_pump_kwh": saved_pump_kwh,
        "saved_co2_ton": saved_co2_ton,
        "saved_eur": saved_eur
    }

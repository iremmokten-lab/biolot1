BIOL0T_ENGINE_VERSION = "0.1.0"

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
def run_biolot(
    electricity_kwh_year,
    natural_gas_m3_year,
    area_m2,
    carbon_price,
    grid_factor,
    gas_factor,
    delta_t,
    energy_sensitivity,
    beta,
    water_baseline,
    water_actual,
    pump_kwh_per_m3,
):
    karbon = calc_scope12(
        electricity_kwh_year,
        natural_gas_m3_year,
        grid_factor,
        gas_factor,
        carbon_price,
    )

    hvac = calc_hvac_savings_simple(
        electricity_kwh_year,
        delta_t,
        energy_sensitivity,
        beta,
        grid_factor,
        carbon_price,
    )

    su = calc_water_savings(
        water_baseline,
        water_actual,
        pump_kwh_per_m3,
        grid_factor,
        carbon_price,
    )

    # toplam kazanç
    toplam_kwh = hvac["saved_kwh"] + su["saved_pump_kwh"]
    toplam_co2 = hvac["saved_co2_ton"] + su["saved_co2_ton"]
    toplam_euro = hvac["saved_eur"] + su["saved_eur"]

    return {
        "engine_version": BIOL0T_ENGINE_VERSION,
        "inputs": {
            "electricity_kwh_year": electricity_kwh_year,
            "natural_gas_m3_year": natural_gas_m3_year,
            "area_m2": area_m2,
            "carbon_price": carbon_price,
            "grid_factor": grid_factor,
            "gas_factor": gas_factor,
            "delta_t": delta_t,
            "energy_sensitivity": energy_sensitivity,
            "beta": beta,
            "water_baseline": water_baseline,
            "water_actual": water_actual,
            "pump_kwh_per_m3": pump_kwh_per_m3,
        },
        "carbon": karbon,
        "hvac": hvac,
        "water": su,
        "total_operational_gain": {
            "total_saved_kwh": toplam_kwh,
            "total_saved_co2_ton": toplam_co2,
            "total_saved_eur": toplam_euro,
        },
    }

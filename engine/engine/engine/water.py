def calc_water_savings(water_baseline_m3_year,
                       water_actual_m3_year,
                       pump_kwh_per_m3,
                       grid_factor_kg_per_kwh,
                       carbon_price_eur_per_ton):

    saved_water_m3 = water_baseline_m3_year - water_actual_m3_year

    if saved_water_m3 < 0:
        saved_water_m3 = 0

    saved_pump_kwh = saved_water_m3 * pump_kwh_per_m3
    saved_co2_ton = (saved_pump_kwh * grid_factor_kg_per_kwh) / 1000.0
    saved_eur = saved_co2_ton * carbon_price_eur_per_ton

    return {
        "saved_water_m3": saved_water_m3,
        "saved_pump_kwh": saved_pump_kwh,
        "saved_co2_ton": saved_co2_ton,
        "saved_eur": saved_eur
    }

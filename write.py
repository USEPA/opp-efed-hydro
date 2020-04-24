import numpy as np
from paths import met_grid_path, ncep_table_path, weather_key_path


def met_grid(precip_points):
    precip_points.to_csv(met_grid_path, index_label='weather_grid')


def ncep_table(table, year):
    path = ncep_table_path.format(year)
    table.to_csv(path)


def keyfile(points, years, output_header):
    np.savez_compressed(weather_key_path, points=points, years=np.array(years), header=np.array(output_header))

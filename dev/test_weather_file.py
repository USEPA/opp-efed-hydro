import pandas as pd
from weather import WeatherArray


def read_old(s):
    weatherfile_path = r"J:\NationalData\NewWeatherFiles\{}_grid.wea"
    table = pd.read_csv(weatherfile_path.format(s),
                        names=["month", "day", "year", "precip", "pet", "temp", "solar_rad", "wind"])
    return table


cube = WeatherArray()

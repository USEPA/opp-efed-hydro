import pandas as pd
from weather import WeatherArray


def read_old(s):
    weatherfile_path = r"J:\opp-efed-data\global\NewWeatherFiles\{}_grid.wea"
    table = pd.read_csv(weatherfile_path.format(s),
                        names=["month", "day", "year", "precip", "pet", "temp", "solar_rad", "wind"])
    return table[:365]

def excelize(it): return ",".join(map(str, it))

def compare():
    cube = WeatherArray()

    for station in cube.index:
        new = cube.fetch_station(station, df=True)
        old = read_old(int(station))
        print(excelize(old.wind))
        print(excelize(new.wind))
        input()



compare()
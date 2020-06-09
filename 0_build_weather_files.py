from hydro.weather import WeatherCubeBuilder, NcepBuilder


def ncep():
    # Specify run parameters
    years = range(1984, 2015)
    bounds = [20, 60, -130, -60]  # min lat, max lat, min long, max long

    # Process all weather and store to memory
    NcepBuilder(years, bounds)

def main():
    # Specify run parameters
    years = range(1971, 2000)
    bounds = [20, 60, -130, -60]  # min lat, max lat, min long, max long

    # Process all weather and store to memory
    WeatherCubeBuilder(years, bounds)

main()
#if __name__ == '__main__':
#    main()
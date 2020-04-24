from weather import WeatherCubeBuilder


def main():
    # Specify run parameters
    years = range(1961, 2018)
    bounds = [20, 60, -130, -60]  # min lat, max lat, min long, max long

    # Process all weather and store to memory
    WeatherCubeBuilder(years, bounds)


if __name__ == '__main__':
    main()

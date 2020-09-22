from weather_files.weather import WeatherCubeBuilder, NcepBuilder


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

<<<<<<< HEAD
=======
#main()
>>>>>>> 4657bb242ca4fe4849977f07c96ac9b57d3dfaa3
ncep()
#if __name__ == '__main__':
#    main()
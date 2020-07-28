import os
import pandas as pd
import scipy.interpolate
import numpy as np
import datetime as dt

import write_hydro as write
import read_hydro as read
from paths_hydro import met_grid_path, ncep_table_path, weather_array_path, ncep_array_path
from utilities_hydro import MemoryMatrix, DateManager, report

ncep_vars = ["tmin.2m", "tmax.2m", "air.2m", "dswrf.ntat", "uwnd.10m", "vwnd.10m"]


# TODO - datemanager
# TODO - wind still not matching up - interpolation pre/post calculation?

class WeatherCubeBuilder(object):
    def __init__(self, years=None, bounds=None):
        self.years = years
        self.output_header = ["precip", "temp_min", "temp_max", "temp_avg", "pet", "wind"]

        # Get the coordinates for all precip stations being used and write to file
        self.precip_points = map_stations(bounds)
        #self.populate(bounds)
        write.keyfile(self.precip_points, self.years, self.output_header)

    def populate(self, bounds):

        # Initialize the output in-memory array
        out_array = np.memmap(weather_array_path, mode='w+', dtype=np.float32, shape=self.shape)

        for year in self.years:
            report("Running year {}...\n\tLoading datasets...".format(year))

            # Read, combine, and adjust NCEP tables
            overwrite = True
            intermediate = ncep_table_path.format(year)
            if not overwrite and os.path.exists(intermediate):
                ncep_table = pd.read_csv(intermediate)
                ncep_table['time'] = pd.to_datetime(ncep_table['time'])
            else:
                ncep_table = read.ncep(year, ncep_vars, bounds)
                write.ncep_table(ncep_table, year)

            # Calculate PET and eliminate unneeded headings
            ncep_table = process_ncep(ncep_table)

            # Load precip table
            precip_table = read.precip(year)
            precip_table = self.precip_points.merge(precip_table, how='left', on=['lat', 'lon'])

            # Determine the offset in days between the start of the year and the start of all years
            annual_offset = (dt.date(year, 1, 1) - self.start_date).days

            # Loop through each date and perform interpolation
            report("\tPerforming daily interpolation...")
            for i, (date, daily_ncep) in enumerate(ncep_table.groupby('date')):
                daily_precip = precip_table[precip_table.time == date]

                # Interpolate NCEP data to resolution of precip data
                daily_table = perform_interpolation(daily_precip, daily_ncep, date)

                # Write to memory map
                out_array[:, annual_offset + i] = daily_table[["precip", "tmin", "tmax", "tavg", "pet", "wind"]]

    @property
    def end_date(self):
        return dt.date(self.years[-1], 12, 31)

    @property
    def shape(self):
        return self.precip_points.shape[0], (self.end_date - self.start_date).days + 1, len(self.output_header)

    @property
    def start_date(self):
        return dt.date(self.years[0], 1, 1)


class NcepBuilder(object):
    def __init__(self, years=None, bounds=None):
        self.years = years
        self.output_header = ["lat", "lon", "temp_min", "temp_max", "temp_avg", "pet", "wind"]

        self.points = self.get_points()

        # Get the coordinates for all precip stations being used and write to file
        self.populate(bounds)
        write.keyfile(self.points, self.years, self.output_header)

    def get_points(self):
        test = ncep_table_path.format(self.years[0])
        points = pd.read_csv(test)[['lat', 'lon']].drop_duplicates()
        points['site_index'] = np.arange(1, points.shape[0] + 1)
        return points

    def populate(self, bounds):

        # Initialize the output in-memory array
        out_array = np.memmap(ncep_array_path, mode='w+', dtype=np.float32, shape=self.shape)

        for year in self.years:
            report("Running year {}...\n\tLoading datasets...".format(year))

            # Read, combine, and adjust NCEP tables
            overwrite = True
            intermediate = ncep_table_path.format(year)
            if not overwrite and os.path.exists(intermediate):
                ncep_table = pd.read_csv(intermediate)
                ncep_table['time'] = pd.to_datetime(ncep_table['time'])
            else:
                ncep_table = read.ncep(year, ncep_vars, bounds)
                write.ncep_table(ncep_table, year)

            # Calculate PET and eliminate unneeded headings
            ncep_table = process_ncep(ncep_table)

            # Determine the offset in days between the start of the year and the start of all years
            annual_offset = (dt.date(year, 1, 1) - self.start_date).days

            # Loop through each date and perform interpolation
            report("\tPerforming daily...")
            for i, (date, daily_ncep) in enumerate(ncep_table.groupby('date')):
                # Write to memory map
                out_array[:, annual_offset + i] = daily_ncep[["lat", "lon", "tmin", "tmax", "tavg", "pet", "wind"]]

    @property
    def end_date(self):
        return dt.date(self.years[-1], 12, 31)

    @property
    def shape(self):
        return self.points.shape[0], (self.end_date - self.start_date).days + 1, len(self.output_header)

    @property
    def start_date(self):
        return dt.date(self.years[0], 1, 1)


class WeatherArray(MemoryMatrix, DateManager):
    def __init__(self, index_col='stationID'):
        # Set row/column offsets
        start_date, end_date, self.header, points = read.keyfile()

        self.points = pd.DataFrame(points, columns=['weather_grid', 'stationID', 'lat', 'lon']).set_index(index_col)

        # Set dates
        DateManager.__init__(self, start_date, end_date)

        # Initialize memory matrix
        MemoryMatrix.__init__(self, [self.points.index, self.n_dates, self.header],
                              dtype=np.float32, path=weather_array_path, existing=True)

    def fetch_station(self, station_id, df=True):
        try:
            data = np.array(self.fetch(station_id, copy=True, verbose=True)).T
            if df:
                data = pd.DataFrame(data.T, columns=self.header, index=self.dates)
        except KeyError:
            report("Met station {} not found".format(station_id), warn=2)
            return
        except ValueError:
            report(f"Met station {station_id} not working")
            return
        return data


class NcepArray(MemoryMatrix, DateManager):
    def __init__(self, index_col='site_index'):
        # Set row/column offsets
        start_date, end_date, self.header, points = read.keyfile()
        print(self.header)
        print(points)
        self.points = pd.DataFrame(points, columns=['lat', 'lon', 'site_index']).set_index(index_col)

        # Set dates
        DateManager.__init__(self, start_date, end_date)

        # Initialize memory matrix
        MemoryMatrix.__init__(self, [self.points.index, self.n_dates, self.header],
                              dtype=np.float32, path=ncep_array_path, existing=True)

    def fetch_station(self, station_id, df=True):
        try:
            data = np.array(self.fetch(station_id, copy=True, verbose=True)).T
        except KeyError:
            report("Met station {} not found".format(station_id), warn=2)
            return
        if df:
            data = pd.DataFrame(data.T, columns=self.header, index=self.dates)
        return data


def process_ncep(table):
    # Convert date-times to dates
    table['date'] = table['time'].dt.normalize()

    # Adjust column names
    table.rename(columns={"air": "tavg", "dswrf": "solar_rad"}, inplace=True)

    # Adjust units
    for var in 'tmin', 'tmax', 'tavg':
        table[var] -= 273.15  # K -> deg C
    table['solar_rad'] = (table.solar_rad / 1e6) * 86400. * 0.408  # W/m2 to mm/d using 1 MJ/m2-d = 0.408 mm/d per FAO

    # Compute vector wind speed from uwind and vwind in m/s to cm/s
    table['wind'] = np.sqrt((table.pop('uwnd') ** 2) + (table.pop('vwnd') ** 2)) * 100.

    # Calculate potential evapotranspiration using Hargreaves-Samani method
    table['pet'] = \
        (0.0023 * table.solar_rad * (table.tavg + 17.8) * ((table.tmax - table.tmin) ** 0.5)) / 10  # mm/d -> cm/d

    return table


def perform_interpolation(daily_precip, daily_ncep, date):
    interpolated = daily_precip.copy()
    interpolated['date'] = date
    points = daily_ncep[['lat', 'lon']].values
    new_points = daily_precip[['lat', 'lon']].values
    for value_field in ('tmax', 'tmin', 'tavg', 'pet', 'wind'):
        interpolated[value_field] = \
            scipy.interpolate.griddata(points, daily_ncep[value_field].values, new_points)
    return interpolated


def map_stations(bounds=None, sample_year=1990, overwrite=True):
    """ Use a representative precip file to assess the number of precipitation stations """
    crosswalk = read.crosswalk()
    if overwrite or not os.path.exists(met_grid_path):
        stations = read.precip(sample_year, bounds)[['lat', 'lon']] \
            .drop_duplicates().sort_values(['lat', 'lon']).reset_index(drop=True)
        # Sort values and add an index
        stations = stations.merge(crosswalk, left_on=('lat', 'lon'), right_on=('lat_met', 'lon_met'), how='outer')
        write.met_grid(stations)
    else:
        stations = read.met_grid()
    return stations[['weather_grid', 'stationID', 'lat', 'lon']]

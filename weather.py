import os
import pandas as pd
import scipy.interpolate
import numpy as np
import datetime as dt

import write
import read
from paths import met_grid_path, ncep_table_path, weather_array_path
from utilities import MemoryMatrix, DateManager, report

ncep_vars = ["tmin.2m", "tmax.2m", "air.2m", "dswrf.ntat", "uwnd.10m", "vwnd.10m"]


class WeatherCubeBuilder(object):
    def __init__(self, years=None, bounds=None):

        self.output_header = ["precip", "temp_min", "temp_max", "temp_avg", "pet", "wind"]

        # If all the necessary input parameters are provided, generate the weather file
        self.years = years
        # Get the coordinates for all precip stations being used and write to file
        self.precip_points = self.map_stations(bounds)
        self.populate(bounds)
        write.keyfile(self.precip_points, self.years, self.output_header)

    @staticmethod
    def perform_interpolation(daily_precip, daily_ncep, date):
        interpolated = daily_precip.copy()
        interpolated['date'] = date
        points = daily_ncep[['lat', 'lon']].values
        new_points = daily_precip[['lat', 'lon']].values
        for value_field in ('tmax', 'tmin', 'tavg', 'pet', 'wind'):
            interpolated[value_field] = \
                scipy.interpolate.griddata(points, daily_ncep[value_field].values, new_points)
        return interpolated

    @staticmethod
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

    def populate(self, bounds):

        # Initialize the output in-memory array
        out_array = np.memmap(weather_array_path, mode='w+', dtype=np.float32, shape=self.shape)

        for year in self.years:
            print("Running year {}...\n\tLoading datasets...".format(year))

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
            ncep_table = self.process_ncep(ncep_table)

            # Load precip table
            precip_table = read.precip(year)
            precip_table = self.precip_points.merge(precip_table, how='left', on=['lat', 'lon'])

            # Determine the offset in days between the start of the year and the start of all years
            annual_offset = (dt.date(year, 1, 1) - self.start_date).days

            # Loop through each date and perform interpolation
            print("\tPerforming daily interpolation...")
            for i, (date, daily_ncep) in enumerate(ncep_table.groupby('date')):
                # 0     1     2  1961   0.0  0.19  22.03  229.35  273.65
                daily_precip = precip_table[precip_table.time == date]

                # Interpolate NCEP data to resolution of precip data
                daily_table = self.perform_interpolation(daily_precip, daily_ncep, date)

                # Write to memory map
                out_array[:, annual_offset + i] = daily_table[["precip", "tmin", "tmax", "tavg", "pet", "wind"]]

    @staticmethod
    def process_ncep(table):

        def hargreaves_samani(t_min, t_max, solar_rad, temp):
            # ;Convert sradt from W/m2 to mm/d; using 1 MJ/m2-d = 0.408 mm/d per FAO
            # srt1 = (srt(time|:,lat|:,lon|:)/1e6) * 86400. * 0.408
            # ;Hargreaves-Samani Method - PET estimate (mm/day -> cm/day)
            # har = (0.0023*srt1*(tempC+17.8)*(rtemp^0.5))/10

            srtl = (solar_rad / 1e6) * 86400. * 0.408
            return (0.0023 * srtl * (temp + 17.8) * ((t_max - t_min) ** 0.5)) / 10  # (mm/d -> cm/d)

        # Adjust column names
        table.rename(columns={"air": "tavg", "dswrf": "solar_rad"}, inplace=True)

        # Convert date-times to dates
        table['date'] = table['time'].dt.normalize()

        # Average out sub-daily data
        table = table.groupby(['lat', 'lon', 'date']).mean().reset_index()

        # Adjust units
        for var in 'tmin', 'tmax', 'tavg':
            table[var] -= 273.15  # K -> deg C

        # Calculate potential evapotranspiration using Hargreaves-Samani method
        table['pet'] = \
            hargreaves_samani(table['tmin'], table['tmax'], table['solar_rad'], table['tavg'])

        # Compute vector wind speed from uwind and vwind in m/s to cm/s
        table['wind'] = np.sqrt((table.pop('uwnd') ** 2) + (table.pop('vwnd') ** 2)) * 100.

        return table

    @property
    def end_date(self):
        return dt.date(self.years[-1], 12, 31)

    @property
    def shape(self):
        return (self.precip_points.shape[0], (self.end_date - self.start_date).days + 1, len(self.output_header))

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
        except Exception as e:
            report("Met station {} not found".format(station_id), warn=2)
            return
        if df:
            data = pd.DataFrame(data.T, columns=self.header, index=self.dates)
        return data
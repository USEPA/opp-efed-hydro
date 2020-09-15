import os
import numpy as np
import pandas as pd

from collections import Iterable
from tempfile import mkstemp


def report(message, tabs=0, warn=0):
    tabs = "\t" * tabs
    prefix = {0: "", 1: "Warning: ", 2: "Failure: ", 3: "Debug: "}[warn]
    print(tabs + prefix + str(message))


class MemoryMatrix(object):    """ A wrapper for NumPy 'memmap' functionality which allows the storage and recall of arrays from disk """

    def __init__(self, dimensions, dtype=np.float32, path=None, existing=False, name='null', index_dim=0,
                 verbose=False):
        self.dtype = dtype
        self.path = path
        self.existing = existing
        self.name = name

        # Initialize dimensions of array
        self.dimensions = tuple(np.array(d) if isinstance(d, Iterable) else d for d in dimensions)
        self.labels = tuple(d if isinstance(d, Iterable) else None for d in self.dimensions)
        self.shape = tuple(map(int, (d.size if isinstance(d, Iterable) else d for d in self.dimensions)))
        self.index = self.labels[index_dim]

        # Add an alias if it's called for
        if self.index is not None:
            self.lookup = {label: i for i, label in enumerate(self.index)}
            self.aliased = True
        else:
            self.lookup = None
            self.aliased = False

        self.initialize_array(verbose)

    def alias_to_index(self, aliases, verbose=False):
        found = None
        if type(aliases) in (pd.Series, list, set, np.array, np.ndarray):
            indices = np.array([self.lookup.get(alias, np.nan) for alias in aliases])
            found = np.where(~np.isnan(indices))[0]
            indices = indices[found]
            if verbose and found.size != len(aliases):
                missing = np.array(aliases)[~found]
                report("Missing {} of {} needed indices from array {}".format(missing.size, len(aliases), self.name))
        else:
            indices = self.lookup.get(aliases)
            if indices is None and verbose:
                report("Alias {} not found in array {}".format(aliases, self.name), warn=2)
                return None, None
        return np.int32(indices), found

    def fetch(self, index, copy=False, verbose=False, return_found=False, iloc=False, pop=False):

        # Initialize reader (with write capability in case of 'pop')
        array = self.reader

        # Convert aliased item(s) to indices if applicable
        if self.aliased and not iloc:
            index, found = self.alias_to_index(index, verbose)
            if index is None:
                return

        # Extract data from array
        output = array[index]

        # Return a copy of the selection instead of a view if necessary
        if pop or copy:
            output = np.array(output)
            if pop:  # Set the selected rows to zero after extracting array
                array[index] = 0.

        del array
        if return_found:
            return output, found
        else:
            return output

    def initialize_array(self, verbose=False):

        # Load from saved file if one is specified, else generate
        if self.path is None:
            self.existing = False
            self.path = mkstemp(suffix=".dat", dir=os.path.join("..", "bin", "temp"))[1]
        else:
            # Add suffix to path if one wasn't provided
            if not self.path.endswith("dat"):
                self.path += ".dat"
            if os.path.exists(self.path):
                self.existing = True

        if not self.existing:
            if verbose:
                report("Creating memory map {}...".format(self.path))
            try:
                os.makedirs(os.path.dirname(self.path))
            except FileExistsError:
                pass
            np.memmap(self.path, dtype=self.dtype, mode='w+', shape=self.shape)  # Allocate memory

    def update(self, index, values, return_found=False, verbose=False, iloc=False):
        array = self.writer
        if self.aliased and not iloc:
            index = self.alias_to_index(index, verbose)
        array[index] = values
        del array

    @property
    def reader(self):
        return np.memmap(self.path, dtype=self.dtype, mode='r+', shape=self.shape)

    @property
    def writer(self):
        mode = 'r+' if os.path.isfile(self.path) else 'w+'
        return np.memmap(self.path, dtype=self.dtype, mode=mode, shape=self.shape)


class DateManager(object):
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date

    def date_offset(self, start, end, coerce=True, return_msg=False):
        messages = []
        start_offset, end_offset = 0, 0
        if self.start_date > start:  # scenarios start later than selected start date
            messages.append('start date is earlier')
        else:
            start_offset = (start - self.start_date).astype(int)
        if self.end_date < end:
            messages.append('end date is later')
        else:
            end_offset = (end - self.end_date).astype(int)

        if coerce:
            self.start_date = self.start_date + np.timedelta64(int(start_offset), 'D')
            self.end_date = self.end_date + np.timedelta64(int(end_offset), 'D')

        if return_msg:
            return start_offset, end_offset, messages
        else:
            return start_offset, end_offset

    @property
    def dates(self):
        return pd.date_range(self.start_date, self.end_date)

    @property
    def dates_julian(self):
        return (self.dates - self.dates[0]).days.astype(int)

    @property
    def mid_month(self):
        return self.months[:-1] + (self.months[1:] - self.months[:-1]) / 2

    @property
    def mid_month_julian(self):
        return np.int32((self.mid_month - self.dates[0]).days)

    @property
    def months(self):
        return pd.date_range(self.dates.min(), self.dates.max() + np.timedelta64(1, 'M'), freq='MS')

    @property
    def months_julian(self):
        return pd.date_range(self.dates.min(), self.dates.max() + np.timedelta64(1, 'M'), freq='MS').month

    @property
    def new_year(self):
        return np.int32([(np.datetime64("{}-01-01".format(year)) - self.start_date).astype(int)
                         for year in np.unique(self.dates.year)])

    @property
    def n_dates(self):
        return self.dates.size

    @property
    def month_index(self):
        return self.dates.month

    @property
    def year_index(self):
        return np.int16(self.dates.year - self.dates.year[0])

    @property
    def year_length(self):
        return np.unique(self.dates, return_counts=True)[1]

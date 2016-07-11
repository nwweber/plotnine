from __future__ import absolute_import, division, print_function

import numpy as np
import pandas as pd
from mizani.bounds import expand_range

from ..utils import DISCRETE_KINDS, CONTINUOUS_KINDS
from ..utils import identity, match, is_waive, alias
from ..utils.exceptions import GgplotError
from .range import RangeContinuous
from .scale import scale_discrete, scale_continuous


# positions scales have a couple of differences (quirks) that
# make necessary to override some of the scale_discrete and
# scale_continuous methods
#
# scale_position_discrete and scale_position_continuous
# are intermediate base classes where the required overiding
# is done
class scale_position_discrete(scale_discrete):
    """
    Base class for discrete position scales
    """
    # All positions have no guide
    guide = None

    # After transformations all position values map
    # to themselves
    palette = staticmethod(identity)

    # Keeps two ranges, range and range_c
    range_c = RangeContinuous

    def __init__(self, *args, **kwargs):
        self.range_c = self.range_c()
        scale_discrete.__init__(self, *args, **kwargs)

    def reset(self):
        # Can't reset discrete scale because
        # no way to recover values
        self.range_c.reset()

    def is_empty(self):
        return (self.range.range is None and
                self._limits is None and
                self.range_c.range is None)

    def train(self, series):
        # The discrete position scale is capable of doing
        # training for continuous data.
        # This complicates training and mapping, but makes it
        # possible to place objects at non-integer positions,
        # as is necessary for jittering etc.
        if series.dtype.kind in CONTINUOUS_KINDS:
            self.range_c.train(series)
        else:
            self.range.train(series)

    def map(self, series, limits=None):
        # Discrete values are converted into integers starting
        # at 1
        if not limits:
            limits = self.limits
        if series.dtype.kind in DISCRETE_KINDS:
            seq = np.arange(1, len(limits)+1)
            return seq[match(series, limits)]
        return series

    @property
    def limits(self):
        if self.is_empty():
            return (0, 1)

        if self._limits:
            return self._limits
        elif self.range.range:
            # discrete range
            return self.range.range
        else:
            raise GgplotError(
                'Lost, do not know what the limits are.')

    def dimension(self, expand=(0, 0)):
        """
        The phyical size of the scale, if a position scale
        Unlike limits, this always returns a numeric vector of length 2
        """
        c_range = self.range_c.range
        d_range = self.range.range

        continuous = expand_range(c_range, expand[0], 0, 1)
        discrete = expand_range((1, len(d_range)), 0, expand[1], 1)

        if self.is_empty():
            return (0, 1)
        elif d_range is None:  # only continuous
            return continuous
        elif c_range is None:  # only discrete
            return discrete
        else:  # both
            # e.g categorical bar plot have discrete items, but
            # are plot on a continuous x scale
            a = np.hstack([continuous, discrete])
            return a.min(), a.max()


class scale_position_continuous(scale_continuous):
    """
    Base class for continuous position scales
    """
    # All positions have no guide
    guide = None

    # After transformations all position values map
    # to themselves
    palette = staticmethod(identity)

    def map(self, series, limits=None):
        # Position aesthetics don't map, because the coordinate
        # system takes care of it.
        # But the continuous scale has to deal with out of bound points
        if not len(series):
            return series
        if not limits:
            limits = self.limits
        scaled = self.oob(series, limits)
        scaled[pd.isnull(scaled)] = self.na_value
        return scaled


class scale_x_discrete(scale_position_discrete):
    aesthetics = ['x', 'xmin', 'xmax', 'xend']


class scale_y_discrete(scale_position_discrete):
    aesthetics = ['y', 'ymin', 'ymax', 'yend']


class scale_x_continuous(scale_position_continuous):
    aesthetics = ['x', 'xmin', 'xmax', 'xend', 'xintercept']


class scale_y_continuous(scale_position_continuous):
    aesthetics = ['y', 'ymin', 'ymax', 'yend', 'yintercept',
                  'ymin_final', 'ymax_final',
                  'lower', 'middle', 'upper']


# Transformed scales
class scale_x_datetime(scale_position_continuous):
    _trans = 'datetime'
    aesthetics = ['x', 'xmin', 'xmax', 'xend']


class scale_y_datetime(scale_position_continuous):
    _trans = 'datetime'
    aesthetics = ['y', 'ymin', 'ymay', 'yend']


alias('scale_x_date', scale_x_datetime)
alias('scale_y_date', scale_y_datetime)


class scale_x_timedelta(scale_position_continuous):
    _trans = 'pd_timedelta'
    aesthetics = ['x', 'xmin', 'xmax', 'xend']


class scale_y_timedelta(scale_position_continuous):
    _trans = 'pd_timedelta'
    aesthetics = ['y', 'ymin', 'ymay', 'yend']


class scale_x_sqrt(scale_x_continuous):
    _trans = 'sqrt'


class scale_y_sqrt(scale_y_continuous):
    _trans = 'sqrt'


class scale_x_log10(scale_x_continuous):
    _trans = 'log10'


class scale_y_log10(scale_y_continuous):
    _trans = 'log10'


class scale_x_reverse(scale_x_continuous):
    _trans = 'reverse'


class scale_y_reverse(scale_y_continuous):
    _trans = 'reverse'

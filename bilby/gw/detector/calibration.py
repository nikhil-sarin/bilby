""" Functions for adding calibration factors to waveform templates.
"""
import copy
import os

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from ...core.utils.log import logger
from ...core.prior.dict import PriorDict


def read_calibration_file(filename, frequency_array, number_of_response_curves, starting_index=0):
    """
    Function to read the hdf5 files from the calibration group containing the physical calibration response curves.

    Parameters
    ----------
    filename: str
        Location of the HDF5 file that contains the curves
    frequency_array: array-like
        The frequency values to calculate the calibration response curves at
    number_of_response_curves: int
        Number of random draws to use from the calibration file
    starting_index: int
        Index of the first curve to use within the array. This allows for segmenting the calibration curve array
        into smaller pieces.

    Returns
    -------
    calibration_draws: array-like
        Array which contains the calibration responses as a function of the frequency array specified.
        Shape is (number_of_response_curves x len(frequency_array))

    """
    import tables

    logger.info(f"Reading calibration draws from {filename}")
    calibration_file = tables.open_file(filename, 'r')
    calibration_amplitude = \
        calibration_file.root.deltaR.draws_amp_rel[starting_index:number_of_response_curves + starting_index]
    calibration_phase = \
        calibration_file.root.deltaR.draws_phase[starting_index:number_of_response_curves + starting_index]

    calibration_frequencies = calibration_file.root.deltaR.freq[:]

    calibration_file.close()

    if len(calibration_amplitude.dtype) != 0:  # handling if this is a calibration group hdf5 file
        calibration_amplitude = calibration_amplitude.view(np.float64).reshape(calibration_amplitude.shape + (-1,))
        calibration_phase = calibration_phase.view(np.float64).reshape(calibration_phase.shape + (-1,))
        calibration_frequencies = calibration_frequencies.view(np.float64)

    # interpolate to the frequency array (where if outside the range of the calibration uncertainty its fixed to 1)
    calibration_draws = calibration_amplitude * np.exp(1j * calibration_phase)
    calibration_draws = interp1d(
        calibration_frequencies, calibration_draws, kind='cubic',
        bounds_error=False, fill_value=1)(frequency_array)

    try:
        parameter_draws = pd.read_hdf(filename, key="CalParams")
    except KeyError:
        parameter_draws = None

    return calibration_draws, parameter_draws


def write_calibration_file(filename, frequency_array, calibration_draws, calibration_parameter_draws=None):
    """
    Function to write the generated response curves to file

    Parameters
    ----------
    filename: str
        Location and filename to save the file
    frequency_array: array-like
        The frequency values where the calibration response was calculated
    calibration_draws: array-like
        Array which contains the calibration responses as a function of the frequency array specified.
        Shape is (number_of_response_curves x len(frequency_array))
    calibration_parameter_draws: data_frame
        Parameters used to generate the random draws of the calibration response curves

    """
    import tables

    logger.info(f"Writing calibration draws to {filename}")
    calibration_file = tables.open_file(filename, 'w')
    deltaR_group = calibration_file.create_group(calibration_file.root, 'deltaR')

    # Save output
    calibration_file.create_carray(deltaR_group, 'draws_amp_rel', obj=np.abs(calibration_draws))
    calibration_file.create_carray(deltaR_group, 'draws_phase', obj=np.angle(calibration_draws))
    calibration_file.create_carray(deltaR_group, 'freq', obj=frequency_array)

    calibration_file.close()

    # Save calibration parameter draws
    if calibration_parameter_draws is not None:
        calibration_parameter_draws.to_hdf(filename, key='CalParams', data_columns=True, format='table')


class Recalibrate(object):

    name = 'none'

    def __init__(self, prefix='recalib_'):
        """
        Base calibration object. This applies no transformation

        Parameters
        ==========
        prefix: str
            Prefix on parameters relating to the calibration.
        """
        self.params = dict()
        self.prefix = prefix

    def __repr__(self):
        return self.__class__.__name__ + '(prefix=\'{}\')'.format(self.prefix)

    def get_calibration_factor(self, frequency_array, **params):
        """Apply calibration model

        This method should be overwritten by subclasses

        Parameters
        ==========
        frequency_array: array-like
            The frequency values to calculate the calibration factor for.
        params : dict
            Dictionary of sampling parameters which includes
            calibration parameters.

        Returns
        =======
        calibration_factor : array-like
            The factor to multiply the strain by.
        """
        return np.ones_like(frequency_array)

    def set_calibration_parameters(self, **params):
        self.params.update({key[len(self.prefix):]: params[key] for key in params
                            if self.prefix in key})

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class CubicSpline(Recalibrate):

    name = 'cubic_spline'

    def __init__(self, prefix, minimum_frequency, maximum_frequency, n_points):
        """
        Cubic spline recalibration

        see https://dcc.ligo.org/DocDB/0116/T1400682/001/calnote.pdf

        This assumes the spline points follow
        np.logspace(np.log(minimum_frequency), np.log(maximum_frequency), n_points)

        Parameters
        ==========
        prefix: str
            Prefix on parameters relating to the calibration.
        minimum_frequency: float
            minimum frequency of spline points
        maximum_frequency: float
            maximum frequency of spline points
        n_points: int
            number of spline points
        """
        super(CubicSpline, self).__init__(prefix=prefix)
        if n_points < 4:
            raise ValueError('Cubic spline calibration requires at least 4 spline nodes.')
        self.n_points = n_points
        self.minimum_frequency = minimum_frequency
        self.maximum_frequency = maximum_frequency
        self._log_spline_points = np.linspace(
            np.log10(minimum_frequency), np.log10(maximum_frequency), n_points)

    @property
    def log_spline_points(self):
        return self._log_spline_points

    def __repr__(self):
        return self.__class__.__name__ + '(prefix=\'{}\', minimum_frequency={}, maximum_frequency={}, n_points={})'\
            .format(self.prefix, self.minimum_frequency, self.maximum_frequency, self.n_points)

    def get_calibration_factor(self, frequency_array, **params):
        """Apply calibration model

        Parameters
        ==========
        frequency_array: array-like
            The frequency values to calculate the calibration factor for.
        prefix: str
            Prefix for calibration parameter names
        params : dict
            Dictionary of sampling parameters which includes
            calibration parameters.

        Returns
        =======
        calibration_factor : array-like
            The factor to multiply the strain by.
        """
        self.set_calibration_parameters(**params)
        amplitude_parameters = [self.params['amplitude_{}'.format(ii)]
                                for ii in range(self.n_points)]
        delta_amplitude = interp1d(
            self.log_spline_points, amplitude_parameters, kind='cubic',
            bounds_error=False, fill_value=0)(np.log10(frequency_array))

        phase_parameters = [
            self.params['phase_{}'.format(ii)] for ii in range(self.n_points)]
        delta_phase = interp1d(
            self.log_spline_points, phase_parameters, kind='cubic',
            bounds_error=False, fill_value=0)(np.log10(frequency_array))

        calibration_factor = (1 + delta_amplitude) * (2 + 1j * delta_phase) / (2 - 1j * delta_phase)

        return calibration_factor


def build_calibration_lookup(
    interferometers,
    lookup_files=None,
    priors=None,
    number_of_response_curves=1000,
    starting_index=0,
):
    if lookup_files is None and priors is None:
        raise ValueError(
            "One of calibration_lookup_table or priors must be specified for "
            "building calibration marginalization lookup table."
        )
    elif lookup_files is None:
        lookup_files = dict()

    draws = dict()
    parameters = dict()
    for interferometer in interferometers:
        name = interferometer.name
        frequencies = interferometer.frequency_array
        frequencies = frequencies[interferometer.frequency_mask]
        filename = lookup_files.get(name, f"{name}_calibration_file.h5")

        if os.path.exists(filename):
            draws[name], parameters[name] = read_calibration_file(
                filename,
                frequencies,
                number_of_response_curves,
                starting_index,
            )
        else:
            if priors is None:
                raise ValueError(
                    "Priors must be passed to generate calibration response curves "
                    "for cubic spline."
                )
            draws[name], parameters[name] = _generate_calibration_draws(
                interferometer=interferometer,
                priors=priors,
                n_curves=number_of_response_curves,
            )
            write_calibration_file(filename, frequencies, draws[name], parameters[name])

        interferometer.calibration_model = Recalibrate()

    return draws, parameters


def _generate_calibration_draws(interferometer, priors, n_curves):
    name = interferometer.name
    frequencies = interferometer.frequency_array
    frequencies = frequencies[interferometer.frequency_mask]
    calibration_priors = PriorDict()
    for key in priors.keys():
        if "recalib" in key and name in key:
            calibration_priors[key] = copy.copy(priors[key])

    parameters = pd.DataFrame(calibration_priors.sample(n_curves))

    draws = np.array(curves_from_spline_and_prior(
        parameters=parameters,
        label=name,
        n_points=interferometer.calibration_model.n_points,
        frequency_array=frequencies,
        n_curves=n_curves,
    ))
    return draws, parameters


def curves_from_spline_and_prior(parameters, label, n_points, frequency_array, n_curves):
    spline = CubicSpline(
        prefix=f"recalib_{label}_",
        minimum_frequency=frequency_array[0],
        maximum_frequency=frequency_array[-1],
        n_points=n_points,
    )
    curves = list()
    for ii in range(n_curves):
        curves.append(spline.get_calibration_factor(
            frequency_array=frequency_array,
            **parameters.iloc[ii]
        ))
    return curves

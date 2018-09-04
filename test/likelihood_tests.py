from __future__ import absolute_import
import tupak
from tupak.core import prior
from tupak.core.result import Result
import unittest
from mock import MagicMock
import mock
import numpy as np
import inspect
import os
import copy


class TestLikelihoodBase(unittest.TestCase):

    def setUp(self):
        self.likelihood = tupak.core.likelihood.Likelihood()

    def tearDown(self):
        del self.likelihood

    def test_repr(self):
        self.likelihood = tupak.core.likelihood.Likelihood(parameters=['a', 'b'])
        expected = 'Likelihood(parameters=[\'a\', \'b\'])'
        self.assertEqual(expected, repr(self.likelihood))

    def test_base_log_likelihood(self):
        self.assertTrue(np.isnan(self.likelihood.log_likelihood()))

    def test_base_noise_log_likelihood(self):
        self.assertTrue(np.isnan(self.likelihood.noise_log_likelihood()))

    def test_base_log_likelihood_ratio(self):
        self.assertTrue(np.isnan(self.likelihood.log_likelihood_ratio()))


class TestAnalytical1DLikelihood(unittest.TestCase):

    def setUp(self):
        self.x = np.arange(start=0, stop=100, step=1)
        self.y = np.arange(start=0, stop=100, step=1)

        def test_func(x, parameter1, parameter2):
            return parameter1 * x + parameter2

        self.func = test_func
        self.parameter1_value = 4
        self.parameter2_value = 7
        self.analytical_1d_likelihood = tupak.likelihood.Analytical1DLikelihood(x=self.x, y=self.y, func=self.func)
        self.analytical_1d_likelihood.parameters['parameter1'] = self.parameter1_value
        self.analytical_1d_likelihood.parameters['parameter2'] = self.parameter2_value

    def tearDown(self):
        del self.x
        del self.y
        del self.func
        del self.analytical_1d_likelihood
        del self.parameter1_value
        del self.parameter2_value

    def test_init_x(self):
        self.assertTrue(np.array_equal(self.x, self.analytical_1d_likelihood.x))

    def test_set_x_to_array(self):
        new_x = np.arange(start=0, stop=50, step=2)
        self.analytical_1d_likelihood.x = new_x
        self.assertTrue(np.array_equal(new_x, self.analytical_1d_likelihood.x))

    def test_set_x_to_int(self):
        new_x = 5
        self.analytical_1d_likelihood.x = new_x
        expected_x = np.array([new_x])
        self.assertTrue(np.array_equal(expected_x, self.analytical_1d_likelihood.x))

    def test_set_x_to_float(self):
        new_x = 5.3
        self.analytical_1d_likelihood.x = new_x
        expected_x = np.array([new_x])
        self.assertTrue(np.array_equal(expected_x, self.analytical_1d_likelihood.x))

    def test_init_y(self):
        self.assertTrue(np.array_equal(self.y, self.analytical_1d_likelihood.y))

    def test_set_y_to_array(self):
        new_y = np.arange(start=0, stop=50, step=2)
        self.analytical_1d_likelihood.y = new_y
        self.assertTrue(np.array_equal(new_y, self.analytical_1d_likelihood.y))

    def test_set_y_to_int(self):
        new_y = 5
        self.analytical_1d_likelihood.y = new_y
        expected_y = np.array([new_y])
        self.assertTrue(np.array_equal(expected_y, self.analytical_1d_likelihood.y))

    def test_set_y_to_float(self):
        new_y = 5.3
        self.analytical_1d_likelihood.y = new_y
        expected_y = np.array([new_y])
        self.assertTrue(np.array_equal(expected_y, self.analytical_1d_likelihood.y))

    def test_init_func(self):
        self.assertEqual(self.func, self.analytical_1d_likelihood.func)

    def test_set_func(self):
        def new_func(x):
            return x
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            self.analytical_1d_likelihood.func = new_func

    def test_parameters(self):
        expected_parameters = dict(parameter1=self.parameter1_value,
                                   parameter2=self.parameter2_value)
        self.assertDictEqual(expected_parameters, self.analytical_1d_likelihood.parameters)

    def test_n(self):
        self.assertEqual(len(self.x), self.analytical_1d_likelihood.n)

    def test_set_n(self):
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            self.analytical_1d_likelihood.n = 2

    def test_model_parameters(self):
        sigma = 5
        self.analytical_1d_likelihood.sigma = sigma
        self.analytical_1d_likelihood.parameters['sigma'] = sigma
        expected_model_parameters = dict(parameter1=self.parameter1_value,
                                         parameter2=self.parameter2_value)
        self.assertDictEqual(expected_model_parameters, self.analytical_1d_likelihood.model_parameters)

    def test_repr(self):
        expected = 'Analytical1DLikelihood(x={}, y={}, func={})'.format(self.x, self.y, self.func.__name__)
        self.assertEqual(expected, repr(self.analytical_1d_likelihood))


class TestGaussianLikelihood(unittest.TestCase):

    def setUp(self):
        self.N = 100
        self.sigma = 0.1
        self.x = np.linspace(0, 1, self.N)
        self.y = 2 * self.x + 1 + np.random.normal(0, self.sigma, self.N)

        def test_function(x, m, c):
            return m * x + c

        self.function = test_function

    def tearDown(self):
        del self.N
        del self.sigma
        del self.x
        del self.y
        del self.function

    def test_known_sigma(self):
        likelihood = tupak.core.likelihood.GaussianLikelihood(
            self.x, self.y, self.function, self.sigma)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        likelihood.log_likelihood()
        self.assertEqual(likelihood.sigma, self.sigma)

    def test_known_array_sigma(self):
        sigma_array = np.ones(self.N) * self.sigma
        likelihood = tupak.core.likelihood.GaussianLikelihood(
            self.x, self.y, self.function, sigma_array)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        likelihood.log_likelihood()
        self.assertTrue(type(likelihood.sigma) == type(sigma_array))
        self.assertTrue(all(likelihood.sigma == sigma_array))

    def test_set_sigma_None(self):
        likelihood = tupak.core.likelihood.GaussianLikelihood(
            self.x, self.y, self.function, sigma=None)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        self.assertTrue(likelihood.sigma is None)
        with self.assertRaises(TypeError):
            likelihood.log_likelihood()

    def test_sigma_float(self):
        likelihood = tupak.core.likelihood.GaussianLikelihood(
            self.x, self.y, self.function, sigma=None)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        likelihood.parameters['sigma'] = 1
        likelihood.log_likelihood()
        self.assertTrue(likelihood.sigma is None)


class TestStudentTLikelihood(unittest.TestCase):

    def setUp(self):
        self.N = 100
        self.nu = self.N - 2
        self.sigma = 1
        self.x = np.linspace(0, 1, self.N)
        self.y = 2 * self.x + 1 + np.random.normal(0, self.sigma, self.N)

        def test_function(x, m, c):
            return m * x + c

        self.function = test_function

    def tearDown(self):
        del self.N
        del self.sigma
        del self.x
        del self.y
        del self.function

    def test_known_sigma(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, self.nu, self.sigma)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        likelihood.log_likelihood()
        self.assertEqual(likelihood.sigma, self.sigma)

    def test_set_nu_none(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, nu=None)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        self.assertTrue(likelihood.nu is None)

    def test_log_likelihood_nu_none(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, nu=None)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        with self.assertRaises((ValueError, TypeError)):
            # ValueError in Python2, TypeError in Python3
            likelihood.log_likelihood()

    def test_log_likelihood_nu_zero(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, nu=0)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        with self.assertRaises(ValueError):
            likelihood.log_likelihood()

    def test_log_likelihood_nu_negative(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, nu=-1)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        with self.assertRaises(ValueError):
            likelihood.log_likelihood()

    def test_setting_nu_positive_does_not_change_class_attribute(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, nu=None)
        likelihood.parameters['m'] = 2
        likelihood.parameters['c'] = 0
        likelihood.parameters['nu'] = 98
        self.assertTrue(likelihood.nu is None)

    def test_lam(self):
        likelihood = tupak.core.likelihood.StudentTLikelihood(
            self.x, self.y, self.function, nu=0, sigma=0.5)

        self.assertAlmostEqual(4.0, likelihood.lam)


class TestPoissonLikelihood(unittest.TestCase):

    def setUp(self):
        self.N = 100
        self.mu = 5
        self.x = np.linspace(0, 1, self.N)
        self.y = np.random.poisson(self.mu, self.N)
        self.yfloat = np.copy(self.y) * 1.
        self.yneg = np.copy(self.y)
        self.yneg[0] = -1

        def test_function(x, c):
            return c

        def test_function_array(x, c):
            return np.ones(len(x)) * c

        self.function = test_function
        self.function_array = test_function_array
        self.poisson_likelihood = tupak.core.likelihood.PoissonLikelihood(self.x, self.y, self.function)

    def tearDown(self):
        del self.N
        del self.mu
        del self.x
        del self.y
        del self.yfloat
        del self.yneg
        del self.function
        del self.function_array
        del self.poisson_likelihood

    def test_init_y_non_integer(self):
        with self.assertRaises(ValueError):
            tupak.core.likelihood.PoissonLikelihood(
                self.x, self.yfloat, self.function)

    def test_init__y_negative(self):
        with self.assertRaises(ValueError):
            tupak.core.likelihood.PoissonLikelihood(
                self.x, self.yneg, self.function)

    def test_neg_rate(self):
        self.poisson_likelihood.parameters['c'] = -2
        with self.assertRaises(ValueError):
            self.poisson_likelihood.log_likelihood()

    def test_neg_rate_array(self):
        likelihood = tupak.core.likelihood.PoissonLikelihood(
            self.x, self.y, self.function_array)
        likelihood.parameters['c'] = -2
        with self.assertRaises(ValueError):
            likelihood.log_likelihood()

    def test_init_y(self):
        self.assertTrue(np.array_equal(self.y, self.poisson_likelihood.y))

    def test_set_y_to_array(self):
        new_y = np.arange(start=0, stop=50, step=2)
        self.poisson_likelihood.y = new_y
        self.assertTrue(np.array_equal(new_y, self.poisson_likelihood.y))

    def test_set_y_to_positive_int(self):
        new_y = 5
        self.poisson_likelihood.y = new_y
        expected_y = np.array([new_y])
        self.assertTrue(np.array_equal(expected_y, self.poisson_likelihood.y))

    def test_set_y_to_negative_int(self):
        with self.assertRaises(ValueError):
            self.poisson_likelihood.y = -5

    def test_set_y_to_float(self):
        with self.assertRaises(ValueError):
            self.poisson_likelihood.y = 5.3

    def test_log_likelihood_wrong_func_return_type(self):
        poisson_likelihood = tupak.likelihood.PoissonLikelihood(x=self.x, y=self.y, func=lambda x: 'test')
        with self.assertRaises(ValueError):
            poisson_likelihood.log_likelihood()

    def test_log_likelihood_negative_func_return_element(self):
        poisson_likelihood = tupak.likelihood.PoissonLikelihood(x=self.x, y=self.y, func=lambda x: np.array([3, 6, -2]))
        with self.assertRaises(ValueError):
            poisson_likelihood.log_likelihood()

    def test_log_likelihood_zero_func_return_element(self):
        poisson_likelihood = tupak.likelihood.PoissonLikelihood(x=self.x, y=self.y, func=lambda x: np.array([3, 6, 0]))
        self.assertEqual(-np.inf, poisson_likelihood.log_likelihood())

    def test_log_likelihood_dummy(self):
        """ Merely tests if it goes into the right if else bracket """
        poisson_likelihood = tupak.likelihood.PoissonLikelihood(x=self.x, y=self.y,
                                                                func=lambda x: np.linspace(1, 100, self.N))
        with mock.patch('numpy.sum') as m:
            m.return_value = 1
            self.assertEqual(0, poisson_likelihood.log_likelihood())


class TestExponentialLikelihood(unittest.TestCase):

    def setUp(self):
        self.N = 100
        self.mu = 5
        self.x = np.linspace(0, 1, self.N)
        self.y = np.random.exponential(self.mu, self.N)
        self.yneg = np.copy(self.y)
        self.yneg[0] = -1.

        def test_function(x, c):
            return c

        def test_function_array(x, c):
            return c * np.ones(len(x))

        self.function = test_function
        self.function_array = test_function_array
        self.exponential_likelihood = tupak.core.likelihood.ExponentialLikelihood(x=self.x, y=self.y,
                                                                                  func=self.function)

    def tearDown(self):
        del self.N
        del self.mu
        del self.x
        del self.y
        del self.yneg
        del self.function
        del self.function_array

    def test_negative_data(self):
        with self.assertRaises(ValueError):
            tupak.core.likelihood.ExponentialLikelihood(self.x, self.yneg, self.function)

    def test_negative_function(self):
        likelihood = tupak.core.likelihood.ExponentialLikelihood(
            self.x, self.y, self.function)
        likelihood.parameters['c'] = -1
        self.assertEqual(likelihood.log_likelihood(), -np.inf)

    def test_negative_array_function(self):
        likelihood = tupak.core.likelihood.ExponentialLikelihood(
            self.x, self.y, self.function_array)
        likelihood.parameters['c'] = -1
        self.assertEqual(likelihood.log_likelihood(), -np.inf)

    def test_init_y(self):
        self.assertTrue(np.array_equal(self.y, self.exponential_likelihood.y))

    def test_set_y_to_array(self):
        new_y = np.arange(start=0, stop=50, step=2)
        self.exponential_likelihood.y = new_y
        self.assertTrue(np.array_equal(new_y, self.exponential_likelihood.y))

    def test_set_y_to_positive_int(self):
        new_y = 5
        self.exponential_likelihood.y = new_y
        expected_y = np.array([new_y])
        self.assertTrue(np.array_equal(expected_y, self.exponential_likelihood.y))

    def test_set_y_to_negative_int(self):
        with self.assertRaises(ValueError):
            self.exponential_likelihood.y = -5

    def test_set_y_to_positive_float(self):
        new_y = 5.3
        self.exponential_likelihood.y = new_y
        self.assertTrue(np.array_equal(np.array([5.3]), self.exponential_likelihood.y))

    def test_set_y_to_negative_float(self):
        with self.assertRaises(ValueError):
            self.exponential_likelihood.y = -5.3

    def test_set_y_to_nd_array_with_negative_element(self):
        with self.assertRaises(ValueError):
            self.exponential_likelihood.y = np.array([4.3, -1.2, 4])

    def test_log_likelihood_default(self):
        """ Merely tests that it ends up at the right place in the code """
        exponential_likelihood = tupak.core.likelihood.ExponentialLikelihood(x=self.x, y=self.y,
                                                                             func=lambda x: np.array([4.2]))
        with mock.patch('numpy.sum') as m:
            m.return_value = 3
            self.assertEqual(-3, exponential_likelihood.log_likelihood())


if __name__ == '__main__':
    unittest.main()

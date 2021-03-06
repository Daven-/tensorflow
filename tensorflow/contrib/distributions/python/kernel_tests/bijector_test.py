# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for Bijector."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math

import numpy as np
import tensorflow as tf

bijectors = tf.contrib.distributions.bijector
rng = np.random.RandomState(42)


class BaseBijectorTest(tf.test.TestCase):
  """Tests properties of the Bijector base-class."""

  def testBijector(self):
    with self.test_session():
      with self.assertRaisesRegexp(
          TypeError,
          ("Can't instantiate abstract class Bijector "
           "with abstract methods __init__")):
        bijectors.Bijector()


class IdentityBijectorTest(tf.test.TestCase):
  """Tests the correctness of the Y = g(X) = X transformation."""

  def testBijector(self):
    with self.test_session():
      bijector = bijectors.Identity()
      self.assertEqual("Identity", bijector.name)
      x = [[[0.],
            [1.]]]
      self.assertAllEqual(x, bijector.forward(x).eval())
      self.assertAllEqual(x, bijector.inverse(x).eval())
      self.assertAllEqual(0., bijector.inverse_log_det_jacobian(x).eval())
      rev, jac = bijector.inverse_and_inverse_log_det_jacobian(x)
      self.assertAllEqual(x, rev.eval())
      self.assertAllEqual(0., jac.eval())


class ExpBijectorTest(tf.test.TestCase):
  """Tests the correctness of the Y = g(X) = exp(X) transformation."""

  def testBijector(self):
    with self.test_session():
      bijector = bijectors.Exp(event_ndims=1)
      self.assertEqual("Exp", bijector.name)
      x = [[[1.],
            [2.]]]
      self.assertAllClose(np.exp(x), bijector.forward(x).eval())
      self.assertAllClose(np.log(x), bijector.inverse(x).eval())
      self.assertAllClose([[0., -math.log(2.)]],
                          bijector.inverse_log_det_jacobian(x).eval())
      rev, jac = bijector.inverse_and_inverse_log_det_jacobian(x)
      self.assertAllClose(np.log(x), rev.eval())
      self.assertAllClose([[0., -math.log(2.)]], jac.eval())


class InlineBijectorTest(tf.test.TestCase):
  """Tests the correctness of the inline constructed bijector."""

  def testBijector(self):
    with self.test_session():
      exp = bijectors.Exp(event_ndims=1)
      inline = bijectors.Inline(
          forward_fn=tf.exp,
          inverse_fn=tf.log,
          inverse_log_det_jacobian_fn=(
              lambda y: -tf.reduce_sum(tf.log(x), reduction_indices=-1)),
          name="Exp")

      self.assertEqual(exp.name, inline.name)
      x = [[[1., 2.],
            [3., 4.],
            [5., 6.]]]
      self.assertAllClose(exp.forward(x).eval(), inline.forward(x).eval())
      self.assertAllClose(exp.inverse(x).eval(), inline.inverse(x).eval())
      self.assertAllClose(exp.inverse_log_det_jacobian(x).eval(),
                          inline.inverse_log_det_jacobian(x).eval())


class ScaleAndShiftBijectorTest(tf.test.TestCase):
  """Tests the correctness of the Y = scale * x + loc transformation."""

  def testProperties(self):
    with self.test_session():
      mu = -1.
      sigma = 2.
      bijector = bijectors.ScaleAndShift(
          loc=mu, scale=sigma)
      self.assertEqual("ScaleAndShift", bijector.name)

  def testNoBatchScalar(self):
    with self.test_session() as sess:
      def static_run(fun, x):
        return fun(x).eval()

      def dynamic_run(fun, x_value):
        x_value = np.array(x_value)
        x = tf.placeholder(tf.float32, name="x")
        return sess.run(fun(x), feed_dict={x: x_value})

      for run in (static_run, dynamic_run):
        mu = -1.
        sigma = 2.  # Scalar.
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma)
        self.assertEqual(0, bijector.shaper.batch_ndims.eval())  # "no batches"
        self.assertEqual(0, bijector.shaper.event_ndims.eval())  # "is scalar"
        x = [1., 2, 3]  # Three scalar samples (no batches).
        self.assertAllClose([1., 3, 5], run(bijector.forward, x))
        self.assertAllClose([1., 1.5, 2.], run(bijector.inverse, x))
        self.assertAllClose([-math.log(2.)],
                            run(bijector.inverse_log_det_jacobian, x))

  def testWeirdSampleNoBatchScalar(self):
    with self.test_session() as sess:
      def static_run(fun, x):
        return fun(x).eval()

      def dynamic_run(fun, x_value):
        x_value = np.array(x_value)
        x = tf.placeholder(tf.float32, name="x")
        return sess.run(fun(x), feed_dict={x: x_value})

      for run in (static_run, dynamic_run):
        mu = -1.
        sigma = 2.  # Scalar.
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma)
        self.assertEqual(0, bijector.shaper.batch_ndims.eval())  # "no batches"
        self.assertEqual(0, bijector.shaper.event_ndims.eval())  # "is scalar"
        x = [[1., 2, 3],
             [4, 5, 6]]  # Weird sample shape.
        self.assertAllClose([[1., 3, 5],
                             [7, 9, 11]],
                            run(bijector.forward, x))
        self.assertAllClose([[1., 1.5, 2.],
                             [2.5, 3, 3.5]],
                            run(bijector.inverse, x))
        self.assertAllClose([-math.log(2.)],
                            run(bijector.inverse_log_det_jacobian, x))

  def testOneBatchScalar(self):
    with self.test_session() as sess:
      def static_run(fun, x):
        return fun(x).eval()

      def dynamic_run(fun, x_value):
        x_value = np.array(x_value)
        x = tf.placeholder(tf.float32, name="x")
        return sess.run(fun(x), feed_dict={x: x_value})

      for run in (static_run, dynamic_run):
        mu = [1.]
        sigma = [1.]  # One batch, scalar.
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma)
        self.assertEqual(
            1, bijector.shaper.batch_ndims.eval())  # "one batch dim"
        self.assertEqual(
            0, bijector.shaper.event_ndims.eval())  # "is scalar"
        x = [1.]  # One sample from one batches.
        self.assertAllClose([2.], run(bijector.forward, x))
        self.assertAllClose([0.], run(bijector.inverse, x))
        self.assertAllClose([0.],
                            run(bijector.inverse_log_det_jacobian, x))

  def testTwoBatchScalar(self):
    with self.test_session() as sess:
      def static_run(fun, x):
        return fun(x).eval()

      def dynamic_run(fun, x_value):
        x_value = np.array(x_value)
        x = tf.placeholder(tf.float32, name="x")
        return sess.run(fun(x), feed_dict={x: x_value})

      for run in (static_run, dynamic_run):
        mu = [1., -1]
        sigma = [1., 1]  # Univariate, two batches.
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma)
        self.assertEqual(
            1, bijector.shaper.batch_ndims.eval())  # "one batch dim"
        self.assertEqual(
            0, bijector.shaper.event_ndims.eval())  # "is scalar"
        x = [1., 1]  # One sample from each of two batches.
        self.assertAllClose([2., 0], run(bijector.forward, x))
        self.assertAllClose([0., 2], run(bijector.inverse, x))
        self.assertAllClose([0., 0],
                            run(bijector.inverse_log_det_jacobian, x))

  def testNoBatchMultivariate(self):
    with self.test_session() as sess:
      def static_run(fun, x):
        return fun(x).eval()

      def dynamic_run(fun, x_value):
        x_value = np.array(x_value)
        x = tf.placeholder(tf.float32, name="x")
        return sess.run(fun(x), feed_dict={x: x_value})

      for run in (static_run, dynamic_run):
        mu = [1., -1]
        sigma = np.eye(2, dtype=np.float32)
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma, event_ndims=1)
        self.assertEqual(0, bijector.shaper.batch_ndims.eval())  # "no batches"
        self.assertEqual(1, bijector.shaper.event_ndims.eval())  # "is vector"
        x = [1., 1]
        self.assertAllClose([2., 0], run(bijector.forward, x))
        self.assertAllClose([0., 2], run(bijector.inverse, x))
        self.assertAllClose([0.], run(bijector.inverse_log_det_jacobian, x))

        x = [[1., 1],
             [-1., -1]]
        self.assertAllClose([[2., 0],
                             [0, -2]],
                            run(bijector.forward, x))
        self.assertAllClose([[0., 2],
                             [-2., 0]],
                            run(bijector.inverse, x))
        self.assertAllClose([0.], run(bijector.inverse_log_det_jacobian, x))

      # When mu is a scalar and x is multivariate then the location is
      # broadcast.
      for run in (static_run, dynamic_run):
        mu = 1.
        sigma = np.eye(2, dtype=np.float32)
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma, event_ndims=1)
        self.assertEqual(0, bijector.shaper.batch_ndims.eval())  # "no batches"
        self.assertEqual(1, bijector.shaper.event_ndims.eval())  # "is vector"
        x = [1., 1]
        self.assertAllClose([2., 2], run(bijector.forward, x))
        self.assertAllClose([0., 0], run(bijector.inverse, x))
        self.assertAllClose([0.], run(bijector.inverse_log_det_jacobian, x))
        x = [[1., 1]]
        self.assertAllClose([[2., 2]], run(bijector.forward, x))
        self.assertAllClose([[0., 0]], run(bijector.inverse, x))
        self.assertAllClose([0.], run(bijector.inverse_log_det_jacobian, x))

  def testNoBatchMultivariateFullDynamic(self):
    with self.test_session() as sess:
      x = tf.placeholder(tf.float32, name="x")
      mu = tf.placeholder(tf.float32, name="mu")
      sigma = tf.placeholder(tf.float32, name="sigma")
      event_ndims = tf.placeholder(tf.int32, name="event_ndims")

      x_value = np.array([[1., 1]], dtype=np.float32)
      mu_value = np.array([1., -1], dtype=np.float32)
      sigma_value = np.eye(2, dtype=np.float32)
      event_ndims_value = np.array(1, dtype=np.int32)
      feed_dict = {x: x_value, mu: mu_value, sigma: sigma_value, event_ndims:
                   event_ndims_value}

      bijector = bijectors.ScaleAndShift(
          loc=mu, scale=sigma, event_ndims=event_ndims)
      self.assertEqual(0, sess.run(bijector.shaper.batch_ndims, feed_dict))
      self.assertEqual(1, sess.run(bijector.shaper.event_ndims, feed_dict))
      self.assertAllClose([[2., 0]], sess.run(bijector.forward(x), feed_dict))
      self.assertAllClose([[0., 2]], sess.run(bijector.inverse(x), feed_dict))
      self.assertAllClose(
          [0.], sess.run(bijector.inverse_log_det_jacobian(x), feed_dict))

  def testBatchMultivariate(self):
    with self.test_session() as sess:
      def static_run(fun, x):
        return fun(x).eval()

      def dynamic_run(fun, x_value):
        x_value = np.array(x_value, dtype=np.float32)
        x = tf.placeholder(tf.float32, name="x")
        return sess.run(fun(x), feed_dict={x: x_value})

      for run in (static_run, dynamic_run):
        mu = [[1., -1]]
        sigma = np.array([np.eye(2, dtype=np.float32)])
        bijector = bijectors.ScaleAndShift(
            loc=mu, scale=sigma, event_ndims=1)
        self.assertEqual(
            1, bijector.shaper.batch_ndims.eval())  # "one batch dim"
        self.assertEqual(
            1, bijector.shaper.event_ndims.eval())  # "is vector"
        x = [[[1., 1]]]
        self.assertAllClose([[[2., 0]]], run(bijector.forward, x))
        self.assertAllClose([[[0., 2]]], run(bijector.inverse, x))
        self.assertAllClose([0.], run(bijector.inverse_log_det_jacobian, x))

  def testBatchMultivariateFullDynamic(self):
    with self.test_session() as sess:
      x = tf.placeholder(tf.float32, name="x")
      mu = tf.placeholder(tf.float32, name="mu")
      sigma = tf.placeholder(tf.float32, name="sigma")
      event_ndims = tf.placeholder(tf.int32, name="event_ndims")

      x_value = np.array([[[1., 1]]], dtype=np.float32)
      mu_value = np.array([[1., -1]], dtype=np.float32)
      sigma_value = np.array([np.eye(2, dtype=np.float32)])
      event_ndims_value = np.array(1, dtype=np.int32)
      feed_dict = {x: x_value, mu: mu_value, sigma: sigma_value,
                   event_ndims: event_ndims_value}

      bijector = bijectors.ScaleAndShift(
          loc=mu, scale=sigma, event_ndims=event_ndims)
      self.assertEqual(1, sess.run(bijector.shaper.batch_ndims, feed_dict))
      self.assertEqual(1, sess.run(bijector.shaper.event_ndims, feed_dict))
      self.assertAllClose([[[2., 0]]], sess.run(bijector.forward(x), feed_dict))
      self.assertAllClose([[[0., 2]]], sess.run(bijector.inverse(x), feed_dict))
      self.assertAllClose(
          [0.], sess.run(bijector.inverse_log_det_jacobian(x), feed_dict))


class SoftplusBijectorTest(tf.test.TestCase):
  """Tests the correctness of the Y = g(X) = Log[1 + exp(X)] transformation."""

  def _softplus(self, x):
    return np.log(1 + np.exp(x))

  def _softplus_inverse(self, y):
    return np.log(np.exp(y) - 1)

  def _softplus_ildj_before_reduction(self, y):
    """Inverse log det jacobian, before being reduced."""
    return -np.log(1 - np.exp(-y))

  def testBijectorForwardInverseEventDimsZero(self):
    with self.test_session():
      bijector = bijectors.Softplus(event_ndims=0)
      self.assertEqual("Softplus", bijector.name)
      x = 2 * rng.randn(2, 10)
      y = self._softplus(x)

      self.assertAllClose(y, bijector.forward(x).eval())
      self.assertAllClose(x, bijector.inverse(y).eval())
      self.assertAllClose(
          x, bijector.inverse_and_inverse_log_det_jacobian(y)[0].eval())

  def testBijectorLogDetJacobianEventDimsZero(self):
    with self.test_session():
      bijector = bijectors.Softplus(event_ndims=0)
      y = 2 * rng.rand(2, 10)
      # No reduction needed if event_dims = 0.
      ildj = self._softplus_ildj_before_reduction(y)

      self.assertAllClose(ildj, bijector.inverse_log_det_jacobian(y).eval())
      self.assertAllClose(
          ildj, bijector.inverse_and_inverse_log_det_jacobian(y)[1].eval())

  def testBijectorForwardInverseEventDimsOne(self):
    with self.test_session():
      bijector = bijectors.Softplus(event_ndims=1)
      self.assertEqual("Softplus", bijector.name)
      x = 2 * rng.randn(2, 10)
      y = self._softplus(x)

      self.assertAllClose(y, bijector.forward(x).eval())
      self.assertAllClose(x, bijector.inverse(y).eval())
      self.assertAllClose(
          x, bijector.inverse_and_inverse_log_det_jacobian(y)[0].eval())

  def testBijectorLogDetJacobianEventDimsOne(self):
    with self.test_session():
      bijector = bijectors.Softplus(event_ndims=1)
      y = 2 * rng.rand(2, 10)
      ildj_before = self._softplus_ildj_before_reduction(y)
      ildj = np.sum(ildj_before, axis=1)

      self.assertAllClose(ildj, bijector.inverse_log_det_jacobian(y).eval())
      self.assertAllClose(
          ildj, bijector.inverse_and_inverse_log_det_jacobian(y)[1].eval())


if __name__ == "__main__":
  tf.test.main()

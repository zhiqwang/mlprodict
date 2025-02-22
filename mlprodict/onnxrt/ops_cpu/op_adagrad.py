# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
import numpy
from ..shape_object import ShapeObject
from ._op import OpRun


def _apply_adagrad(r, t, x, g, h, norm_coefficient,
                   epsilon, decay_factor):
    # Compute adjusted learning-rate.
    r_ = r / (1 + t * decay_factor)
    # Add gradient of regularization term.
    g_regularized = norm_coefficient * x + g
    # Update squared accumulated gradient.
    h_new = h + g_regularized * g_regularized
    # Compute ADAGRAD's gradient scaling factors
    h_sqrt = numpy.sqrt(h_new) + epsilon
    # Apply ADAGRAD update rule.
    x_new = x - r_ * g_regularized / h_sqrt
    return (x_new, h_new)


class Adagrad(OpRun):

    atts = {'decay_factor': 0.,
            'epsilon': 9.999999974752427e-07,
            'norm_coefficient': 0.}

    def __init__(self, onnx_node, desc=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=Adagrad.atts,
                       **options)

    def _run(self, *data, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        if len(data) == 5:
            return self._run1(*data)
        n = (len(data) - 2) // 3
        xs = []
        hs = []
        for i in range(0, n):
            a, b = self._run1(*data[:2], data[2 + i],
                              data[2 + n + i], data[2 + n * 2 + i])
            xs.append(a)
            hs.append(b)
        return tuple(xs + hs)

    def _run1(self, r, t, x, g, h):  # pylint: disable=W0221
        x_new, h_new = _apply_adagrad(
            r, t, x, g, h, self.norm_coefficient, self.epsilon, self.decay_factor)
        return x_new, h_new

    def _infer_shapes(self, i, *data):  # pylint: disable=W0221
        n = (len(data) - 1) // 3
        return (ShapeObject(None, i.dtype), ShapeObject(None, i.dtype)) * n

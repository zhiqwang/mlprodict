# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
import numpy
from onnx.mapping import TENSOR_TYPE_TO_NP_TYPE
from ._op import OpRun
from ..shape_object import ShapeObject


class _CommonRandom(OpRun):
    """
    Common methods to all random operators.
    """

    def __init__(self, *args, **kwargs):
        OpRun.__init__(self, *args, **kwargs)

    def _dtype(self, *data):
        res = None
        if len(data) == 0:
            res = self.numpy_type
        elif self.numpy_type is not None:
            res = self.numpy_type
        elif hasattr(data[0], 'dtype'):
            res = data[0].dtype
        if res is None:
            raise RuntimeError(  # pragma: no cover
                "dtype cannot be None for operator %s, "
                "self.numpy_type=%r, type(data[0])=%r."
                "" % (self.__class__.__name__,
                      self.numpy_type, type(data[0])))
        return res

    def _infer_shapes(self, *data):  # pylint: disable=W0221
        return (ShapeObject(None, self._dtype(*data)), )

    def _infer_types(self, *data):  # pylint: disable=W0221
        return (self._dtype(*data), )

    def _infer_sizes(self, *args, **kwargs):
        res = self.run(*args, **kwargs)
        return (dict(temp=0), ) + res


class RandomUniform(_CommonRandom):

    atts = {'dtype': 1,
            'low': 0.,
            'high': 1.,
            'seed': None,
            'shape': []}

    def __init__(self, onnx_node, desc=None, **options):
        _CommonRandom.__init__(self, onnx_node, desc=desc,
                               expected_attributes=RandomUniform.atts,
                               **options)
        if len(self.shape) == 0:
            raise ValueError(  # pragma: no cover
                "shape cannot be empty for operator %s."
                "" % self.__class__.__name__)
        self.numpy_type = TENSOR_TYPE_TO_NP_TYPE[self.dtype]

    def _run(self, *args):  # pylint: disable=W0221
        if len(args) != 0:
            raise RuntimeError(  # pragma: no cover
                "Operator %s cannot have inputs." % self.__class__.__name__)
        dtype = self._dtype(*args)
        res = numpy.random.rand(*self.shape).astype(dtype)
        res *= (self.high - self.low)
        res += self.low
        return (res.astype(dtype), )

    def to_python(self, inputs):
        lines = [
            'return (numpy.random.rand(*%r).astype(numpy.%s) * (%f - %f)) + %f' % (
                list(self.shape), self.numpy_type, self.high, self.low, self.low)]
        return ("import numpy", "\n".join(lines))


class RandomUniformLike(_CommonRandom):

    atts = {'low': 0.,
            'high': 1.,
            'seed': None,
            'dtype': 0}

    def __init__(self, onnx_node, desc=None, **options):
        _CommonRandom.__init__(self, onnx_node, desc=desc,
                               expected_attributes=RandomUniformLike.atts,
                               **options)
        self.numpy_type = (
            None if self.dtype == 0 else TENSOR_TYPE_TO_NP_TYPE[self.dtype])

    def _run(self, x):  # pylint: disable=W0221
        dtype = self._dtype(x)
        res = numpy.random.rand(*x.shape).astype(dtype)
        res *= (self.high - self.low)
        res += self.low
        return (res.astype(dtype), )

    def to_python(self, inputs):
        if len(inputs) > 0 and hasattr(inputs[0], 'dtype'):
            dtype = inputs[0].dtype
            shape = inputs[0].shape
        else:
            dtype = self.numpy_type or numpy.float32
            shape = (1, )
        lines = [
            'return (numpy.random.rand(*%r).astype(numpy.%s) * (%f - %f)) + %f' % (
                shape, dtype, self.high, self.low, self.low)]
        return ("import numpy", "\n".join(lines))


class RandomNormal(_CommonRandom):

    atts = {'dtype': 1,
            'mean': 0.,
            'scale': 1.,
            'seed': None,
            'shape': []}

    def __init__(self, onnx_node, desc=None, **options):
        _CommonRandom.__init__(self, onnx_node, desc=desc,
                               expected_attributes=RandomNormal.atts,
                               **options)
        if len(self.shape) == 0:
            raise ValueError(  # pragma: no cover
                "shape cannot be empty for operator %s."
                "" % self.__class__.__name__)
        self.numpy_type = TENSOR_TYPE_TO_NP_TYPE[self.dtype]

    def _run(self, *args):  # pylint: disable=W0221
        if len(args) != 0:
            raise RuntimeError(  # pragma: no cover
                "Operator %s cannot have inputs." % self.__class__.__name__)
        res = numpy.random.randn(*self.shape).astype(self.numpy_type)
        res *= self.scale
        res += self.mean
        return (res.astype(self.numpy_type), )

    def to_python(self, inputs):
        lines = [
            'return (numpy.random.randn(*%r).astype(numpy.%s) * %f) + %f' % (
                list(self.shape), self.numpy_type, self.scale, self.mean)]
        return ("import numpy", "\n".join(lines))


class RandomNormalLike(_CommonRandom):

    atts = {'dtype': 0,
            'mean': 0.,
            'scale': 1.,
            'seed': None}

    def __init__(self, onnx_node, desc=None, **options):
        _CommonRandom.__init__(self, onnx_node, desc=desc,
                               expected_attributes=RandomNormalLike.atts,
                               **options)
        self.numpy_type = (
            None if self.dtype == 0 else TENSOR_TYPE_TO_NP_TYPE[self.dtype])

    def _run(self, x):  # pylint: disable=W0221
        dtype = self._dtype(x)
        res = numpy.random.randn(*x.shape).astype(dtype)
        res *= self.scale
        res += self.mean
        return (res.astype(dtype), )

    def to_python(self, inputs):
        if len(inputs) > 0 and hasattr(inputs[0], 'dtype'):
            dtype = inputs[0].dtype
            shape = inputs[0].shape
        else:
            dtype = self.numpy_type or numpy.float32
            shape = (1, )
        lines = [
            'return (numpy.random.randn(%r).astype(numpy.%s) * %f) + %f' % (
                shape, dtype, self.scale, self.mean)]
        return ("import numpy", "\n".join(lines))

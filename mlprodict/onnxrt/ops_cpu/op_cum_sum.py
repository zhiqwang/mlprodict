# -*- encoding: utf-8 -*-
# pylint: disable=E0203,E1101,C0111
"""
@file
@brief Runtime operator.
"""
import numpy
from ._op import OpRun


class CumSum(OpRun):

    atts = {'exclusive': 0, 'reverse': 0}
    python_inputs = ['x', 'axis=None']

    def __init__(self, onnx_node, desc=None, **options):
        OpRun.__init__(self, onnx_node, desc=desc,
                       expected_attributes=CumSum.atts,
                       **options)

    def _run(self, x, *axis, attributes=None, verbose=0, fLOG=None):  # pylint: disable=W0221
        axis = None if len(axis) == 0 else axis[0]
        if axis is None:
            if self.reverse or self.exclusive:
                raise NotImplementedError(  # pragma no cover
                    'reverse=1 or exclusive=1 not implemented')
            if self.inplaces.get(0, False) and x.flags['WRITEABLE']:
                return (numpy.cumsum(x, out=x), )
            return (numpy.cumsum(x), )
        if not isinstance(axis, (numpy.int32, numpy.int64)):
            if (len(axis.shape) > 1 or
                    (len(axis.shape) > 0 and axis.shape[0] != 1)):
                raise RuntimeError(  # pragma no cover
                    "axis must be an array of one number not {} "
                    "(shape {})".format(axis, axis.shape))
            if len(axis.shape) > 0:
                axis = axis[0]  # pylint: disable=E1136
        if self.reverse:
            rev_indices = [slice(0, s) for s in x.shape]
            rev_indices[axis] = slice(None, None, -1)
            x = x[rev_indices]
        if self.exclusive:
            indices_c = [slice(0, s) for s in x.shape]
            indices_d = [slice(0, s) for s in x.shape]
            indices_c[axis] = slice(0, -1)
            indices_d[axis] = slice(1, x.shape[axis])
            res = numpy.zeros(x.shape, dtype=x.dtype)
            numpy.cumsum(x[indices_c], axis=axis, out=res[indices_d])
        else:
            if self.inplaces.get(0, False) and x.flags['WRITEABLE']:
                res = numpy.cumsum(x, axis=axis, out=x)
            else:
                res = numpy.cumsum(x, axis=axis)
        if self.reverse:
            res = res[rev_indices]
        return (res, )

    def _infer_shapes(self, x, *axis):  # pylint: disable=W0221
        return (x, )

    def _infer_types(self, x, *axis):  # pylint: disable=W0221
        return (x, )

    def _infer_sizes(self, *args, **kwargs):
        res = self.run(*args, **kwargs)
        return (dict(temp=0), ) + res

    def to_python(self, inputs):
        lines = ['if exclusive or reverse:',
                 '    raise NotImplementedError("reverse=1 or exclusive=1 not implemente")',
                 'if axis is None:',
                 '    return numpy.cumsum(x)',
                 'return numpy.cumsum(x, axis=axis[0])']
        return 'import numpy', "\n".join(lines)

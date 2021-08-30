"""
@file
@brief Numpy helpers for the conversion from onnx to numpy.
"""
import numpy


def make_slice(data, starts, ends, axes=None, steps=None):
    """
    Implements operator slice in numpy.

    :param data: input
    :param starts: mandatory
    :param ends: mandatory
    :param axes: optional
    :param steps: optional
    :return: results
    """
    slices = [slice(0, data.shape[i]) for i in range(len(data.shape))]
    if axes is None:
        axes = range(len(starts))
    for i, a in enumerate(axes):
        if steps is None:
            slices[a] = slice(starts[i], ends[i])
        else:
            slices[a] = slice(starts[i], ends[i], steps[i])
    return data[slices]


def argmin_use_numpy_select_last_index(
        data, axis=0, keepdims=True, select_last_index=False):
    """
    Needed or operator `ArgMin`.
    """
    if select_last_index:
        result = numpy.argmin(data, axis=axis)
        if keepdims and len(result.shape) < len(data.shape):
            result = numpy.expand_dims(result, axis)
        return result.astype(numpy.int64)

    data = numpy.flip(data, axis)
    result = numpy.argmin(data, axis=axis)
    result = data.shape[axis] - result - 1
    if keepdims:
        result = numpy.expand_dims(result, axis)
    return result.astype(numpy.int64)


class NumpyCode:
    """
    Converts an ONNX operators into :epkg:`numpy` code.

    :param opset: target opset for the conversion (usually unused)
    :param name: node name
    :param op_type: operator type
    :param domain: domain
    :param inputs: inputs
    :param outputs: outputs
    :param attributes: attributes
    :param used: dictionary `{k: v}`,
        list of nodes taking *k* as input
    :param context: whole context
    :param mark_inits: marks initializer as replaced
    :param indent: indentation of the second line and following
    :return: code as str
    """

    def __init__(self, opset, name=None, op_type=None, domain='',
                 inputs=None, outputs=None, attributes=None,
                 used=None, context=None, mark_inits=None,
                 indent="", **unused):
        self.opset = opset
        self.name = name
        self.op_type = op_type
        self.domain = domain
        self.inputs = inputs
        self.outputs = outputs
        self.attributes = attributes
        self.used = used
        self.context = context
        self.mark_inits = mark_inits
        self.unused = unused
        self.indent = indent

    def _make_sure_inputs(self, n, m=None):
        if m is None:
            m = n
        if len(self.inputs) < n:
            raise RuntimeError(  # pragma: no cover
                "Expecting at least %d inputs for operator %r not %r." % (
                    n, self.op_type, self.inputs))
        if len(self.inputs) > m:
            raise RuntimeError(  # pragma: no cover
                "Expecting at most %d inputs for operator %r not %r." % (
                    m, self.op_type, self.inputs))

    def _make_sure_opsets(self, mi, ma=None):
        if mi is not None and self.opset < mi:
            raise RuntimeError(  # pragma: no cover
                "Cannot convert operator type %d, opset %d < %d." % (
                    self.op_type, self.opset, mi))
        if ma is not None and self.opset > ma:
            raise RuntimeError(  # pragma: no cover
                "Cannot convert operator type %d, opset %d > %d." % (
                    self.op_type, self.opset, mi))

    def _getat(self, name, defval=None):
        for n, val in self.attributes:
            if name == n:
                return val
        return defval

    def _simplify(self, name, kind):
        value = None
        if (self.used is not None and name in self.used and
                len(self.used[name]) == 1 and self.context is not None):
            inits = self.context['initializers_dict']
            if name in inits:
                v = inits[name]
                if v.dtype == numpy.int64 and v.size < 10:
                    value = v
                    if name not in self.mark_inits:
                        self.mark_inits[name] = []
                    self.mark_inits[name].append(v)

        if kind == 'tuple':
            if value is None:
                return "tuple(%s)" % name
            if value.size == 1:
                return str(tuple(value)[0])
            return str(tuple(value))
        elif kind == 'list':
            if value is None:
                return name
            if len(value.shape) == 0:
                return str(value)
            return str(list(value))
        raise NotImplementedError(
            "Unknown scenario to simplify (%r)." % kind)

    @staticmethod
    def _make_tuple(val):
        if isinstance(val, tuple):
            return val
        if isinstance(val, list):
            return tuple(val)
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            return tuple(map(int, val.strip('()[]').replace(" ", "").split(",")))
        raise NotImplementedError(
            "Unable to convert %r into tuple." % val)

    def make_numpy_code(self):
        """
        Main method, returns the python code for a given
        operator.
        """
        if self.domain == '':
            return self._make_numpy_code_onnx()

        if self.domain == 'ai.onnx.ml':
            return self._make_numpy_code_onnxml()

        raise NotImplementedError(
            "Unable to convert any operator from domain %r." % self.domain)

    def _make_numpy_code_onnx(self):

        binary_ops = dict(Add='+', Sub='-', Div='/', Mul='*', MatMul='@',
                          Pow='**')
        unary_ops = dict(Neg='-')
        unary_ops_ = dict(Sqrt='** 0.5')

        outs = ", ".join(self.outputs)

        if self.op_type in binary_ops:
            self._make_sure_inputs(2)
            return "%s = %s %s %s" % (
                outs, self.inputs[0], binary_ops[self.op_type],
                self.inputs[1])

        if self.op_type in unary_ops:
            self._make_sure_inputs(1)
            return "%s = %s %s" % (
                outs, unary_ops[self.op_type], self.inputs[0])

        if self.op_type in unary_ops_:
            self._make_sure_inputs(1)
            return "%s = %s %s" % (
                outs, self.inputs[0], unary_ops_[self.op_type])

        if self.op_type == 'ArgMin':
            self._make_sure_opsets(12)
            self._make_sure_inputs(1)
            axis = self._getat('axis', 0)
            keepdims = self._getat('keepdims', 1)
            select_last_index = self._getat('keepdims', 0)
            return (
                "%s = argmin_use_numpy_select_last_index("
                "%s, axis=%s, keepdims=%s, select_last_index=%s)" % (
                    outs, self.inputs[0], axis, keepdims, select_last_index))

        if self.op_type == 'Concat':
            axis = self._getat('axis', 0)
            return "%s = numpy.concatenate([%s], %s)" % (
                outs, ", ".join(self.inputs), axis)

        if self.op_type == 'Max':
            return "%s = numpy.maximum(%s)" % (outs, ", ".join(self.inputs))

        if self.op_type == 'Gather':
            self._make_sure_opsets(11)
            self._make_sure_inputs(2)
            axis = self._getat('axis', 0)
            return "%s = numpy.take(%s, %s, axis=%s)" % (
                outs, self.inputs[0],
                self._simplify(self.inputs[1], 'list'), axis)

        if self.op_type == 'Gemm':
            self._make_sure_inputs(2, 3)
            alpha = self._getat('alpha', 0.)
            transA = self._getat('transA', 0)
            transB = self._getat('transB', 0)
            ta = ".T" if transA in ('1', 1, True) else ""
            tb = ".T" if transB in ('1', 1, True) else ""
            if len(self.inputs) == 2:
                return "%s = %s%s @ %s%s * %s" % (
                    outs, self.inputs[0], ta, self.inputs[1], tb, alpha)
            beta = self._getat('beta', 0.)
            return "%s = %s%s @ %s%s * %s + %s * %s" % (
                outs, self.inputs[0], ta, self.inputs[1], tb, alpha,
                self.inputs[2], beta)

        if self.op_type == 'Identity':
            return "%s = %s" % (outs, self.inputs[0])

        if self.op_type == 'ReduceProd':
            self._make_sure_inputs(1)
            axes = self._getat('axes', "[0]")
            keepdims = self._getat('keepdims', 0)
            return "%s = %s.prod(axis=tuple(%s), keepdims=%s)" % (
                outs, self.inputs[0], axes, keepdims)

        if self.op_type == 'ReduceSum':
            self._make_sure_opsets(11)
            self._make_sure_inputs(2)
            keepdims = self._getat('keepdims', 0)
            return "%s = %s.sum(axis=%s, keepdims=%s)" % (
                outs, self.inputs[0], self._simplify(self.inputs[1], 'tuple'),
                keepdims)

        if self.op_type == 'ReduceSumSquare':
            self._make_sure_inputs(1)
            axes = self._getat('axes', "[0]")
            keepdims = self._getat('keepdims', 0)
            return "%s = (%s ** 2).sum(axis=tuple(%s), keepdims=%s)" % (
                outs, self.inputs[0], axes, keepdims)

        if self.op_type == 'Reshape':
            self._make_sure_inputs(2)
            simp = self._simplify(self.inputs[1], 'tuple')
            return "%s = %s.reshape(%s)" % (
                outs, self.inputs[0], simp)

        if self.op_type == 'Shape':
            self._make_sure_inputs(1)
            return "%s = numpy.array(%s.shape, dtype=numpy.int64)" % (
                outs, self.inputs[0])

        if self.op_type == 'Slice':
            return "%s = make_slice(%s)" % (outs, ", ".join(self.inputs))

        if self.op_type == 'Squeeze':
            self._make_sure_opsets(13)
            self._make_sure_inputs(2)
            return "%s = numpy.squeeze(%s, axis=%s)" % (
                outs, self.inputs[0], self._simplify(self.inputs[1], 'tuple'))

        if self.op_type == 'Transpose':
            self._make_sure_inputs(1)
            perm = self._getat('perm', None)
            return "%s = numpy.transpose(%s, axes=%s)" % (
                outs, self.inputs[0], self._make_tuple(perm))

        if self.op_type == 'Unsqueeze':
            self._make_sure_opsets(13)
            self._make_sure_inputs(2)
            return "%s = numpy.expand_dims(%s, axis=%s)" % (
                outs, self.inputs[0],
                self._simplify(self.inputs[1], 'tuple'))

        raise NotImplementedError(  # pragma: no cover
            "Unable to convert operator type %r name=%r." % (
                self.op_type, self.name))

    def _make_numpy_code_onnxml(self):
        outs = ", ".join(self.outputs)

        if self.op_type == 'LinearRegressor':
            self._make_sure_inputs(1)
            coefficients = self._getat('coefficients', None)
            intercepts = self._getat('intercepts', None)
            post_transform = self._getat('post_transform', 'NONE')
            targets = self._getat('targets', 1)
            if post_transform != "NONE":
                raise NotImplementedError(
                    "Conversion of operator %r with post_transform %r "
                    "is not implemented." % (self.op_type, post_transform))
            rows = [
                "coefs = numpy.array(%s, dtype=numpy.float32)."
                "reshape((-1, %d))" % (coefficients, targets),
                "%sinter = numpy.array(%s, dtype=numpy.float32)."
                "reshape((-1, %d))" % (self.indent, intercepts, targets),
                "%s%s = %s @ coefs + inter" % (
                    self.indent, outs, self.inputs[0])]
            return "\n".join(rows)

        raise NotImplementedError(  # pragma: no cover
            "Unable to convert operator type %r name=%r (onnxml)." % (
                self.op_type, self.name))


def make_numpy_code(opset, name=None, op_type=None, domain='',
                    inputs=None, outputs=None, attributes=None,
                    used=None, context=None, mark_inits=None,
                    indent="", **unused):
    """
    Converts an ONNX operators into :epkg:`numpy` code.

    :param opset: target opset for the conversion (usually unused)
    :param name: node name
    :param op_type: operator type
    :param domain: domain
    :param inputs: inputs
    :param outputs: outputs
    :param attributes: attributes
    :param used: dictionary `{k: v}`,
        list of nodes taking *k* as input
    :param context: whole context
    :param mark_inits: marks initializer as replaced
    :param indent: indentation of the second line and following
    :return: code as str
    """
    cl = NumpyCode(
        opset=opset, name=name, op_type=op_type, domain=domain,
        inputs=inputs, outputs=outputs, attributes=attributes,
        used=used, context=context, mark_inits=mark_inits,
        indent=indent, **unused)
    return cl.make_numpy_code()

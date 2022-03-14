"""
@file
@brief Runtime to infer shapes.

.. versionadded:: 0.9
"""
import numpy
from onnx.numpy_helper import to_array
from onnx.mapping import TENSOR_TYPE_TO_NP_TYPE
from .ops_shape.shape_result import ShapeResult
from .ops_shape.shape_container import ShapeContainer
from .ops_shape import shape_dispatch


class OnnxShapeInference:
    """
    Implements a micro runtime for ONNX graphs.
    It does not implements all the operator types.

    :param model_onnx: ONNX model

    .. runpython::
        :showcode:

        import pprint
        import numpy
        from mlprodict.onnxrt.onnx_shape_inference import OnnxShapeInference
        from mlprodict.npy.xop_variable import Variable
        from mlprodict.npy.xop import loadop

        opset = 15
        OnnxAdd = loadop('Add')
        dtype = numpy.float32

        cop = OnnxAdd('X', numpy.array(
            [[1]], dtype=dtype), op_version=opset)
        cop4 = OnnxAdd(cop, numpy.array([[2]], dtype=dtype),
                       output_names=['Y'])
        vari = Variable('X', numpy.float32, [None, 3])
        model_def = cop4.to_onnx([vari], run_shape=False)
        rt = OnnxShapeInference(model_def)
        out = rt.run()
        pprint.pprint(out.get())
    """

    def __init__(self, model_onnx):
        if not hasattr(model_onnx, 'graph'):
            raise TypeError(  # pragma: no cover
                "model_onnx is not an ONNX graph but %r." % type(model_onnx))
        self.model_onnx = model_onnx
        self.known_shapes_ = self._run_empty()

    @property
    def input_names(self):
        "Returns input names."
        return [i.name for i in self.model_onnx.graph.input]

    @property
    def output_names(self):
        "Returns output names."
        return [i.name for i in self.model_onnx.graph.output]

    def __repr__(self):
        "Usual"
        return "%s(...)" % self.__class__.__name__

    @staticmethod
    def _get_shape(obj, known_shapes=None, result_name=None):
        dtype = TENSOR_TYPE_TO_NP_TYPE.get(
            obj.type.tensor_type.elem_type, None)
        shape = []
        for dimi, d in enumerate(obj.type.tensor_type.shape.dim):
            v = d.dim_value if d.dim_value > 0 else d.dim_param
            if v in ('', None):
                if known_shapes is None or result_name is None:
                    raise RuntimeError(  # pragma: no cover
                        "known_shapes must be specified if "
                        "a dimension is not.")
                v = known_shapes.get_new_name(v, result_name, dimi)
            shape.append(v)
        return shape, dtype, False

    def _run_empty(self):
        """
        Computes shape and types of all results.

        :return: all intermediates results and output as a dictionary
        """
        known_shapes = ShapeContainer()
        for init in self.model_onnx.graph.initializer:
            mat = to_array(init)
            known_shapes.update(init.name, ShapeResult(
                init.name, mat.shape, mat.dtype, sparse=False))

        for obj in self.model_onnx.graph.input:
            if obj.name in known_shapes:
                raise NotImplementedError(
                    "Optional inputs are not implemented yet. "
                    "(name=%r)" % obj.name)
            shape, dtype, sparse = self._get_shape(
                obj, known_shapes, result_name=obj.name)
            known_shapes.update(obj.name, ShapeResult(
                obj.name, shape, dtype, sparse=sparse))

        for obj in self.model_onnx.graph.output:
            if obj.name in known_shapes:
                raise RuntimeError(  # pragma: no cover
                    "Output %r is already present. Use Identity node."
                    "" % obj.name)
            shape, dtype, sparse = self._get_shape(
                obj, known_shapes, result_name=obj.name)
            if dtype is None:
                # The onnx graph was created with named outputs
                # but with no type or shape.
                continue
            known_shapes.update(obj.name, ShapeResult(
                obj.name, shape, dtype, sparse=sparse))

        cont = True
        while cont:
            cont = False
            for node in self.model_onnx.graph.node:
                cont = cont or shape_dispatch(known_shapes, node)

        return known_shapes

    def run(self, inputs=None):
        """
        Runs shape inference and type given known inputs.

        :param inputs: inputs
        :return: all results
        """
        known_shapes = self.known_shapes_.copy(deep=True)
        if inputs is None:
            known_shapes.resolve()
            return known_shapes

        cont = False
        for name, obj in inputs.items():
            shape, dtype, sparse = (
                obj.shape, obj.dtype, not isinstance(obj, numpy.ndarray))
            cont = cont or known_shapes.update(
                name, ShapeResult(name, shape, dtype, sparse=sparse))

        while cont:
            cont = False
            for node in self.model_onnx.graph.node:
                cont = cont or shape_dispatch(known_shapes, node)

        known_shapes.resolve()
        return known_shapes

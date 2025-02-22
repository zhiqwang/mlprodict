"""
@brief      test log(time=24s)
"""
import os
import sys
from io import BytesIO
import pickle
import unittest
import warnings
from logging import getLogger
import numpy
import pandas
from onnx.onnx_cpp2py_export.checker import ValidationError  # pylint: disable=E0401,E0611
from onnx.helper import (
    make_tensor, make_node, make_graph, make_tensor_value_info,
    make_model)
from onnx import TensorProto
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from pyquickhelper.pycode import ExtTestCase, get_temp_folder, ignore_warnings
from skl2onnx.algebra.onnx_ops import (  # pylint: disable=E0611
    OnnxAdd, OnnxLinearRegressor, OnnxLinearClassifier,
    OnnxConstantOfShape, OnnxShape, OnnxIdentity,
    OnnxIf, OnnxSub, OnnxGreater, OnnxReduceSum)
from skl2onnx.common.data_types import FloatTensorType, Int64TensorType
from skl2onnx import __version__ as skl2onnx_version
from mlprodict.onnx_conv import to_onnx
from mlprodict.onnxrt import OnnxInference
from mlprodict import __max_supported_opset__ as TARGET_OPSET


class TestOnnxrtSimple(ExtTestCase):

    def setUp(self):
        logger = getLogger('skl2onnx')
        logger.disabled = True

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_idi(self):
        idi = numpy.identity(2).astype(numpy.float32)
        onx = OnnxAdd('X', idi, output_names=['Y'],
                      op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)

        oinf = OnnxInference(model_def)
        res = str(oinf)
        self.assertIn('op_type: "Add"', res)

        sb = model_def.SerializeToString()
        oinf = OnnxInference(sb)
        res = str(oinf)
        self.assertIn('op_type: "Add"', res)

        sb = BytesIO(model_def.SerializeToString())
        oinf = OnnxInference(sb)
        res = str(oinf)
        self.assertIn('op_type: "Add"', res)

        temp = get_temp_folder(__file__, "temp_onnxrt_idi")
        name = os.path.join(temp, "m.onnx")
        with open(name, "wb") as f:
            f.write(model_def.SerializeToString())

        oinf = OnnxInference(name)
        res = str(oinf)
        self.assertIn('op_type: "Add"', res)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_pickle_check(self):
        idi = numpy.identity(2).astype(numpy.float32)
        onx = OnnxAdd('X', idi, output_names=['Y'],
                      op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        shape = oinf.shape_inference()
        self.assertNotEmpty(shape)
        if not sys.platform.startswith('win'):
            # Crashes (onnx crashes).
            try:
                oinf.check_onnx()
            except ValidationError as e:
                warnings.warn("Why? " + str(e))  # pylint: disable=E1101

        pkl = pickle.dumps(oinf)
        obj = pickle.loads(pkl)
        self.assertEqual(str(oinf), str(obj))

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_dot(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        dot = oinf.to_dot()
        self.assertIn('Add [', dot)
        self.assertIn('Add1 [', dot)
        self.assertIn('Add\\n(Ad_Add)', dot)
        self.assertIn('Add\\n(Ad_Add1)', dot)
        self.assertIn('X -> Ad_Add;', dot)
        self.assertIn('Ad_Addcst1 -> Ad_Add1;', dot)
        self.assertIn('Ad_Addcst -> Ad_Add;', dot)
        self.assertIn('Ad_Add1 -> Y;', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_text(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        text = oinf.to_text()
        self.assertIn('Init', text)
        self.assertIn('Input-0', text)
        self.assertIn('Output-0', text)
        self.assertIn('inout', text)
        self.assertIn('O0 I0', text)
        self.assertIn('Ad_Addcst', text)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_text_seq(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        text = oinf.to_text(kind='seq')
        self.assertIn('input:', text)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_dot_onnx(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        dot = oinf.to_dot(use_onnx=True)
        self.assertIn('[label="Ad_Addcst1"', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_dot_shape(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        dot = oinf.to_dot(add_rt_shapes=True)
        self.assertIn('Add [', dot)
        self.assertIn('Add1 [', dot)
        self.assertIn('Add\\n(Ad_Add)', dot)
        self.assertIn('Add\\n(Ad_Add1)', dot)
        self.assertIn('X -> Ad_Add;', dot)
        self.assertIn('Ad_Addcst1 -> Ad_Add1;', dot)
        self.assertIn('Ad_Addcst -> Ad_Add;', dot)
        self.assertIn('Ad_Add1 -> Y;', dot)
        self.assertIn('shape=(n, 2)', dot)
        self.assertIn('inplace', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lreg(self):
        pars = dict(coefficients=numpy.array([1., 2.]), intercepts=numpy.array([1.]),
                    post_transform='NONE')
        onx = OnnxLinearRegressor('X', output_names=['Y'], **pars)
        model_def = onx.to_onnx({'X': pars['coefficients'].astype(numpy.float32)},
                                outputs=[('Y', FloatTensorType([1]))],
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        dot = oinf.to_dot()
        self.assertIn('coefficients=[1. 2.]', dot)
        self.assertIn('LinearRegressor', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lrc(self):
        pars = dict(coefficients=numpy.array([1., 2.]), intercepts=numpy.array([1.]),
                    classlabels_ints=[0, 1], post_transform='NONE')
        onx = OnnxLinearClassifier('X', output_names=['Y', 'Yp'], **pars)
        model_def = onx.to_onnx({'X': pars['coefficients'].astype(numpy.float32)},
                                outputs=[('Y', Int64TensorType()),
                                         ('Yp', FloatTensorType())],
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        dot = oinf.to_dot()
        self.assertIn('coefficients=[1. 2.]', dot)
        self.assertIn('LinearClassifier', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lrc_iris(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, _, y_train, __ = train_test_split(X, y, random_state=11)
        clr = LogisticRegression(solver="liblinear")
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        dot = oinf.to_dot()
        self.assertIn('ZipMap', dot)
        self.assertIn('LinearClassifier', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lrc_iris_json(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, _, y_train, __ = train_test_split(X, y, random_state=11)
        clr = LogisticRegression(solver="liblinear")
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        js = oinf.to_json()
        self.assertIn('"producer_name": "skl2onnx",', js)
        self.assertIn('"name": "output_label",', js)
        self.assertIn('"name": "output_probability",', js)
        self.assertIn('"name": "LinearClassifier",', js)
        self.assertIn('"coefficients": {', js)
        self.assertIn('"name": "Normalizer",', js)
        self.assertIn('"name": "Cast",', js)
        self.assertIn('"name": "ZipMap",', js)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_json(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        js = oinf.to_json()
        self.assertIn('"initializers": {', js)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_graph(self):
        idi = numpy.identity(2).astype(numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        js = oinf.to_sequence()
        self.assertIn('inits', js)
        self.assertIn('inputs', js)
        self.assertIn('outputs', js)
        self.assertIn('intermediate', js)
        self.assertIn('nodes', js)
        self.assertIn('sequence', js)
        self.assertEqual(len(js['sequence']), 2)
        self.assertEqual(len(js['intermediate']), 2)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_run(self):
        idi = numpy.identity(2, dtype=numpy.float32)
        idi2 = (numpy.identity(2) * 2).astype(numpy.float32)
        onx = OnnxAdd(
            OnnxAdd('X', idi, op_version=TARGET_OPSET),
            idi2, output_names=['Y'],
            op_version=TARGET_OPSET)
        model_def = onx.to_onnx({'X': idi.astype(numpy.float32)},
                                target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        X = numpy.array([[1, 1], [3, 3]])
        y = oinf.run({'X': X.astype(numpy.float32)})
        exp = numpy.array([[4, 1], [3, 6]], dtype=numpy.float32)
        self.assertEqual(list(y), ['Y'])
        self.assertEqualArray(y['Y'], exp)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lrreg_iris_run(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, X_test, y_train, _ = train_test_split(X, y, random_state=11)
        clr = LinearRegression()
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        y = oinf.run({'X': X_test})
        exp = clr.predict(X_test)
        self.assertEqual(list(sorted(y)), ['variable'])
        self.assertEqualArray(exp, y['variable'].ravel(), decimal=6)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lrc_iris_run(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, X_test, y_train, _ = train_test_split(X, y, random_state=11)
        clr = LogisticRegression(solver="liblinear")
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        y = oinf.run({'X': X_test})
        self.assertEqual(list(sorted(y)), [
                         'output_label', 'output_probability'])
        lexp = clr.predict(X_test)
        self.assertEqualArray(lexp, y['output_label'])

        exp = clr.predict_proba(X_test)
        got = pandas.DataFrame(list(y['output_probability'])).values
        self.assertEqualArray(exp, got, decimal=5)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_knn_iris_dot(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, __, y_train, _ = train_test_split(X, y, random_state=11)
        clr = KNeighborsClassifier()
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def, skip_run=True)
        dot = oinf.to_dot()
        self.assertNotIn("class_labels_0 -> ;", dot)

    @ignore_warnings(DeprecationWarning)
    def test_getitem(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, __, y_train, _ = train_test_split(X, y, random_state=11)
        clr = KNeighborsClassifier()
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def, skip_run=True)

        exp_name = 'blab_ArrayFeatureExtractor'
        if exp_name not in str(model_def):
            exp_name = "knny_ArrayFeatureExtractor"
        topk = oinf[exp_name]
        self.assertIn(exp_name, str(topk))
        zm = oinf['ZipMap']
        self.assertIn('ZipMap', str(zm))
        par = oinf['ZipMap', 'classlabels_int64s']
        self.assertIn('classlabels_int64s', str(par))

    @ignore_warnings(DeprecationWarning)
    def test_constant_of_shape(self):
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        tensor_value = make_tensor(
            "value", TensorProto.FLOAT, (1,), [-5])  # pylint: disable=E1101
        cop2 = OnnxConstantOfShape(
            OnnxShape('input', op_version=TARGET_OPSET),
            value=tensor_value,
            output_names=['mat'],
            op_version=TARGET_OPSET)
        model_def = cop2.to_onnx({'input': x},
                                 outputs=[('mat', FloatTensorType())],
                                 target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def, skip_run=True)
        dot = oinf.to_dot()
        self.assertIn('ConstantOfShape', dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_pdist_dot(self):
        from skl2onnx.algebra.complex_functions import onnx_squareform_pdist  # pylint: disable=E0401,E0611
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('input', 'input',
                      op_version=TARGET_OPSET)
        cdist = onnx_squareform_pdist(cop, dtype=numpy.float32,
                                      op_version=TARGET_OPSET)
        cop2 = OnnxIdentity(cdist, output_names=['cdist'],
                            op_version=TARGET_OPSET)

        model_def = cop2.to_onnx(
            {'input': x}, outputs=[('cdist', FloatTensorType())],
            target_opset=TARGET_OPSET)

        oinf = OnnxInference(model_def, skip_run=True)
        dot = oinf.to_dot(recursive=True)
        self.assertIn("B_next_out", dot)
        self.assertIn("cluster", dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnxt_lrc_iris_run_node_time(self):
        iris = load_iris()
        X, y = iris.data, iris.target
        X_train, X_test, y_train, _ = train_test_split(X, y, random_state=11)
        clr = LogisticRegression(solver="liblinear")
        clr.fit(X_train, y_train)

        model_def = to_onnx(clr, X_train.astype(numpy.float32),
                            target_opset=TARGET_OPSET)
        oinf = OnnxInference(model_def)
        _, mt = oinf.run({'X': X_test}, node_time=True)
        self.assertIsInstance(mt, list)
        self.assertGreater(len(mt), 1)
        self.assertIsInstance(mt[0], dict)

        rows = []

        def myprint(*args):
            rows.append(' '.join(map(str, args)))

        _, mt = oinf.run({'X': X_test}, node_time=True,
                         verbose=1, fLOG=myprint)
        self.assertIsInstance(mt, list)
        self.assertGreater(len(mt), 1)
        self.assertIsInstance(mt[0], dict)

    @ignore_warnings(DeprecationWarning)
    def test_blofat16(self):
        node1 = make_node("Min", ["X", "Y"], ["Z"], name="trans")

        graph = make_graph(
            [node1], "min_graph",
            [make_tensor_value_info("X", TensorProto.FLOAT16, [3]),  # pylint: disable=E1101
             make_tensor_value_info("Y", TensorProto.FLOAT16, [3])],  # pylint: disable=E1101
            [make_tensor_value_info("Z", TensorProto.FLOAT16, [3])])  # pylint: disable=E1101
        model_proto = make_model(
            graph, producer_name='mlprodict', ir_version=6, producer_version='0.1')

        oinf = OnnxInference(model_proto)
        x_val = [1, 2, -3]
        y_val = [4, -5, -6]
        res = oinf.run({"X": numpy.array(x_val, dtype=numpy.float16),
                        "Y": numpy.array(y_val, dtype=numpy.float16)})
        self.assertEqualArray(res['Z'], numpy.array(
            [1, -5, -6], dtype=numpy.float16))
        dot = oinf.to_dot()
        self.assertIn('float16', dot)

        oinf = OnnxInference(model_proto, runtime='python_compiled')
        res = oinf.run({"X": numpy.array(x_val, dtype=numpy.float16),
                        "Y": numpy.array(y_val, dtype=numpy.float16)})
        self.assertEqualArray(res['Z'], numpy.array(
            [1, -5, -6], dtype=numpy.float16))
        self.assertIn('n0_min(X, Y)', str(oinf))

    @ignore_warnings(DeprecationWarning)
    def test_onnx_if_to_dot(self):
        opv = 15
        x1 = numpy.array([[0, 3], [7, 0]], dtype=numpy.float32)
        x2 = numpy.array([[1, 0], [2, 0]], dtype=numpy.float32)

        node = OnnxAdd(
            'x1', 'x2', output_names=['absxythen'], op_version=opv)
        then_body = node.to_onnx(
            {'x1': x1, 'x2': x2}, target_opset=opv,
            outputs=[('absxythen', FloatTensorType())])
        node = OnnxSub(
            'x1', 'x2', output_names=['absxyelse'], op_version=opv)
        else_body = node.to_onnx(
            {'x1': x1, 'x2': x2}, target_opset=opv,
            outputs=[('absxyelse', FloatTensorType())])
        del else_body.graph.input[:]
        del then_body.graph.input[:]

        cond = OnnxGreater(
            OnnxReduceSum('x1', op_version=opv),
            OnnxReduceSum('x2', op_version=opv),
            op_version=opv)
        ifnode = OnnxIf(cond, then_branch=then_body.graph,
                        else_branch=else_body.graph,
                        op_version=opv, output_names=['y'])
        model_def = ifnode.to_onnx(
            {'x1': x1, 'x2': x2}, target_opset=opv,
            outputs=[('y', FloatTensorType())])
        dot = OnnxInference(model_def, skip_run=True).to_dot(recursive=True)
        self.assertIn("subgraph cluster_If", dot)

    @ignore_warnings(DeprecationWarning)
    def test_onnx_if_to_dot2(self):
        opv = TARGET_OPSET
        x1 = numpy.array([[0, 3], [7, 0]], dtype=numpy.float32)
        x2 = numpy.array([[1, 0], [2, 0]], dtype=numpy.float32)

        node = OnnxAdd(
            'x1', 'x2', output_names=['absxythen'], op_version=opv)
        then_body = node.to_onnx(
            {'x1': x1, 'x2': x2}, target_opset=opv,
            outputs=[('absxythen', FloatTensorType())])
        node = OnnxSub(
            'x1', 'x2', output_names=['absxyelse'], op_version=opv)
        else_body = node.to_onnx(
            {'x1': x1, 'x2': x2}, target_opset=opv,
            outputs=[('absxyelse', FloatTensorType())])
        del else_body.graph.input[:]
        del then_body.graph.input[:]

        cond = OnnxGreater(
            OnnxReduceSum('x1', op_version=opv),
            OnnxReduceSum('x2', op_version=opv),
            op_version=opv)
        ifnode = OnnxIf(cond, then_branch=then_body.graph,
                        else_branch=else_body.graph,
                        op_version=opv, output_names=['y'])
        model_def = ifnode.to_onnx(
            {'x1': x1, 'x2': x2}, target_opset=opv,
            outputs=[('y', FloatTensorType())])
        dot = OnnxInference(model_def).to_dot(recursive=True)
        self.assertIn('[lhead=cluster_If', dot)


if __name__ == "__main__":
    unittest.main()

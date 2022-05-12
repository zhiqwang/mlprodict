"""
@brief      test log(time=3s)
"""
import unittest
import os
import pprint
import time
from collections import Counter
import numpy
from onnx import helper, TensorProto, load, FunctionProto
from pyquickhelper.pycode import ExtTestCase, get_temp_folder
from mlprodict.npy.xop import loadop, OnnxOperatorFunction
from mlprodict.npy.xop_variable import Variable
from mlprodict.onnx_tools.optim.onnx_helper import onnx_statistics
from mlprodict.onnx_tools.onnx_tools import (
    enumerate_onnx_names, enumerate_onnx_nodes)
from mlprodict.onnxrt import OnnxInference
from mlprodict.onnx_tools.optim import onnx_remove_node_unused
from mlprodict.onnx_tools.onnx_manipulations import (
    select_model_inputs_outputs, enumerate_model_node_outputs,
    onnx_rename_names, insert_results_into_onnx, onnx_model_to_function,
    onnx_inline_function, onnx_function_to_model, change_input_type)
from mlprodict import __max_supported_opset__ as TARGET_OPSET
from mlprodict.plotting.text_plot import onnx_simple_text_plot
from mlprodict.onnxrt.excs import MissingOperatorError


class TestOptimOnnxManipulations(ExtTestCase):

    def test_onnx_remove_unused_outputs(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        model_def = select_model_inputs_outputs(
            model_def, "inter", infer_shapes=True, remove_unused=False)
        stats = onnx_statistics(model_def, optim=True)
        c1 = model_def.SerializeToString()
        new_model = onnx_remove_node_unused(model_def)
        c2 = model_def.SerializeToString()
        self.assertEqual(c1, c2)
        stats2 = onnx_statistics(model_def, optim=True)
        stats3 = onnx_statistics(new_model, optim=False)
        self.assertEqual(stats['ninits'], 2)
        self.assertEqual(stats2['ninits'], 2)
        self.assertEqual(stats3['ninits'], 1)
        self.assertEqual(stats2['nnodes'], 1)
        self.assertEqual(stats3['nnodes'], 1)
        oinf1 = OnnxInference(model_def)
        y1 = oinf1.run({'X': x})

        oinf2 = OnnxInference(new_model)
        y2 = oinf2.run({'X': x})
        self.assertNotIn('final', y1)
        self.assertNotIn('final', y2)
        self.assertIn('inter', y1)
        self.assertIn('inter', y2)
        self.assertEqualArray(y1['inter'], y2['inter'])

    def test_onnx_remove_unused_outputs_new(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def0 = cop4.to_onnx({'X': x})
        model_def = select_model_inputs_outputs(
            model_def0, "inter", infer_shapes=True, remove_unused=False)
        stats = onnx_statistics(model_def, optim=True)
        c1 = model_def.SerializeToString()
        new_model = select_model_inputs_outputs(
            model_def0, "inter", infer_shapes=True)
        c2 = model_def.SerializeToString()
        self.assertEqual(c1, c2)
        stats2 = onnx_statistics(model_def, optim=True)
        stats3 = onnx_statistics(new_model, optim=False)
        self.assertEqual(stats['ninits'], 2)
        self.assertEqual(stats2['ninits'], 2)
        self.assertEqual(stats3['ninits'], 1)
        self.assertEqual(stats2['nnodes'], 1)
        self.assertEqual(stats3['nnodes'], 1)
        oinf1 = OnnxInference(model_def)
        y1 = oinf1.run({'X': x})

        oinf2 = OnnxInference(new_model)
        y2 = oinf2.run({'X': x})
        self.assertNotIn('final', y1)
        self.assertNotIn('final', y2)
        self.assertIn('inter', y1)
        self.assertIn('inter', y2)
        self.assertEqualArray(y1['inter'], y2['inter'])

    def test_onnx_remove_unused_inputs(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', cop2,
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop3, cop3, op_version=TARGET_OPSET),
            cop3, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        model_def = select_model_inputs_outputs(
            model_def, inputs=["inter"], infer_shapes=True, remove_unused=False)
        stats = onnx_statistics(model_def, optim=True)
        c1 = model_def.SerializeToString()
        new_model = onnx_remove_node_unused(model_def)
        c2 = model_def.SerializeToString()
        self.assertEqual(c1, c2)
        stats2 = onnx_statistics(model_def, optim=True)
        stats3 = onnx_statistics(new_model, optim=False)
        self.assertEqual(stats['ninits'], 1)
        self.assertEqual(stats2['ninits'], 1)
        self.assertEqual(stats3['ninits'], 0)
        self.assertEqual(stats2['nnodes'], 2)
        self.assertEqual(stats3['nnodes'], 2)
        oinf1 = OnnxInference(model_def)
        y1 = oinf1.run({'inter': x})

        oinf2 = OnnxInference(new_model)
        y2 = oinf2.run({'inter': x})
        self.assertIn('final', y1)
        self.assertIn('final', y2)
        self.assertNotIn('inter', y1)
        self.assertNotIn('inter', y2)
        self.assertEqualArray(y1['final'], y2['final'])

    def test_onnx_remove_unused_inputs_overwrite(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', cop2,
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop3, cop3, op_version=TARGET_OPSET),
            cop3, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        model_def = select_model_inputs_outputs(
            model_def, inputs=["inter"], infer_shapes=False,
            overwrite=dict(inter=(numpy.float32, [None, None]),
                           final=(numpy.float32, [None, None])),
            remove_unused=False)
        stats = onnx_statistics(model_def, optim=True)
        c1 = model_def.SerializeToString()
        new_model = onnx_remove_node_unused(model_def)
        c2 = model_def.SerializeToString()
        self.assertEqual(c1, c2)
        stats2 = onnx_statistics(model_def, optim=True)
        stats3 = onnx_statistics(new_model, optim=False)
        self.assertEqual(stats['ninits'], 1)
        self.assertEqual(stats2['ninits'], 1)
        self.assertEqual(stats3['ninits'], 0)
        self.assertEqual(stats2['nnodes'], 2)
        self.assertEqual(stats3['nnodes'], 2)
        oinf1 = OnnxInference(model_def)
        y1 = oinf1.run({'inter': x})

        oinf2 = OnnxInference(new_model)
        y2 = oinf2.run({'inter': x})
        self.assertIn('final', y1)
        self.assertIn('final', y2)
        self.assertNotIn('inter', y1)
        self.assertNotIn('inter', y2)
        self.assertEqualArray(y1['final'], y2['final'])

    def test_enumerate_model_node_outputs(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        nodes1 = list(enumerate_model_node_outputs(model_def))
        nodes2 = list(enumerate_model_node_outputs(model_def, order=True))
        self.assertEqual(list(sorted(nodes1)), list(sorted(nodes2)))
        expected = ['inter', 'out_add_0', 'out_mul_0', 'final']
        self.assertEqual(nodes2, expected)

    def test_onnx_rename_names_exc(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        self.assertRaise(
            lambda: onnx_rename_names(model_def, strategy="none"),
            ValueError)

    def test_onnx_rename_names_simple(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        rows = []

        def flog(*s):
            rows.append(" ".join(map(str, s)))

        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        oinf1 = OnnxInference(model_def)
        new_model = onnx_rename_names(model_def, verbose=1, fLOG=flog)
        total = "\n".join(rows)
        self.assertIn("[onnx_rename_names] init: 'init_1' -> 'i1'", total)
        oinf2 = OnnxInference(new_model)
        y1 = oinf1.run({'X': x})
        y2 = oinf2.run({'X': x})
        self.assertEqualArray(y1['final'], y2['final'])

    def test_onnx_rename_names_type(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        rows = []

        def flog(*s):
            rows.append(" ".join(map(str, s)))

        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        oinf1 = OnnxInference(model_def)
        new_model = onnx_rename_names(
            model_def, verbose=1, fLOG=flog, strategy='type')
        total = "\n".join(rows)
        self.assertIn("'init' -> 'i_DB'", total)
        oinf2 = OnnxInference(new_model)
        y1 = oinf1.run({'X': x})
        y2 = oinf2.run({'X': x})
        self.assertEqualArray(y1['final'], y2['final'])

    def test_onnx_rename_node_scan(self):
        (OnnxSub, OnnxReduceSumSquare,
         OnnxIdentity, OnnxScan) = loadop(
            'Sub', 'ReduceSumSquare', 'Identity', 'Scan')

        def onnx_squareform_pdist(X, dtype=None, op_version=None, **kwargs):
            diff = OnnxSub('next_in', 'next',
                           op_version=op_version)
            id_next = OnnxIdentity('next_in', output_names=['next_out'],
                                   op_version=op_version)
            flat = OnnxReduceSumSquare(diff, axes=[1], op_version=op_version,
                                       output_names=['scan_out'], keepdims=0)
            scan_body = id_next.to_onnx(
                [Variable('next_in', numpy.float32, (None, None)),  # tensor_type([None, None])),
                 Variable('next', numpy.float32, (None, ))],  # tensor_type([None]))]),
                outputs=[Variable('next_out', numpy.float32, (None, None)),  # ([None, None])),
                         Variable('scan_out', numpy.float32, (None, ))],  # tensor_type([None]))],
                other_outputs=[flat],
                target_opset=op_version)
            node = OnnxScan(X, X, output_names=['S1', 'S2'],
                            num_scan_inputs=1,
                            body=(scan_body.graph, [id_next, flat]),
                            op_version=op_version, **kwargs)
            return node[1]

        rows = []

        def flog(*s):
            rows.append(" ".join(map(str, s)))

        opv = TARGET_OPSET
        onnx_fct = OnnxIdentity(onnx_squareform_pdist(
            'x'), output_names='Y', op_version=opv)
        model_def = onnx_fct.to_onnx(inputs={'x': numpy.float32})

        oinf1 = OnnxInference(model_def)
        new_model = onnx_rename_names(
            model_def, verbose=1, fLOG=flog, strategy='type')
        total = "\n".join(rows)
        self.assertNotIn('name: "Re_ReduceSumSquare"', str(new_model))
        self.assertIn("'node__reducesumsquare_", total)
        oinf2 = OnnxInference(new_model)
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        y1 = oinf1.run({'x': x})
        y2 = oinf2.run({'x': x})
        self.assertEqualArray(y1['Y'], y2['Y'])

    def test_insert_results_into_onnx(self):
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, None)  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.INT64, None)  # pylint: disable=E1101
        node_def = helper.make_node('Shape', ['X'], ['Z0'], name='Zt')
        node_def1 = helper.make_node('Identity', ['Z0'], ['Z'], name='Zti')
        graph_def = helper.make_graph(
            [node_def, node_def1], 'test-model', [X], [Z])
        model_def = helper.make_model(
            graph_def, producer_name='mlprodict',
            ir_version=7, producer_version='0.1',
            opset_imports=[helper.make_operatorsetid('', 13)])

        new_graph = insert_results_into_onnx(
            model_def, {'Z0': numpy.array([[29, 39]], dtype=numpy.int64)})
        s_graph = str(new_graph)
        self.assertIn('domain: "DEBUG"', s_graph)
        self.assertNotIn('pname', s_graph)
        self.assertIn('op_type: "DEBUG"', s_graph)
        self.assertRaise(lambda: insert_results_into_onnx(
            model_def, {'Zt': numpy.array([29, 39], dtype=numpy.int64)}),
            RuntimeError)
        # with open('debug.onnx', 'wb') as f:
        #     f.write(new_graph.SerializeToString())

        oinf1 = OnnxInference(model_def, inplace=False)
        oinf2 = OnnxInference(new_graph, inplace=False)
        cst = numpy.array([[5.6, 7.8]])
        self.assertEqualArray(oinf1.run({'X': cst})['Z'],
                              oinf2.run({'X': cst})['Z'])

        onx = oinf1.run2onnx({'X': cst})[1]
        s_graph = str(onx)
        self.assertIn('domain: "DEBUG"', s_graph)
        self.assertIn('op_type: "DEBUG"', s_graph)
        self.assertNotIn('pname', s_graph)
        oinf3 = OnnxInference(onx)
        self.assertEqualArray(oinf1.run({'X': cst})['Z'],
                              oinf3.run({'X': cst})['Z'])

    def test_insert_results_into_onnx_init(self):
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, None)  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.INT64, None)  # pylint: disable=E1101
        node_def = helper.make_node('Shape', ['X'], ['Z0'], name='Zt')
        node_def1 = helper.make_node('Identity', ['Z0'], ['Z'], name='Zti')
        graph_def = helper.make_graph(
            [node_def, node_def1], 'test-model', [X], [Z])
        model_def = helper.make_model(
            graph_def, producer_name='mlprodict',
            ir_version=7, producer_version='0.1',
            opset_imports=[helper.make_operatorsetid('', 13)])

        new_graph = insert_results_into_onnx(
            model_def, {'Z0': numpy.array([[29, 39]], dtype=numpy.int64)},
            as_parameter=False, param_name=lambda k: k)
        s_graph = str(new_graph)
        self.assertIn('domain: "DEBUG"', s_graph)
        self.assertIn('op_type: "DEBUG"', s_graph)
        self.assertRaise(lambda: insert_results_into_onnx(
            model_def, {'Zt': numpy.array([29, 39], dtype=numpy.int64)}),
            RuntimeError)
        self.assertRaise(lambda: insert_results_into_onnx(
            model_def, {'X': numpy.array([29, 39], dtype=numpy.int64)}),
            NotImplementedError)
        # with open('debug.onnx', 'wb') as f:
        #     f.write(new_graph.SerializeToString())

        oinf1 = OnnxInference(model_def)
        oinf2 = OnnxInference(new_graph)
        cst = numpy.array([[5.6, 7.8]])
        self.assertEqualArray(oinf1.run({'X': cst})['Z'],
                              oinf2.run({'X': cst})['Z'])

    def test_onnx_enumerate_onnx_names(self):
        OnnxAdd, OnnxSub, OnnxMul = loadop('Add', 'Sub', 'Mul')
        dtype = numpy.float32
        x = numpy.array([1, 2, 4, 5, 5, 4]).astype(
            numpy.float32).reshape((3, 2))
        cop = OnnxAdd('X', numpy.array([1], dtype=dtype),
                      op_version=TARGET_OPSET)
        cop2 = OnnxAdd('X', numpy.array([1], dtype=dtype),
                       op_version=TARGET_OPSET)
        cop3 = OnnxAdd('X', numpy.array([2], dtype=dtype),
                       op_version=TARGET_OPSET,
                       output_names=['inter'])
        cop4 = OnnxSub(
            OnnxMul(cop, cop3, op_version=TARGET_OPSET),
            cop2, output_names=['final'],
            op_version=TARGET_OPSET)
        model_def = cop4.to_onnx({'X': x})
        names = list(enumerate_onnx_names(model_def))
        self.assertEqual(len(names), 16)
        self.assertIn('X', names)
        self.assertIn('inter', names)

    def test_onnx_to_function(self):
        data = os.path.join(os.path.dirname(__file__), "data")
        fft2d = os.path.join(data, "fft2d.onnx")
        onx = load(fft2d)

        # original graph
        oinf = OnnxInference(onx)
        x = numpy.random.randn(7, 7).astype(numpy.float32)
        y = oinf.run({'x': x})['y']

        fct = onnx_model_to_function(onx, name="fft2d")
        self.assertIsInstance(fct, FunctionProto)

        op = OnnxOperatorFunction(fct, 'X', output_names=['Y'])
        onx2 = op.to_onnx(numpy.float32, numpy.float32)
        s2 = str(onx2)
        self.assertIn("functions {", s2)
        self.assertIn('name: "fft2d"', s2)
        oinf2 = OnnxInference(onx2)
        y2 = oinf2.run({'X': x})['Y']
        self.assertEqualArray(y, y2)

    def test_onnx_inline_function(self):
        data = os.path.join(os.path.dirname(__file__), "data")
        fft2d = os.path.join(data, "fft2d.onnx")
        onx = load(fft2d)
        fct = onnx_model_to_function(onx, name="fft2d")
        op = OnnxOperatorFunction(fct, 'X', output_names=['Y'])
        onx2 = op.to_onnx(numpy.float32, numpy.float32)
        inlined, m = onnx_inline_function(onx2)
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0].op_type, "fft2d")
        s3 = str(inlined)
        self.assertNotIn("functions {", s3)

        x = numpy.random.randn(7, 7).astype(numpy.float32)
        oinf2 = OnnxInference(onx2)
        y2 = oinf2.run({'X': x})['Y']
        oinf3 = OnnxInference(inlined)
        y3 = oinf3.run({'X': x})['Y']
        self.assertEqualArray(y2, y3)

    def test_onnx_inline_function_function(self):
        data = os.path.join(os.path.dirname(__file__), "data")
        fft2d = os.path.join(data, "fft2d.onnx")
        onx = load(fft2d)
        fct = onnx_model_to_function(onx, name="fft2d")
        op = OnnxOperatorFunction(fct, 'X', output_names=['Y'])
        onx2 = op.to_onnx(numpy.float32, numpy.float32)

        fct = onnx_model_to_function(onx2, name="fft2d")
        inlined, m = onnx_inline_function(fct, list(onx2.functions))
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0].op_type, "fft2d")
        self.assertEqual(len(inlined.node), 35)

    def test_onnx_inline_function_fft(self, log=False):

        def _check_run_(name, onx):
            oinf = OnnxInference(onx)
            names = oinf.input_names

            if names[0] == 'window_length':
                # window function
                inputs = {'window_length': numpy.array([5], dtype=numpy.int64)}
                if 'alpha' in names:
                    inputs['alpha'] = numpy.array([0.56], dtype=numpy.float32)
                    inputs['beta'] = numpy.array([0.54], dtype=numpy.float32)
                got = oinf.run(inputs)
                res = got['return_val']
                self.assertEqual(res.shape, (5, ))
                self.assertEqual(res.dtype, numpy.float32)
                return got

            if names == ['x', 'axis1', 'axis2']:
                # switch axis
                inputs = {'x': numpy.random.randn(3, 4, 5).astype(numpy.float32),
                          'axis1': numpy.array([0], dtype=numpy.int64),
                          'axis2': numpy.array([2], dtype=numpy.int64)}
                got = oinf.run(inputs)
                res = got['return_val']
                self.assertEqual(res.shape, (5, 4, 3))
                self.assertEqualArray(numpy.transpose(
                    inputs['x'], (2, 1, 0)), res)
                return got

            if names == ['x', 'fft_length', 'weights', 'onesided',
                         'inverse', 'normalize']:
                # dft_last_axis
                inputs = {'x': numpy.random.randn(3, 4, 5, 1).astype(numpy.float32),
                          'fft_length': numpy.array([5], dtype=numpy.int64),
                          'weights': numpy.array([1, 1, 1, 1, 1], dtype=numpy.float32),
                          'onesided': numpy.array([0], dtype=numpy.float32),
                          'inverse': numpy.array([0], dtype=numpy.float32),
                          'normalize': numpy.array([0], dtype=numpy.float32)}
                ft = numpy.fft.fft(inputs['x'][:, :, :, 0], 5)
                got = oinf.run(inputs)
                output_name = onx.graph.output[0].name
                res = got[output_name]
                self.assertEqual(res.shape, (3, 4, 5, 2))
                self.assertEqualArray(
                    res[:, :, :, 0], numpy.real(ft), decimal=4)
                self.assertEqualArray(
                    res[:, :, :, 1], numpy.imag(ft), decimal=4)
                return got

            if names == ['x', 'fft_length', 'axis', 'weights', 'onesided',
                         'inverse', 'normalize']:
                # dft_inv
                inputs = {'x': numpy.random.randn(3, 4, 5, 1).astype(numpy.float32),
                          'fft_length': numpy.array([5], dtype=numpy.int64),
                          'weights': numpy.array([1, 1, 1, 1, 1], dtype=numpy.float32),
                          'axis': numpy.array([2], dtype=numpy.int64),
                          'onesided': numpy.array([0], dtype=numpy.float32),
                          'inverse': numpy.array([0], dtype=numpy.float32),
                          'normalize': numpy.array([0], dtype=numpy.float32)}
                ft = numpy.fft.fft(inputs['x'][:, :, :, 0], 5)
                got = oinf.run(inputs)
                output_name = onx.graph.output[0].name
                res = got[output_name]
                self.assertEqual(res.shape, (3, 4, 5, 2))
                self.assertEqualArray(
                    res[:, :, :, 0], numpy.real(ft), decimal=4)
                self.assertEqualArray(
                    res[:, :, :, 1], numpy.imag(ft), decimal=4)
                return got

            if names == ['x', 'fft_length', 'axis', 'onesided']:
                # dft or idft
                inputs = {'x': numpy.random.randn(3, 4, 5, 1).astype(numpy.float32),
                          'fft_length': numpy.array([5], dtype=numpy.int64),
                          'axis': numpy.array([2], dtype=numpy.int64),
                          'onesided': numpy.array([0], dtype=numpy.float32)}
                if name == "dft":
                    ft = numpy.fft.fft(inputs['x'][:, :, :, 0])
                elif name == "idft":
                    ft = numpy.fft.ifft(inputs['x'][:, :, :, 0])
                else:
                    raise AssertionError(
                        "Not implemented for function %r." % name)
                got = oinf.run(inputs, verbose=0, fLOG=print)
                output_name = onx.graph.output[0].name
                res = got[output_name]
                self.assertEqual(res.shape, (3, 4, 5, 2))
                self.assertEqualArray(
                    res[:, :, :, 0], numpy.real(ft), decimal=4)
                self.assertEqualArray(
                    res[:, :, :, 1], numpy.imag(ft), decimal=4)
                return got

            if names == ['x', 'fft_length', 'hop_length', 'n_frames',
                         'window', 'onesided']:
                # stft
                inputs = {'window': numpy.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                                                dtype=numpy.float32),
                          'fft_length': numpy.array([6], dtype=numpy.int64),
                          'hop_length': numpy.array([6], dtype=numpy.int64),
                          'n_frames': numpy.array([3], dtype=numpy.int64),
                          'onesided': numpy.array([0], dtype=numpy.float32)}
                inputs['x'] = numpy.random.randn(3, 8, 1).astype(numpy.float32)
                try:
                    import torch
                    p = torch.from_numpy(inputs['x'][:, :, 0])
                    win = torch.from_numpy(inputs['window'])
                    tft = torch.stft(p, n_fft=6, center=False,
                                     win_length=6, window=win,
                                     onesided=False, return_complex=True)
                    ft = tft.numpy()
                except ImportError:
                    ft = None
                got = oinf.run(inputs, verbose=0, fLOG=print)
                output_name = onx.graph.output[0].name
                res = got[output_name]
                self.assertEqual(res.shape, (3, 6, 3, 2))
                if ft is not None:
                    self.assertEqual(res.shape[:-1], ft.shape)
                    # self.assertEqualArray(
                    #     res[:, :, :, 0], numpy.real(ft), decimal=4)
                    # self.assertEqualArray(
                    #     res[:, :, :, 1], numpy.imag(ft), decimal=4)
                return got

            if names == ['x', 'fft_length', 'hop_length', 'window', 'onesided']:
                # istft
                inputs = {'window': numpy.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                                                dtype=numpy.float32),
                          'fft_length': numpy.array([6], dtype=numpy.int64),
                          'hop_length': numpy.array([6], dtype=numpy.int64),
                          'onesided': numpy.array([0], dtype=numpy.float32)}
                c = (
                    numpy.random.randn(3, 6, 3).astype(numpy.float32) +
                    numpy.random.randn(3, 6, 3).astype(numpy.float32) * 1j)
                z = numpy.zeros(c.shape + (2, ), dtype=numpy.float32)
                z[:, :, :, 0] = numpy.real(c)
                z[:, :, :, 1] = numpy.imag(c)
                inputs['x'] = z
                try:
                    import torch
                    p = torch.from_numpy(c)
                    win = torch.from_numpy(inputs['window'])
                    tft = torch.istft(p, n_fft=6, center=False,
                                      win_length=6, window=win,
                                      onesided=False, return_complex=True)
                    ft = tft.numpy()
                except ImportError:
                    ft = None
                got = oinf.run(inputs, verbose=0, fLOG=print)
                output_name = onx.graph.output[0].name
                res = got[output_name]
                self.assertEqual(res.shape[0], 3)
                # self.assertEqual(res.shape, (3, 8, 2))
                if ft is not None:
                    pass
                    # self.assertEqual(res.shape[:-1], ft.shape)
                    # self.assertEqualArray(
                    #     res[:, :, :, 0], numpy.real(ft), decimal=4)
                    # self.assertEqualArray(
                    #     res[:, :, :, 1], numpy.imag(ft), decimal=4)
                return got

            raise NameError("Unable to process %r." % names)

        def _check_run(name, onx):
            t = time.perf_counter()
            res = _check_run_(name, onx)
            d = time.perf_counter()
            print("TIME  EXEC ", fct, d - t)
            return res

        def _repare(onx):
            inputs = [_.name for _ in onx.graph.input]
            if 'window_length' in inputs or 'axis1' in inputs:
                # make it an INT
                onx = change_input_type(
                    onx, {'window_length': TensorProto.INT64,
                          'axis1': TensorProto.INT64,
                          'axis2': TensorProto.INT64})
            return onx

        def _type_info(name):
            if name in {'x', 'weights', 'window'}:
                return numpy.float32
            if name in {'fft_length', 'axis', 'hop_length', 'n_frames'}:
                return numpy.int64
            if name in {'onesided', 'inverse', 'normalize'}:
                return numpy.float32
            if name in {'final_3', 'return_val', 'final'}:
                return numpy.float32
            raise AssertionError("Unexpected name %r." % name)

        temp = get_temp_folder(__file__, 'temp_onnx_inline_function_fft')
        fcts = ["blackman_window", "hamming_window", "hann_window",
                "switch_axes", "dft_last_axis", "dft_inv", "dft", "idft",
                "stft", "istft"]

        # first loop, conversion to function
        data = os.path.join(os.path.dirname(__file__), "data", "fft")
        models = {}
        protos = {}
        for fct in fcts:
            if log:
                t = time.perf_counter()
                print("STEP1 begin", fct)
            onx = load(os.path.join(data, fct + ".onnx"))
            onx = _repare(onx)
            try:
                OnnxInference(onx)
                use_fct = False
            except (MissingOperatorError, RuntimeError):
                # The model misses a function.
                use_fct = True
            if use_fct:
                fpr = onnx_model_to_function(onx)
                onx = onnx_function_to_model(fpr, protos, type_info=_type_info)

            try:
                _check_run(fct, onx)
            except (RuntimeError, AttributeError, NameError) as e:
                raise AssertionError(
                    "Unable to run fct %r\n---\n%s" % (
                        fct, onnx_simple_text_plot(
                            onx, recursive=True))) from e
            proto = onnx_model_to_function(onx)
            proto.domain = 'this'
            protos[proto.domain, proto.name] = proto
            models[fct] = onx
            if log:
                print("STEP1 end  ", fct, time.perf_counter() - t)

        rows = []

        def myprint(*args):
            rows.append(' '.join(map(str, args)))

        if log:
            print()

        # first loop, inlining functions
        for fct, onx in models.items():
            if log:
                t = time.perf_counter()
                print("STEP2 begin", fct)
            del rows[:]
            with open(os.path.join(temp, fct + '.onnx'), 'wb') as f:
                f.write(onx.SerializeToString())
            with open(os.path.join(temp, fct + '.txt'), 'w') as f:
                f.write(helper.printable_graph(onx.graph))
            verbose = 4
            if log:
                ti = time.perf_counter()
            try:
                inlined, _ = onnx_inline_function(
                    onx, protos, verbose=verbose, fLOG=myprint)
            except RuntimeError as e:
                raise AssertionError(
                    "Unable to inline function %r\n%s\n#####\n%s" % (
                        fct, "\n".join(rows),
                        onnx_simple_text_plot(onx, recursive=True))) from e
            if log:
                print("TIME  INLIN", fct, time.perf_counter() - ti)
            distri = Counter((n.domain, n.op_type)
                             for n in enumerate_onnx_nodes(inlined))
            if ('this', 'dft_last_axis') in distri:
                raise AssertionError(
                    "Inlining went wrong for fct=%r\n----\n%s\n----\n%s" % (
                        fct, pprint.pformat(distri), "\n".join(rows)))
            if len(inlined.functions) > 0:
                raise AssertionError(
                    "Inlining* went wrong for fct=%r\n----\n%s\n----\n%s" % (
                        fct, pprint.pformat(distri), "\n".join(rows)))
            with self.subTest(fct=fct, inline=True):
                try:
                    _check_run(fct, inlined)
                except (RuntimeError, AttributeError, NameError, IndexError) as e:
                    raise AssertionError(
                        "Unable to run inlined function %r"
                        "\n--##--\n--##--inlined\n%s"
                        "\n--##--\n--##--not inlined\n%s"
                        "\n--##--\n--##--log\n%s" % (
                            fct, onnx_simple_text_plot(
                                inlined, recursive=True, raise_exc=False),
                            onnx_simple_text_plot(
                                onx, recursive=True),
                            "\n".join(map(str, rows)))) from e
            with open(os.path.join(temp, fct + '.inlined.onnx'), 'wb') as f:
                f.write(inlined.SerializeToString())
            with open(os.path.join(temp, fct + '.inlined.txt'), 'w') as f:
                f.write(helper.printable_graph(inlined.graph))
            if log:
                print("STEP2 end  ", fct, time.perf_counter() - t)

        if log:
            print()

        # third loop, checking inlined functions with onnxruntime
        from onnxruntime import InferenceSession
        from onnxruntime.capi.onnxruntime_pybind11_state import (  # pylint: disable=E0611
            Fail, InvalidArgument, InvalidGraph)
        for fct, onx in models.items():
            if log:
                t = time.perf_counter()
                print("STEP3 begin", fct)
            try:
                InferenceSession(onx.SerializeToString())
            except (Fail, InvalidArgument, InvalidGraph) as e:
                print(fct, e)
                with open(os.path.join(temp, fct + '.error.onnx'), 'wb') as f:
                    f.write(onx.SerializeToString())
            if log:
                print("STEP2 end  ", fct, time.perf_counter() - t)

    def test_onnx_inline_subgraph(self, log=False):
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        one = helper.make_tensor_value_info(
            'one', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101

        graph1 = helper.make_graph([], 'then', [], [X])
        graph2 = helper.make_graph([], 'else', [], [one])

        graph_def = helper.make_graph(
            [helper.make_node('Constant', [], ['one'], value_floats=[1.]),
             helper.make_node('Greater', ['X', 'one'], ['cond']),
             helper.make_node('If', ['cond'], ['Z'],
                              then_branch=graph1, else_branch=graph2)],
            'test', [X], [Z])

        model_def = helper.make_model(
            graph_def, producer_name='mlprodict',
            ir_version=7, producer_version='0.1',
            opset_imports=[helper.make_operatorsetid('', 15)])
        feeds = {'X': numpy.array([-5], dtype=numpy.float32)}

        for rt in ['python', 'python']:  # , 'onnxruntime1']:
            if log:
                print(rt)
            oinf = OnnxInference(model_def, runtime=rt)
            oinf.check_model()
            got = oinf.run(feeds)

            inlined, m = onnx_inline_function(
                model_def, {}, verbose=1 if log else 0, fLOG=print)
            self.assertEqual(len(m), 0)
            oinf = OnnxInference(inlined)
            oinf.check_model()
            goti = oinf.run(feeds)
            self.assertEqualArray(got['Z'], goti['Z'])

    def test_onnx_inline_subgraph_function(self, log=False):
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        one = helper.make_tensor_value_info(
            'one', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101

        graph1 = helper.make_graph([], 'then', [], [X])
        graph2 = helper.make_graph([], 'else', [], [one])

        func_def = helper.make_function(
            'this', 'fct', ['X'], ['Z'], [
                helper.make_node('Constant', [], ['one'], value_floats=[1.]),
                helper.make_node('Greater', ['X', 'one'], ['cond']),
                helper.make_node('If', ['cond'], ['Z'],
                                 then_branch=graph1, else_branch=graph2)],
            opset_imports=[helper.make_operatorsetid('', 15)])

        graph_def = helper.make_graph(
            [helper.make_node('fct', ['X'], ['Z'], domain='this')],
            'test', [X], [Z])

        model_def = helper.make_model(
            graph_def, producer_name='mlprodict',
            ir_version=7, producer_version='0.1',
            opset_imports=[helper.make_operatorsetid('', 15),
                           helper.make_operatorsetid('this', 1)],
            functions=[func_def])
        feeds = {'X': numpy.array([-5], dtype=numpy.float32)}

        for rt in ['python']:  # , 'onnxruntime1']:
            if log:
                print(rt)
            oinf = OnnxInference(model_def, runtime=rt)
            oinf.check_model()
            got = oinf.run(feeds)

            inlined, m = onnx_inline_function(
                model_def, verbose=3 if log else 0, fLOG=print)
            self.assertNotIn('functions {', str(inlined))
            self.assertEqual(len(m), 1)
            oinf = OnnxInference(inlined)
            oinf.check_model()
            goti = oinf.run(feeds)
            self.assertEqualArray(got['Z'], goti['Z'])
            self.assertEqualArray(
                got['Z'], numpy.array([1], dtype=numpy.float32))

    def test_onnx_inline_subgraph_function2(self, log=False):
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        one = helper.make_tensor_value_info(
            'one', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101

        graph1 = helper.make_graph([], 'then', [], [X])
        graph2 = helper.make_graph([], 'else', [], [one])
        g1 = helper.make_graph(
            [helper.make_node('Greater', ['X', 'one'], ['cond']),
             helper.make_node('If', ['cond'], ['Z'],
                              then_branch=graph1, else_branch=graph2)],
            'test', [], [Z])

        graph1 = helper.make_graph([], 'then', [], [X])
        graph2 = helper.make_graph([], 'else', [], [one])
        g2 = helper.make_graph(
            [helper.make_node('Greater', ['X', 'one'], ['cond']),
             helper.make_node('If', ['cond'], ['Z'],
                              then_branch=graph1, else_branch=graph2)],
            'test', [], [Z])

        func_def = helper.make_function(
            'this', 'fct', ['X'], ['Z'], [
                helper.make_node('Constant', [], ['one'], value_floats=[1.]),
                helper.make_node('Greater', ['X', 'one'], ['cond']),
                helper.make_node('If', ['cond'], ['Z'],
                                 then_branch=g1, else_branch=g2)],
            opset_imports=[helper.make_operatorsetid('', 15)])

        graph_def = helper.make_graph(
            [helper.make_node('fct', ['X'], ['Z'], domain='this')],
            'test', [X], [Z])

        model_def = helper.make_model(
            graph_def, producer_name='mlprodict',
            ir_version=7, producer_version='0.1',
            opset_imports=[helper.make_operatorsetid('', 15),
                           helper.make_operatorsetid('this', 1)],
            functions=[func_def])
        feeds = {'X': numpy.array([-5], dtype=numpy.float32)}

        for rt in ['python', 'python']:  # , 'onnxruntime1']:
            if log:
                print(rt)
            oinf = OnnxInference(model_def, runtime=rt)
            oinf.check_model()
            got = oinf.run(feeds)

            inlined, m = onnx_inline_function(
                model_def, verbose=1 if log else 0, fLOG=print)
            self.assertNotIn('functions {', str(inlined))
            self.assertEqual(len(m), 1)
            oinf = OnnxInference(inlined)
            oinf.check_model()
            goti = oinf.run(feeds)
            self.assertEqualArray(got['Z'], goti['Z'])
            self.assertEqualArray(
                got['Z'], numpy.array([1], dtype=numpy.float32))

    def test_onnx_inline_subgraph_function3_fct(self, log=False):
        # subfct
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        one = helper.make_tensor_value_info(
            'one', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101

        graph1 = helper.make_graph([], 'then', [], [X])
        graph2 = helper.make_graph([], 'else', [], [one])
        g1 = helper.make_graph(
            [helper.make_node('Greater', ['X', 'one'], ['cond']),
             helper.make_node('If', ['cond'], ['Z'],
                              then_branch=graph1, else_branch=graph2)],
            'test', [], [Z])

        graph1 = helper.make_graph([], 'then', [], [X])
        graph2 = helper.make_graph([], 'else', [], [one])
        g2 = helper.make_graph(
            [helper.make_node('Greater', ['X', 'one'], ['cond']),
             helper.make_node('If', ['cond'], ['Z'],
                              then_branch=graph1, else_branch=graph2)],
            'test', [], [Z])

        func_def1 = helper.make_function(
            'this', 'subfct', ['X'], ['Z'], [
                helper.make_node('Constant', [], ['one'], value_floats=[1.]),
                helper.make_node('Greater', ['X', 'one'], ['cond']),
                helper.make_node('If', ['cond'], ['Z'],
                                 then_branch=g1, else_branch=g2)],
            opset_imports=[helper.make_operatorsetid('', 15)])

        # mainfct
        X = helper.make_tensor_value_info(
            'X', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        Z = helper.make_tensor_value_info(
            'Z', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101
        one = helper.make_tensor_value_info(
            'one', TensorProto.FLOAT, ['N'])  # pylint: disable=E1101

        gg1 = helper.make_graph(
            [helper.make_node('subfct', ['X'], ['Z'], domain='this')],
            'then', [], [Z])
        gg2 = helper.make_graph(
            [helper.make_node('subfct', ['X'], ['T'], domain='this'),
             helper.make_node('Neg', ['T'], ['Z'])],
            'else', [], [Z])

        func_def2 = helper.make_function(
            'this', 'mainfct', ['X'], ['Z'], [
                helper.make_node('Constant', [], ['one'], value_floats=[1.]),
                helper.make_node('Greater', ['X', 'one'], ['cond']),
                helper.make_node('If', ['cond'], ['Z'],
                                 then_branch=gg1, else_branch=gg2)],
            opset_imports=[helper.make_operatorsetid('', 15)])

        graph_def = helper.make_graph(
            [helper.make_node('mainfct', ['X'], ['Z'], domain='this')],
            'test', [X], [Z])

        model_def = helper.make_model(
            graph_def, producer_name='mlprodict',
            ir_version=7, producer_version='0.1',
            opset_imports=[helper.make_operatorsetid('', 15),
                           helper.make_operatorsetid('this', 1)],
            functions=[func_def1, func_def2])

        feeds = {'X': numpy.array([-5], dtype=numpy.float32)}

        for rt in ['python']:  # , 'onnxruntime1']:
            if log:
                print(rt)
            oinf = OnnxInference(model_def, runtime=rt)
            oinf.check_model()
            got = oinf.run(feeds)

            inlined, m = onnx_inline_function(
                model_def, verbose=1 if log else 0, fLOG=print)
            self.assertNotIn('functions {', str(inlined))
            self.assertEqual(len(m), 5)

            oinf2 = OnnxInference(model_def)
            oinf2.check_model()
            got2 = oinf2.run(feeds)
            self.assertEqualArray(got['Z'], got2['Z'])

            oinf3 = OnnxInference(inlined)
            oinf3.check_model()
            got3 = oinf3.run(feeds)
            self.assertEqualArray(got['Z'], got3['Z'])


if __name__ == "__main__":
    # TestOptimOnnxManipulations().test_onnx_inline_function_fft(True)
    unittest.main()

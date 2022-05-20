"""
@file
@brief Helpers to run examples created with :epkg:`sklearn-onnx`.
"""
from onnx import helper, TensorProto
from onnx_tools.onnx2py_helper import (
        get_tensor_shape, get_tensor_elem_type)


def _copy_inout(inout, scope, new_name):
    shape = get_tensor_shape(inout)
    elem_type = get_tensor_elem_type(inout)
    value_info = helper.make_tensor_value_info(
        new_name, elem_type, shape)
    return value_info


def _clean_variable_name(name, scope):
    return scope.get_unique_variable_name(name)


def _clean_operator_name(name, scope):
    return scope.get_unique_operator_name(name)


def _clean_initializer_name(name, scope):
    return scope.get_unique_variable_name(name)


def add_onnx_graph(scope, operator, container, onx):
    """
    Adds a whole ONNX graph to an existing one following
    :epkg:`skl2onnx` API assuming this ONNX graph implements
    an `operator <http://onnx.ai/sklearn-onnx/api_summary.html?
    highlight=operator#skl2onnx.common._topology.Operator>`_.

    :param scope: scope (to get unique names)
    :param operator: operator
    :param container: container
    :param onx: ONNX graph
    """
    graph = onx.graph
    name_mapping = {}
    node_mapping = {}
    for node in graph.node:
        name = node.name
        if name is not None:
            node_mapping[node.name] = _clean_initializer_name(
                node.name, scope)
        for o in node.input:
            name_mapping[o] = _clean_variable_name(o, scope)
        for o in node.output:
            name_mapping[o] = _clean_variable_name(o, scope)
    for o in graph.initializer:
        name_mapping[o.name] = _clean_operator_name(o.name, scope)

    inputs = [_copy_inout(o, scope, name_mapping[o.name])
              for o in graph.input]
    outputs = [_copy_inout(o, scope, name_mapping[o.name])
               for o in graph.output]

    for inp, to in zip(operator.inputs, inputs):
        n = helper.make_node('Identity', [inp.onnx_name], [to.name],
                             name=_clean_operator_name('Identity', scope))
        container.nodes.append(n)

    for inp, to in zip(outputs, operator.outputs):
        n = helper.make_node('Identity', [inp.name], [to.onnx_name],
                             name=_clean_operator_name('Identity', scope))
        container.nodes.append(n)

    for node in graph.node:
        n = helper.make_node(
            node.op_type,
            [name_mapping[o] for o in node.input],
            [name_mapping[o] for o in node.output],
            name=node_mapping[node.name] if node.name else None,
            domain=node.domain if node.domain else None)
        n.attribute.extend(node.attribute)  # pylint: disable=E1101
        container.nodes.append(n)

    for o in graph.initializer:
        as_str = o.SerializeToString()
        tensor = TensorProto()
        tensor.ParseFromString(as_str)
        tensor.name = name_mapping[o.name]
        container.initializers.append(tensor)

    # opset
    for oimp in onx.opset_import:
        container.node_domain_version_pair_sets.add(
            (oimp.domain, oimp.version))

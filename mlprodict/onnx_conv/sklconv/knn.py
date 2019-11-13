"""
@file
@brief Rewrites some of the converters implemented in
:epkg:`sklearn-onnx`.
"""
from collections import OrderedDict
import numpy
from skl2onnx.common.data_types import FloatTensorType, DoubleTensorType
from skl2onnx.algebra.onnx_ops import (  # pylint: disable=E0611
    OnnxAbs,
    OnnxArgMax,
    OnnxArrayFeatureExtractor,
    OnnxCast,
    OnnxConcat,
    OnnxDiv,
    OnnxEqual,
    OnnxFlatten,
    OnnxIdentity,
    OnnxMax,
    OnnxMul,
    OnnxPow,
    OnnxReciprocal,
    OnnxReduceMean,
    OnnxReduceSum,
    OnnxReduceSumSquare,
    OnnxReshape,
    OnnxScan,
    OnnxShape,
    OnnxSqrt,
    OnnxTopK_1,
    OnnxTranspose,
    OnnxSub,
)
try:
    from skl2onnx.algebra.onnx_ops import OnnxTopK_10
except ImportError:
    OnnxTopK_10 = None
try:
    from skl2onnx.algebra.onnx_ops import OnnxTopK_11
except ImportError:
    OnnxTopK_11 = None

def onnx_cdist(X, Y, metric='sqeuclidean', dtype=None, op_version=None, **kwargs):
    """
    Returns the ONNX graph which computes
    ``cdist(X, Y, metric=metric)``.

    :param X: :epkg:`numpy:ndarray` or :epkg:`OnnxOperatorMixin`
    :param Y: :epkg:`numpy:ndarray` or :epkg:`OnnxOperatorMixin`
    :param metric: distance type
    :param dtype: *numpy.float32* or *numpy.float64*
    :param op_version: opset version
    :param kwargs: addition parameter
    :return: :epkg:`OnnxOperatorMixin`
    """
    if metric == 'sqeuclidean':
        return _onnx_cdist_sqeuclidean(
            X, Y, dtype=dtype, op_version=op_version, **kwargs)
    elif metric == 'euclidean':
        res = _onnx_cdist_sqeuclidean(X, Y, dtype=dtype, op_version=op_version)
        return OnnxSqrt(res, op_version=op_version, **kwargs)
    elif metric == 'minkowski':
        p = kwargs.pop('p')
        res = _onnx_cdist_minkowski(
            X, Y, dtype=dtype, op_version=op_version, p=p)
        return OnnxPow(res, numpy.array([1. / p], dtype=dtype),
                       op_version=op_version, **kwargs)
    elif metric == 'manhattan':
        return _onnx_cdist_manhattan(
            X, Y, dtype=dtype, op_version=op_version, **kwargs)
    else:
        raise NotImplementedError("metric='{}' is not implemented.".format(
            metric))


def _onnx_cdist_sqeuclidean(X, Y, dtype=None, op_version=None, **kwargs):
    """
    Returns the ONNX graph which computes
    ``cdist(X, metric='sqeuclidean')``.
    """
    diff = OnnxSub('next_in', 'next', output_names=[
                   'diff'], op_version=op_version)
    id_next = OnnxIdentity('next_in', output_names=[
                           'next_out'], op_version=op_version)
    norm = OnnxReduceSumSquare(diff, output_names=['norm'], axes=[
                               1], keepdims=0, op_version=op_version)
    flat = OnnxIdentity(norm, output_names=['scan_out'], op_version=op_version)
    tensor_type = FloatTensorType if dtype == numpy.float32 else DoubleTensorType
    id_next.set_onnx_name_prefix('cdistsqe')
    scan_body = id_next.to_onnx(
        OrderedDict([('next_in', tensor_type()),
                     ('next', tensor_type())]),
        outputs=[('next_out', tensor_type()),
                 ('scan_out', tensor_type())],
        other_outputs=[flat],
        dtype=dtype, target_opset=op_version)

    node = OnnxScan(X, Y, output_names=['u(scan0)', 'u(scan1)'],
                    num_scan_inputs=1, body=scan_body.graph, op_version=op_version)
    return OnnxTranspose(node[1], perm=[1, 0], op_version=op_version,
                         **kwargs)


def _onnx_cdist_minkowski(X, Y, dtype=None, op_version=None, p=2, **kwargs):
    """
    Returns the ONNX graph which computes the :epkg:`Minkowski distance`
    or ``minkowski(X, Y, p)``.
    """
    diff = OnnxSub('next_in', 'next', output_names=[
                   'diff'], op_version=op_version)
    id_next = OnnxIdentity('next_in', output_names=[
                           'next_out'], op_version=op_version)
    diff_pow = OnnxPow(OnnxAbs(diff, op_version=op_version),
                       numpy.array([p], dtype=dtype), op_version=op_version)
    norm = OnnxReduceSum(diff_pow, axes=[1], output_names=[
                         'norm'], keepdims=0, op_version=op_version)
    flat = OnnxIdentity(norm, output_names=['scan_out'], op_version=op_version)
    tensor_type = FloatTensorType if dtype == numpy.float32 else DoubleTensorType
    id_next.set_onnx_name_prefix('cdistmink')
    scan_body = id_next.to_onnx(
        OrderedDict([('next_in', tensor_type()),
                     ('next', tensor_type())]),
        outputs=[('next_out', tensor_type()),
                 ('scan_out', tensor_type())],
        other_outputs=[flat],
        dtype=dtype, target_opset=op_version)

    node = OnnxScan(X, Y, output_names=['u(scan0)', 'u(scan1)'],
                    num_scan_inputs=1, body=scan_body.graph, op_version=op_version)
    return OnnxTranspose(node[1], perm=[1, 0], op_version=op_version,
                         **kwargs)


def _onnx_cdist_manhattan(X, Y, dtype=None, op_version=None, **kwargs):
    """
    Returns the ONNX graph which computes the :epkg:`Minkowski distance`
    or ``minkowski(X, Y, p)``.
    """
    diff = OnnxSub('next_in', 'next', output_names=[
                   'diff'], op_version=op_version)
    id_next = OnnxIdentity('next_in', output_names=[
                           'next_out'], op_version=op_version)
    diff_pow = OnnxAbs(diff, op_version=op_version)
    norm = OnnxReduceSum(diff_pow, axes=[1], output_names=[
                         'norm'], keepdims=0, op_version=op_version)
    flat = OnnxIdentity(norm, output_names=['scan_out'], op_version=op_version)
    tensor_type = FloatTensorType if dtype == numpy.float32 else DoubleTensorType
    id_next.set_onnx_name_prefix('cdistmink')
    scan_body = id_next.to_onnx(
        OrderedDict([('next_in', tensor_type()),
                     ('next', tensor_type())]),
        outputs=[('next_out', tensor_type()),
                 ('scan_out', tensor_type())],
        other_outputs=[flat],
        dtype=dtype, target_opset=op_version)

    node = OnnxScan(X, Y, output_names=['u(scan0)', 'u(scan1)'],
                    num_scan_inputs=1, body=scan_body.graph, op_version=op_version)
    return OnnxTranspose(node[1], perm=[1, 0], op_version=op_version,
                         **kwargs)


def onnx_nearest_neighbors_indices(X, Y, k, metric='euclidean', dtype=None,
                                   op_version=None, keep_distances=False,
                                   optim=None, **kwargs):
    """
    Retrieves the nearest neigbours :epkg:`ONNX`.
    :param X: features or :epkg:`OnnxOperatorMixin`
    :param Y: neighbours or :epkg:`OnnxOperatorMixin`
    :param k: number of neighbours to retrieve
    :param metric: requires metric
    :param dtype: numerical type
    :param op_version: opset version
    :param keep_distance: returns the distances as well (second position)
    :param optim: implements specific optimisations,
        ``'cdist'`` replaces *Scan* operator by operator *CDist*
    :param kwargs: additional parameters for function @see fn onnx_cdist
    :return: top indices
    """
    if optim == 'cdist':
        from skl2onnx.algebra.custom_ops import OnnxCDist
        dist = OnnxCDist(X, Y, metric=metric, op_version=op_version,
                         **kwargs)
    elif optim is None:
        dist = onnx_cdist(X, Y, metric=metric, dtype=dtype,
                          op_version=op_version, **kwargs)
    else:
        raise ValueError("Unknown optimisation '{}'.".format(optim))
    stop
    if op_version < 10:
        neg_dist = OnnxMul(dist, numpy.array(
            [-1], dtype=dtype), op_version=op_version)
        node = OnnxTopK_1(neg_dist, k=k, op_version=1, **kwargs)
    elif op_version < 11:
        neg_dist = OnnxMul(dist, numpy.array(
            [-1], dtype=dtype), op_version=op_version)
        node = OnnxTopK_10(neg_dist, numpy.array([k], dtype=numpy.int64),
                           op_version=10, **kwargs)
    else:
        neg_dist = OnnxMul(dist, numpy.array(
            [-1], dtype=dtype), op_version=op_version)
        node = OnnxTopK_11(neg_dist, numpy.array([k], dtype=numpy.int64),
                           largest=1, sorted=1,
                           op_version=11, **kwargs)

    if keep_distances:
        return (node[1], OnnxMul(node[0], numpy.array(
                    [-1], dtype=dtype), op_version=op_version))
    else:
        return node[1]


def _convert_nearest_neighbors(scope, operator, container):
    """
    Common parts to regressor and classifier. Let's denote
    *N* as the number of observations, *k*
    the number of neighbours. It returns
    the following intermediate results:

    top_indices: [N, k] (int64), best indices for
        every observation
    top_distances: [N, k] (dtype), float distances
        for every observation, it can be None
        if the weights are uniform
    top_labels: [N, k] (label type), labels
        associated to every top index
    weights: [N, k] (dtype), if top_distances is not None,
        returns weights
    norm: [N, k] (dtype), if top_distances is not None,
        returns normalized weights
    axis: 1 if there is one dimension only, 2 if
        this is a multi-regression or a multi classification
    """
    X = operator.inputs[0]
    op = operator.raw_operator
    opv = container.target_opset
    dtype = container.dtype

    options = container.get_options(op, dict(optim=None))

    single_reg = (not hasattr(op, '_y') or len(op._y.shape) == 1 or
                  len(op._y.shape) == 2 and op._y.shape[1] == 1)
    ndim = 1 if single_reg else op._y.shape[1]

    metric = op.effective_metric_
    neighb = op._fit_X.astype(container.dtype)
    k = op.n_neighbors
    training_labels = op._y if hasattr(op, '_y') else None
    distance_kwargs = {}
    if metric == 'minkowski':
        if op.p != 2:
            distance_kwargs['p'] = op.p
        else:
            metric = "euclidean"

    weights = op.weights if hasattr(op, 'weights') else 'distance'
    if weights == 'uniform':
        top_indices = onnx_nearest_neighbors_indices(
            X, neighb, k, metric=metric, dtype=dtype,
            op_version=opv, optim=options.get('optim', None),
            **distance_kwargs)
        top_distances = None
    elif weights == 'distance':
        top_indices, top_distances = onnx_nearest_neighbors_indices(
            X, neighb, k, metric=metric, dtype=dtype,
            op_version=opv, keep_distances=True,
            optim=options.get('optim', None),
            **distance_kwargs)
    else:
        raise RuntimeError(
            "Unable to convert KNeighborsRegressor when weights is callable.")

    shape = OnnxShape(top_indices, op_version=opv)
    flattened = OnnxFlatten(top_indices, op_version=opv)
    if training_labels is not None:
        if ndim > 1:
            # shape = (ntargets, ) + shape
            training_labels = training_labels.T
            shape = OnnxConcat(numpy.array([ndim], dtype=numpy.int64),
                               shape, op_version=opv, axis=0)
            axis = 2
        else:
            training_labels = training_labels.ravel()
            axis = 1

        if training_labels.dtype == numpy.int32:
            training_labels = training_labels.astype(numpy.int64)
        extracted = OnnxArrayFeatureExtractor(
            training_labels, flattened, op_version=opv)
        reshaped = OnnxReshape(extracted, shape, op_version=opv)

        if ndim > 1:
            reshaped = OnnxTranspose(reshaped, op_version=opv, perm=[1, 0, 2])
    else:
        reshaped = None
        axis = 1

    if top_distances is not None:
        modified = OnnxMax(top_distances, numpy.array([1e-6], dtype=dtype),
                           op_version=opv)
        wei = OnnxReciprocal(modified, op_version=opv)
        norm = OnnxReduceSum(wei, op_version=opv, axes=[1], keepdims=0)
    else:
        norm = None
        wei = None

    return top_indices, top_distances, reshaped, wei, norm, axis


def convert_nearest_neighbors_regressor(scope, operator, container):
    """
    Converts :epkg:`sklearn:neighbors:KNeighborsRegressor` into
    :epkg:`ONNX`.
    """
    many = _convert_nearest_neighbors(scope, operator, container)
    _, top_distances, reshaped, wei, norm, axis = many

    opv = container.target_opset
    out = operator.outputs

    if top_distances is not None:
        weighted = OnnxMul(reshaped, wei, op_version=opv)
        res = OnnxReduceSum(weighted, axes=[axis], op_version=opv,
                            keepdims=0)
        res = OnnxDiv(res, norm, op_version=opv, output_names=out)
    else:
        res = OnnxReduceMean(reshaped, axes=[axis], op_version=opv,
                             keepdims=0, output_names=out)
    res.add_to(scope, container)


def convert_nearest_neighbors_classifier(scope, operator, container):
    """
    Converts :epkg:`sklearn:neighbors:KNeighborsClassifier` into
    :epkg:`ONNX`.
    """
    many = _convert_nearest_neighbors(scope, operator, container)
    _, __, reshaped, wei, ___, axis = many

    opv = container.target_opset
    out = operator.outputs
    op = operator.raw_operator
    nb_classes = len(op.classes_)

    if axis == 0:
        raise RuntimeError(
            "Binary classification not implemented in scikit-learn. "
            "Check this code is not reused for other libraries.")

    conc = []
    for cl in range(nb_classes):
        cst = numpy.array([cl], dtype=numpy.int64)
        mat_cast = OnnxCast(
            OnnxEqual(reshaped, cst, op_version=opv),
            op_version=opv,
            to=container.proto_dtype)
        if wei is not None:
            mat_cast = OnnxMul(mat_cast, wei, op_version=opv)
        wh = OnnxReduceSum(mat_cast, axes=[1], op_version=opv)
        conc.append(wh)
    all_together = OnnxConcat(*conc, axis=1, op_version=opv)
    sum_prob = OnnxReduceSum(
        all_together, axes=[1], op_version=opv, keepdims=1)
    probas = OnnxDiv(all_together, sum_prob, op_version=opv,
                     output_names=out[1:])
    res = OnnxArgMax(all_together, axis=axis, op_version=opv,
                     keepdims=0, output_names=out[:1])

    res.add_to(scope, container)
    probas.add_to(scope, container)


def convert_nearest_neighbors_transform(scope, operator, container):
    """
    Converts :epkg:`sklearn:neighbors:NearestNeighbors` into
    :epkg:`ONNX`.
    """
    many = _convert_nearest_neighbors(scope, operator, container)
    top_indices, top_distances = many[:2]

    out = operator.outputs

    ind = OnnxIdentity(top_indices, output_names=out[:1])
    dist = OnnxIdentity(top_distances, output_names=out[1:])

    dist.add_to(scope, container)
    ind.add_to(scope, container)

# Import specific to this model.
from sklearn.linear_model import LinearRegression

from mlprodict.asv_benchmark import _CommonAsvSklBenchmarkRegressor
from mlprodict.onnx_conv import to_onnx  # pylint: disable=W0611
from mlprodict.onnxrt import OnnxInference  # pylint: disable=W0611


class LinearRegression_m_reg_default_9Regressor(_CommonAsvSklBenchmarkRegressor):
    "asv example for a regressor"
    # Full template can be found in
    # https://github.com/sdpython/mlprodict/blob/master/mlprodict/asv_benchmark/common_asv_skl.py>`_

    params = [
        ['skl', 'pyrt'],
        [1, 100, 10000],
        [4, 20],
    ]
    param_names = ['rt', 'N', 'nf']
    target_opset = 9

    def _create_model(self):
        return LinearRegression()

try:
    from inFairness import fairalgo
    from skorch import NeuralNet
    from skorch.dataset import unpack_data, Dataset as Dataset_
    from skorch.utils import is_pandas_ndframe
except ImportError as error:
    from logging import warning
    warning("{}: SenSeI and SenSR will be unavailable. To install, run:\n"
            "pip install 'aif360[inFairness]'".format(error))
    Dataset_ = NeuralNet = object
from sklearn.preprocessing import LabelBinarizer
from sklearn.utils.multiclass import type_of_target
from sklearn.exceptions import NotFittedError


class Dataset(Dataset_):
    """A generic dataset class inheriting from :class:`skorch.dataset.Dataset`
    which simply converts DataFrames to arrays instead of treating them like
    dicts.
    """
    def __init__(self, X, y=None, length=None):
        if is_pandas_ndframe(X):
            X = X.values
        if y is not None and is_pandas_ndframe(y):
            y = y.values
        super().__init__(X, y=y, length=length)

class InFairnessNet(NeuralNet):
    """Base class for models which incorporate inFairness algorithms."""
    def __init__(self, *args, criterion, train_split=None, regression='auto',
                 dataset=Dataset, **kwargs):
        """
        Args:
            criterion (torch.nn.Module, keyword-only): Loss function.
            train_split (callable, optional): See :class:`skorch.net.NeuralNet`.
                Note: validation loss *does not* include any fairness loss, only
                the provided criterion, and should not be used for early
                stopping, etc. Default is None (no split).
            regression (bool or 'auto'): Task is regression. If 'auto', this is
                inferred using :func:`sklearn.utils.multiclass.type_of_target`
                on y in fit(). If a Dataset is provided to fit, this defaults to
                False. If y contains 'soft' targets (i.e. probabilities per
                class), this should be manually set to False.
        """
        super().__init__(*args, criterion=criterion, train_split=train_split,
                         dataset=dataset, **kwargs)
        self.regression = regression

    @property
    def _estimator_type(self):
        if hasattr(self, "regression_"):
            return 'regressor' if self.regression_ else 'classifier'
        elif self.regression != 'auto':
            return 'regressor' if self.regression else 'classifier'
        else:
            raise NotFittedError("regression is set to 'auto'. Call 'fit' with "
                    "appropriate arguments or set regression manually.")

    def get_loss(self, y_pred, y_true, X=None, training=False):
        """Return the loss for this batch.

        Parameters
        ----------
        y_pred : torch tensor
          Predicted target values

        y_true : torch tensor
          True target values.

        X : input data, compatible with skorch.dataset.Dataset
          By default, you should be able to pass:

            * numpy arrays
            * torch tensors
            * pandas DataFrame or Series
            * scipy sparse CSR matrices
            * a dictionary of the former three
            * a list/tuple of the former three
            * a Dataset

          If this doesn't work with your data, you have to pass a
          ``Dataset`` that can deal with the data.

        training : bool (default=False)
          Whether train mode should be used or not.

        """
        if training:
            return y_pred.loss
        else:
            return super().get_loss(y_pred.y_pred, y_true)

    def train_step_single(self, batch, **fit_params):
        """Compute y_pred, loss value, and update net's gradients.

        The module is set to be in train mode (e.g. dropout is
        applied).

        Parameters
        ----------
        batch
          A single batch returned by the data loader.

        **fit_params : dict
          Additional parameters passed to the ``forward`` method of
          the module and to the ``self.train_split`` call.

        Returns
        -------
        step : dict
          A dictionary ``{'loss': loss, 'y_pred': y_pred}``, where the
          float ``loss`` is the result of the loss function and
          ``y_pred`` the prediction generated by the PyTorch module.

        """
        self._set_training(True)
        Xi, yi = unpack_data(batch)
        response = self.infer(Xi, Y=yi, **fit_params)
        loss = self.get_loss(response, yi, X=Xi, training=True)
        loss.backward()
        return {
            'loss': loss,
            'y_pred': response.y_pred,
        }

    def validation_step(self, batch, **fit_params):
        """Perform a forward step using batched data and return the
        resulting loss.

        The module is set to be in evaluation mode (e.g. dropout is
        not applied).

        Parameters
        ----------
        batch
          A single batch returned by the data loader.

        **fit_params : dict
          Additional parameters passed to the ``forward`` method of
          the module and to the ``self.train_split`` call.

        """
        step = super().validation_step(batch, **fit_params)
        return {'loss': step['loss'], 'y_pred': step['y_pred'].y_pred}

    def evaluation_step(self, batch, training=False):
        """Perform a forward step to produce the output used for
        prediction and scoring.

        Therefore, the module is set to evaluation mode by default
        beforehand which can be overridden to re-enable features
        like dropout by setting ``training=True``.

        Parameters
        ----------
        batch
          A single batch returned by the data loader.

        training : bool (default=False)
          Whether to set the module to train mode or not.

        Returns
        -------
        y_infer
          The prediction generated by the module.

        """
        return super().evaluation_step(batch, training=training).y_pred

    def fit(self, X, y, **fit_params):
        """Initialize and fit the model.

        If the module was already initialized, by calling fit, the module will
        be re-initialized (unless ``warm_start`` is True).

        Args:
            X (array-like): Training samples.
            y (array-like): Training labels. If X is a Dataset that contains
                the target, y may be set to ``None``. Note: if ``regression`` is
                'auto' in this case, classification will be assumed. If y is
                already binary/ordinal encoded (i.e., the unique labels consist
                of the integers from [0, C)) it is passed as-is, however, if y
                contains nominal values, it is encoded with
                :class:`sklearn.preprocessing.LabelBinarizer` and cast to
                'float32' for compatibility with torch loss functions.
                Regression targets are also left unmodified.
            **fit_params: Additional parameters passed to the `forward`` method
                of the module and to the ``self.train_split`` call.

        Returns:
            self
        """
        self.regression_ = self.regression
        if y is not None and self.regression_ is not True:
            ttype = type_of_target(y)
            if ttype in ("binary", "multiclass", "multilabel-indicator"):
                lb = LabelBinarizer().fit(y)
                self.classes_ = lb.classes_
                if self.classes_.tolist() != list(range(len(self.classes_))):
                    y = lb.transform(y).astype('float32')
            elif "continuous" in ttype and self.regression_ == 'auto':
                self.regression_ = True
            else:
                raise ValueError(f'Detected {ttype} type y with regression='
                    f'{self.regression}. This combination is not supported.')
        if self.regression_ == 'auto':
            self.regression_ = False
        return super().fit(X, y, **fit_params)

    def predict(self, X):
        """Return class labels for samples in X if task is classification or
        predicted values if task is regression.

        Args:
            X (array-like): Test samples.

        Returns:
            numpy.ndarray: Test predictions.

        See also:
            :meth:`skorch.net.NeuralNet.predict`
        """
        if self.regression_:
            return super().predict(X)
        elif hasattr(self, "classes_"):
            return self.classes_[self.predict_proba(X).argmax(axis=1)]
        else:
            return self.predict_proba(X).argmax(axis=1)

class SenSeI(InFairnessNet):
    """Sensitive Set Invariance (SenSeI).

    SenSeI is an in-processing method for individual fairness [#yurochkin20]_.
    In this method, individual fairness is formulated as invariance on certain
    sensitive sets. SenSeI minimizes a transport-based regularizer that enforces
    this version of individual fairness.

    References:
        .. [#yurochkin20] `M. Yurochkin and Y. Sun, "SenSeI: Sensitive Set
           Invariance for Enforcing Individual Fairness." International
           Conference on Learning Representations, 2021.
           <https://arxiv.org/abs/2006.14168>`_

    See also:
        :class:`inFairness.fairalgo.SenSeI`

    Attributes:
        regression_ (bool): Whether or not this task is treated as regression.
        classes_ (array, shape (n_classes,)): A list of class labels known to
            the transformer. Only present if ``self.regression_`` is False and
            y is provided to ``fit``.
        module_ (inFairness.fairalgo.SenSeI): The fair PyTorch module.
    """
    def __init__(self, module, *, criterion, distance_x, distance_y, rho, eps,
                 auditor_nsteps, auditor_lr, regression='auto', **kwargs):
        """
        Args:
            module (torch.nn.Module): Network architecture.
            criterion (torch.nn.Module): Loss function.
            distance_x (inFairness.distances.Distance): Distance metric in the
                input space.
            distance_y (inFairness.distances.Distance): Distance metric in the
                output space.
            rho (float): :math:`\\rho` parameter in the SenSeI algorithm.
            eps (float): :math:`\epsilon` parameter in the SenSeI algorithm.
            auditor_nsteps (int): Number of update steps for the auditor to find
                worst-case examples
            auditor_lr (float): Learning rate for the auditor.
            regression (bool or 'auto'): Task is regression. If 'auto', this is
                inferred using :func:`sklearn.utils.multiclass.type_of_target`
                on y in fit(). If a Dataset is provided to fit, this defaults to
                False. If y contains 'soft' targets (i.e. probabilities per
                class), this should be manually set to False.
            train_split (callable, optional): See :class:`skorch.net.NeuralNet`.
                Note: validation loss *does not* include any fairness loss, only
                the provided criterion, and should not be used for early
                stopping, etc. Default is None (no split).
            **kwargs: See :class:`skorch.net.NeuralNet`.
        """
        self.distance_x = distance_x
        self.distance_y = distance_y
        self.rho = rho
        self.eps = eps
        self.auditor_nsteps = auditor_nsteps
        self.auditor_lr = auditor_lr

        super().__init__(module=module, criterion=criterion,
                         regression=regression, **kwargs)

    def initialize_module(self):
        """Initializes the module.

        If the module is already initialized and no parameter was changed, it
        will be left as is.
        """
        self.initialize_criterion()
        kwargs = self.get_params_for('module')
        network = self.initialized_instance(self.module, kwargs)

        sensei_kwargs = {
            'network': network,
            'loss_fn': self.criterion_,
            'distance_x': self.distance_x,
            'distance_y': self.distance_y,
            'rho': self.rho,
            'eps': self.eps,
            'auditor_nsteps': self.auditor_nsteps,
            'auditor_lr': self.auditor_lr,
        }
        self.module_ = self.initialized_instance(fairalgo.SenSeI, sensei_kwargs)
        return self

class SenSR(InFairnessNet):
    """Sensitive Subspace Robustness (SenSR).

    SenSR is an in-processing method for individual fairness which enforces
    performance invariance under certain sensitive perturbations to the input
    [#yurochkin19]_.

    References:
        .. [#yurochkin19] `M. Yurochkin, A. Bower, and Y. Sun, "Training
           individually fair ML models with sensitive subspace robustness."
           International Conference on Learning Representations, 2020.
           <https://arxiv.org/abs/1907.00020>`_

    See also:
        :class:`inFairness.fairalgo.SenSR`

    Attributes:
        regression_ (bool): Whether or not this task is treated as regression.
        classes_ (array, shape (n_classes,)): A list of class labels known to
            the transformer. Only present if ``self.regression_`` is False and
            y is provided to ``fit``.
        module_ (inFairness.fairalgo.SenSR): The fair PyTorch module.
    """
    def __init__(self, module, *, criterion, distance_x, eps, lr_lamb, lr_param,
                 auditor_nsteps, auditor_lr, regression='auto', **kwargs):
        """
        Args:
            module (torch.nn.Module): Network architecture.
            criterion (torch.nn.Module): Loss function.
            distance_x (inFairness.distances.Distance): Distance metric in the
                input space.
            eps (float): :math:`\epsilon` parameter in the SenSR algorithm.
            lr_lamb (float): :math:`\lambda` parameter in the SenSR algorithm.
            lr_param (float): :math:`\\alpha` parameter in the SenSR algorithm.
            auditor_nsteps (int): Number of update steps for the auditor to find
                worst-case examples
            auditor_lr (float): Learning rate for the auditor.
            regression (bool or 'auto'): Task is regression. If 'auto', this is
                inferred using :func:`sklearn.utils.multiclass.type_of_target`
                on y in fit(). If a Dataset is provided to fit, this defaults to
                False. If y contains 'soft' targets (i.e. probabilities per
                class), this should be manually set to False.
            train_split (callable, optional): See :class:`skorch.net.NeuralNet`.
                Note: validation loss *does not* include any fairness loss, only
                the provided criterion, and should not be used for early
                stopping, etc. Default is None (no split).
            **kwargs: See :class:`skorch.net.NeuralNet`.
        """
        self.distance_x = distance_x
        self.eps = eps
        self.lr_lamb = lr_lamb
        self.lr_param = lr_param
        self.auditor_nsteps = auditor_nsteps
        self.auditor_lr = auditor_lr

        super().__init__(module=module, criterion=criterion,
                         regression=regression, **kwargs)

    def initialize_module(self):
        """Initializes the module.

        If the module is already initialized and no parameter was changed, it
        will be left as is.
        """
        self.initialize_criterion()
        kwargs = self.get_params_for('module')
        network = self.initialized_instance(self.module, kwargs)

        sensr_kwargs = {
            'network': network,
            'loss_fn': self.criterion_,
            'distance_x': self.distance_x,
            'eps': self.eps,
            'lr_lamb': self.lr_lamb,
            'lr_param': self.lr_param,
            'auditor_nsteps': self.auditor_nsteps,
            'auditor_lr': self.auditor_lr,
        }
        self.module_ = self.initialized_instance(fairalgo.SenSR, sensr_kwargs)
        return self
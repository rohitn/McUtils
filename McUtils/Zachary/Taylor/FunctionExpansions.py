from ..LazyTensors import Tensor
from .Derivatives import FiniteDifferenceDerivative
from ...Coordinerds import CoordinateSet, CoordinateSystem
from ..Symbolic import TensorDerivativeConverter
from ...Numputils import vec_tensordot
import numpy as np, itertools, copy

__all__ = [
    'FunctionExpansion'
]

########################################################################################################################
#
#                                           FunctionExpansion
#
class FunctionExpansionException(Exception):
    pass
class FunctionExpansion:
    """
    A class for handling expansions of an arbitrary function
    given a set of derivatives and also allows for coordinate
    transformations if the appropriate derivatives are supplied.

    Can be used to handle multiple expansions simultaneously, but requires
    that all expansions are provided up to the same order.

    """

    def __init__(self,
                 derivatives,
                 transforms=None,
                 center=None,
                 ref=0,
                 weight_coefficients=False
                 ):
        """
        :param derivatives: Derivatives of the function being expanded
        :type derivatives: Iterable[np.ndarray | Tensor]
        :param transforms: Jacobian and higher order derivatives in the coordinates
        :type transforms: Iterable[np.ndarray | Tensor] | None
        :param center: the reference point for expanding aobut
        :type center: np.ndarray | None
        :param ref: the reference point value for shifting the expansion
        :type ref: float | np.ndarray
        :param weight_coefficients: whether the derivative terms need to be weighted or not
        :type weight_coefficients: bool
        """

        # raise NotImplementedError("doesn't deal with higher-order expansions properly yet")
        self._derivs = self.FunctionDerivatives(derivatives, weight_coefficients)
        self._center = np.asanyarray(center) if center is not None else center
        self.ref = np.asanyarray(ref) if not isinstance(ref, (int, float, np.integer, np.floating)) else ref
        if transforms is None:
            self._transf = None
        else:
            # transformation matrices from cartesians to internals
            self._transf = self.CoordinateTransforms(transforms)
        self._tensors = None
    @property
    def center(self):
        return self._center
    @property
    def is_multiexpansion(self):
        return self._derivs[0].ndim > 1
    @classmethod
    def multiexpansion(cls, *expansions):
        return cls(
            list(zip(*[e.expansion_tensors for e in expansions])),
            center=np.asanyarray([e.center for e in expansions]),
            ref=np.asanyarray([e.ref for e in expansions]),
            weight_coefficients=False
        )
    @classmethod
    def expand_function(cls,
                        f, point,
                        order=4,
                        basis=None,
                        function_shape=None,
                        transforms=None,
                        weight_coefficients=True,
                        **fd_options
                        ):
        """
        Expands a function about a point up to the given order

        :param f:
        :type f: function
        :param point:
        :type point: np.ndarray | CoordinateSet
        :param order:
        :type order: int
        :param basis:
        :type basis: None | CoordinateSystem
        :param fd_options:
        :type fd_options:
        :return:
        :rtype:
        """

        derivs = FiniteDifferenceDerivative(f, function_shape=function_shape)(point, **fd_options)
        ref = f(point)
        dts = [derivs.derivative_tensor(i) for i in range(1, order+1)]
        if transforms is None:
            if basis is not None and isinstance(point, CoordinateSet):
                transforms = [point.jacobian(basis, order=i) for i in range(order)]
            else:
                transforms = None
        return cls(dts, center=point, ref=ref, transforms=transforms, weight_coefficients=weight_coefficients)

    @property
    def expansion_tensors(self):
        """
        Provides the tensors that will contracted

        :return:
        :rtype: Iterable[np.ndarray]
        """
        if self._tensors is None:
            if self._transf is None:
                self._tensors = self._derivs
            else:
                self._tensors = TensorDerivativeConverter(self._transf, self._derivs).convert()
        return self._tensors
    @expansion_tensors.setter
    def expansion_tensors(self, tensors):
        """
        Are we going to assume in setting the tensors that
        people have done any requisite coordinate transformations?

        -> I think that's leaving room open for nasty surprises since we have
        the `_transf_ member
        -> but the `expansion_tensors` are in general expected to ... be transformed?

        Which means that we need _two_ properties 1) these tensors and 2) the derivs
        neither of which is transformed when being set
        """
        self._tensors = tensors

    @property
    def derivative_tensors(self):
        """
        Provides the base derivative tensors
        independent of any coordinate transformations

        :return:
        :rtype: Iterable[np.ndarray]
        """
        return self._derivs
    @derivative_tensors.setter
    def derivative_tensors(self, derivs):
        self._tensors = derivs

    def get_expansions(self, coords, subexpansions=None, outer=True, squeeze=True):
        """

        :param coords: Coordinates to evaluate the expansion at
        :type coords: np.ndarray | CoordinateSet
        :param subexpansions: A set of tensor expansion indices to use if we have a multiexpansion
        but only want some subset of the relevant points
        :type subexpansions: int | Iterable[int]
        :return:
        :rtype:
        """

        if not outer and not self.is_multiexpansion:
            raise ValueError("outer doesn't make sense without multiexpansion")
        outer = (not self.is_multiexpansion) or outer
        # doesn't really make sense if we don't have stuff to take the outer product over

        coords = np.asanyarray(coords)
        cshape = coords.shape # so we can squeeze at the end if need be
        if coords.ndim == 1:
            coords = coords[np.newaxis]
            outer = True # again...doesn't make sense _not_ to take an outer product here
        elif coords.ndim >= 2:
            if outer:
                if coords.ndim > 2: # we want to apply each expansion to each point
                    coords = np.reshape(coords, (-1, cshape[-1]))
            else:
                # we assume the first dimension is shared between the
                # multi-expansion and the coordinates
                coords = np.reshape(coords, (cshape[0], -1, cshape[-1]))

        center = self._center
        if center is None:
            # we assume we have a vector of points
            disp = coords
        else:
            # by default we take the outer product through
            # broacasting, but if outer==False I want to be
            # able to just thread things and require that the number
            # of vectors of points is the same as the numbers of expansions
            # which I think has to map onto the number of centers
            if outer:
                if center.ndim == 1:
                    center = center[np.newaxis]
                else:
                    center = center[np.newaxis, :, :]
                    coords = coords[:, np.newaxis]
            else:
                # we need to coerce things into the appropriate form
                # and by now we _know_ coords is rank three and now we just
                # need to make sure that center has the appropriate shape
                # for this
                if center.ndim == 1:
                    center = center[np.newaxis, np.newaxis]
                else:
                    center = center[:, np.newaxis, :] # need to broadcast along axis 1
                    # coords = coords[:, np.newaxis]

            disp = coords - center

        if isinstance(subexpansions, (int, np.integer)):
            subexpansions = [subexpansions]

        expansions=[]
        for i, tensr in enumerate(self.expansion_tensors):
            if subexpansions is not None:
                tensr = tensr[subexpansions] # I think it's really this simple...?
                # TBH I'm not entirely sure why one would want to use this kind of subexpansion
                # since it's generally not that expensive to build one of the smaller expansions
                # but it's nice to have the option since I can see this being a small optimization on the
                # edge somewhere.
            # contract the tensor by the displacements until it's completely reduced
            if outer:
                tensr = np.broadcast_to(tensr[np.newaxis], (disp.shape[0],) + tensr.shape)
            for j in range(i+1):
                # try:
                tensr = vec_tensordot(disp, tensr, axes=[[-1], [tensr.ndim-1]])
                # except:
                #     raise ValueError(disp.shape, tensr.shape, -1, tensr.ndim)
            contraction = tensr
            if squeeze:
                contraction = contraction.squeeze()
            expansions.append(contraction)

        if len(cshape) == 1:
            expansions = [np.squeeze(e) for e in expansions]
        elif len(cshape) > 2:
            new_shape = cshape[:-1]
            if outer:
                # need to reshape including the broadcast shape...
                # but at each order the contraction should be complete
                # meaning we lose the final dimension
                new_shape = (-1) + new_shape
            expansions = [np.reshape(e, new_shape) for e in expansions]


        return expansions
    def expand(self, coords, outer=True, squeeze=True):
        """Returns a numerical value for the expanded coordinates

        :param coords:
        :type coords: np.ndarray
        :return:
        :rtype: float | np.ndarray
        """
        ref = self.ref
        exps = self.get_expansions(coords, outer=outer, squeeze=squeeze)
        return ref + sum(exps)

    def __call__(self, coords, **kw):
        return self.expand(coords, **kw)

    class CoordinateTransforms:
        def __init__(self, transforms):
            self._transf = [np.asanyarray(t) for t in transforms]
        def __getitem__(self, i):
            if len(self._transf) < i:
                raise FunctionExpansionException("{}: transformations requested up to order {} but only provided to order {}".format(
                    type(self).__name__,
                    i,
                    len(self._transf)
                ))
            return self._transf[i]
        def __len__(self):
            return len(self._transf)
    class FunctionDerivatives:
        def __init__(self, derivs, weight_coefficients=True):
            self.derivs = [ np.asanyarray(t) for t in derivs ]
            if weight_coefficients:
                self.derivs = [self.weight_derivs(t, o+1) if weight_coefficients else t for o, t in enumerate(self.derivs)]
        def weight_derivs(self, t, order = None):
            """

            :param order:
            :type order: int
            :param t:
            :type t: Tensor
            :return:
            :rtype:
            """
            weighted = t
            if order is None:
                order = len(t.shape)
            if order > 1:
                weighted = weighted * (1/np.math.factorial(order))
                # s = t.shape
                # weights = np.ones(s)
                # all_inds = list(range(len(s)))
                # for i in range(2, order+1):
                #     for inds in itertools.combinations(all_inds, i):
                #         # define a diagonal slice through
                #         sel = tuple(slice(None, None, None) if a not in inds else np.arange(s[a]) for a in all_inds)
                #         weights[sel] = 1/np.math.factorial(i)
                # weighted = weighted.mul(weights)
                # print(weights, weighted.array)

            return weighted

        def __getitem__(self, i):
            if len(self.derivs) < i:
                raise FunctionExpansionException("{}: derivatives requested up to order {} but only provided to order {}".format(
                    type(self).__name__,
                    i,
                    len(self.derivs)
                ))
            return self.derivs[i]
        def __len__(self):
            return len(self.derivs)

    def deriv(self, which=None):
        """
        Computes the derivative(s) of the expansion(s) with respect to the
        supplied coordinates (`which=None` means compute the gradient)

        :param which:
        :type which:
        :return:
        :rtype:
        """

        expansions = self.expansion_tensors
        smol = isinstance(which, int)
        if smol:
            which = [which]
        elif which is None:
            which = list(range(expansions[0].shape[-1]))

        res = []
        cls = type(self)
        for i in which:
            derivs = []
            for j,e in enumerate(expansions):
                # need to know the shift dims?.... ?
                base_slice = tuple(slice(None, None, None) for _ in range(j+1))
                red = 0
                for k in range(j+1):
                    s = (...,) + base_slice[:k] + (i,) + base_slice[k+1:]
                    red = red + e[s] # this iteration is how we get the different multiples...?
                    # and even though it seems like it makes off diagonal mat els contribute too much
                    # this is actually correct!
                derivs.append(red)
            res.append(cls(
                derivs[1:],
                ref=derivs[0],
                center=self._center,
                weight_coefficients=False
            ))
        return cls.multiexpansion(*res)

    @classmethod
    def from_indices(cls, inds, ref=0, expansion_order=None, ndim=None, symmetrize=True, **opts):
        if isinstance(inds, dict):
            inds = tuple(inds.items())
        ref = ref
        if ndim is None or expansion_order is None:
            if ndim is None:
                ndim = 0
            if expansion_order is None:
                expansion_order = 0
            for (i, v) in inds: # prescan to get tensor dimensions
                if len(i) == 0:
                    continue
                expansion_order = max(expansion_order, len(i))
                ndim = max(ndim, max(i)+1)
        t = [np.zeros((ndim,)*n) for n in range(1, expansion_order+1)]
        for (i, v) in inds:
            if len(i) == 0:
                ref = v
                continue
            tens = t[len(i)-1]
            if symmetrize:
                for p in itertools.permutations(i):
                    tens[p] = v
            else:
                tens[i] = v
        return cls(
            t,
            ref=ref,
            **opts
        )







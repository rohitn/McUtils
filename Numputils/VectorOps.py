"""
A module of useful math for handling coordinate transformations and things
"""

import numpy as np

__all__ = [
    "vec_dots",
    "vec_normalize",
    "vec_norms",
    "vec_tensordot",
    "vec_tdot",
    "vec_crosses",
    "vec_angles",
    "vec_sins",
    "vec_cos",
    "vec_outer",
    "pts_normals",
    "pts_dihedrals",
    "mat_vec_muls",
    "one_pad_vecs",
    "affine_multiply"
]

##
# NOTE: The design of a lot of this stuff needs a bit of work
#       Like should it work with things that aren't just stacks of vectors?
#       Or should it all be specifically for vector-vector operations?
#       Lots of it doesn't even make sense in a non-vector context...
#       But then there's also like "vec_tensordot" which is explicitly non-vector in scope...
#       Not sure what exactly I want with this. Lots of stuff TBD.

################################################
#
#       vec_dots
#

def vec_dots(vecs1, vecs2, axis=-1):
    """
    Computes the pair-wise dot product of two lists of vecs using np.matmul

    :param vecs1:
    :type vecs1:
    :param vecs2:
    :type vecs2:
    """

    vecs1 = np.expand_dims(vecs1, axis-1)
    vecs2 = np.expand_dims(vecs2, axis)
    res = np.matmul(vecs1, vecs2)
    res_shape = res.shape

    for _ in range(2):
        if res_shape[axis] == 1:
            res = res.reshape(np.delete(res_shape, axis))
            res_shape = res.shape

    return res

################################################
#
#       vec_norms
#

def vec_norms(vecs, axis=-1):
    """

    :param vecs:
    :type vecs: np.ndarray
    :param axis:
    :type axis: int
    :return:
    :rtype:
    """
    return np.linalg.norm(vecs, axis=-1)

################################################
#
#       vec_normalize
#

def vec_normalize(vecs, axis=-1):
    """

    :param vecs:
    :type vecs: np.ndarray
    :param axis:
    :type axis: int
    :return:
    :rtype:
    """
    norms = vec_norms(vecs)[..., np.newaxis]
    return vecs/norms

################################################
#
#       vec_crosses
#

def vec_crosses(vecs1, vecs2, normalize=False, axis=-1):
    crosses = np.cross(vecs1, vecs2, axis=axis)
    if normalize:
        crosses = crosses/vec_norms(crosses, axis=axis)[..., np.newaxis]
    return crosses

################################################
#
#       vec_cos
#

def vec_cos(vectors1, vectors2, axis=-1):
    """Gets the cos of the angle between two vectors

    :param vectors1:
    :type vectors1: np.ndarray
    :param vectors2:
    :type vectors2: np.ndarray
    """
    dots   = vec_dots(vectors1, vectors2, axis=axis)
    norms1 = vec_norms(vectors1, axis=axis)
    norms2 = vec_norms(vectors2, axis=axis)

    return dots/(norms1*norms2)

################################################
#
#       vec_sins
#

def vec_sins(vectors1, vectors2, axis=-1):
    """Gets the sin of the angle between two vectors

    :param vectors1:
    :type vectors1: np.ndarray
    :param vectors2:
    :type vectors2: np.ndarray
    """
    crosses= vec_crosses(vectors1, vectors2, axis=axis)
    norms1 = vec_norms(vectors1, axis=axis)
    norms2 = vec_norms(vectors2, axis=axis)

    return crosses/(norms1*norms2)


################################################
#
#       vec_angles
#

def vec_angles(vectors1, vectors2, axis=-1):
    """Gets the angles and normals between two vectors

    :param vectors1:
    :type vectors1: np.ndarray
    :param vectors2:
    :type vectors2: np.ndarray
    :return: angles and normals between two vectors
    :rtype: (np.ndarray, np.ndarray)
    """
    dots    = vec_dots(vectors1, vectors2, axis=axis)
    crosses = vec_crosses(vectors1, vectors2, axis=axis)
    norms1  = vec_norms(vectors1, axis=axis)
    norms2  = vec_norms(vectors2, axis=axis)
    norm_prod = norms1*norms2
    cos_comps = dots/norm_prod
    cross_norms = vec_norms(crosses, axis=axis)
    sin_comps = cross_norms/norm_prod

    return (np.arctan2(sin_comps, cos_comps), crosses)

################################################
#
#       vec_normals
#
def vec_outer(a, b, axes=None):
    """
    Provides the outer product of a and b in a vectorized way.
    Currently not entirely convinced I'm doing it right :|

    :param a:
    :type a:
    :param b:
    :type b:
    :param axis:
    :type axis:
    :return:
    :rtype:
    """
    # we'll treat this like tensor_dot:
    #   first we turn this into a plain matrix
    #   then we do the outer on the matrix
    #   then we cast back to the shape we want
    if axes is None:
        if a.ndim > 1:
            axes = [-1, -1]
        else:
            axes = [0, 0]

    # we figure out how we'd conver
    a_ax = axes[0]
    if isinstance(a_ax, (int, np.integer)):
        a_ax = [a_ax]
    a_ax = [ax + a.ndim if ax<0 else ax for ax in a_ax]
    a_leftover = [x for x in range(a.ndim) if x not in a_ax]
    a_transp = a_leftover + a_ax
    a_shape = a.shape
    a_old_shape = [a_shape[x] for x in a_leftover]
    a_subshape = [a_shape[x] for x in a_ax]
    a_contract = a_old_shape + [np.prod(a_subshape)]

    b_ax = axes[1]
    if isinstance(b_ax, (int, np.integer)):
        b_ax = [b_ax]
    b_ax = [ax + b.ndim if ax<0 else ax for ax in b_ax]
    b_leftover = [x for x in range(b.ndim) if x not in b_ax]
    b_transp = b_leftover + b_ax
    b_shape = b.shape
    b_old_shape = [b_shape[x] for x in b_leftover]
    b_subshape = [b_shape[x] for x in b_ax]
    b_contract = b_old_shape + [np.prod(b_subshape)]

    a_new = a.transpose(a_transp).reshape(a_contract)
    b_new = b.transpose(b_transp).reshape(b_contract)

    outer = a_new[..., :, np.newaxis] * b_new[..., np.newaxis, :]

    # now we put the shapes right again and revert the transposition
    # base assumption is that a_old_shape == b_old_shape
    # if not we'll get an error anyway
    final_shape = a_old_shape + a_subshape + b_subshape

    res = outer.reshape(final_shape)
    final_transp = np.argsort(a_leftover + a_ax + b_ax)

    return res.transpose(final_transp)

#################################################################################
#
#   vec_tensordot
#
def vec_tensordot(tensa, tensb, axes=2):
    """Defines a version of tensordot that uses matmul to operate over stacks of things
    Basically had to duplicate the code for regular tensordot but then change the final call

    :param tensa:
    :type tensa:
    :param tensb:
    :type tensb:
    :param axes:
    :type axes:
    :return:
    :rtype:
    """

    if isinstance(axes, (int, np.integer)):
        axes = (list(range(-axes, 0)), list(range(0, axes)))
    axes_a, axes_b = axes
    try:
        na = len(axes_a)
        axes_a = list(axes_a)
    except TypeError:
        axes_a = [axes_a]
        na = 1
    try:
        nb = len(axes_b)
        axes_b = list(axes_b)
    except TypeError:
        axes_b = [axes_b]
        nb = 1

    a, b = np.asarray(tensa), np.asarray(tensb)

    axes_a = [ax if ax >= 0 else a.ndim + ax for ax in axes_a]
    axes_b = [ax if ax >= 0 else b.ndim + ax for ax in axes_b]
    a_shape = tensa.shape
    b_shape = tensb.shape
    shared = 0
    for shared, s in enumerate(zip(a_shape, b_shape)):
        if s[0] != s[1]:
            break
        shared = shared + 1

    # the minimum number of possible shared axes
    # is constrained by the contraction of axes
    shared = min(shared, min(axes_a), min(axes_b))

    if shared == 0:
        return np.tensordot(a, b, axes=axes)

    as_ = a_shape
    nda = a.ndim
    bs = b.shape
    ndb = b.ndim

    equal = True
    if na != nb:
        equal = False
        raise ValueError("{}: shape-mismatch ({}) and ({}) in number of axes to contract over".format(
            "vec_tensordot",
            na,
            nb
        ))
    else:
        for k in range(na):
            if as_[axes_a[k]] != bs[axes_b[k]]:
                equal = False
                raise ValueError("{}: shape-mismatch ({}) and ({}) in contraction over axes ({}) and ({})".format(
                    "vec_tensordot",
                    axes_a[k],
                    axes_b[k],
                    na,
                    nb
                    ))
            if axes_a[k] < 0:
                axes_a[k] += nda
            if axes_b[k] < 0:
                axes_b[k] += ndb

    # Move the axes to sum over to the end of "a"
    # and to the front of "b"
    # preserve things so that the "shared" stuff remains at the fron of both of these...
    notin_a = [k for k in range(nda) if k not in axes_a]
    newaxes_a = notin_a + axes_a
    N2_a = 1
    for axis in axes_a:
        N2_a *= as_[axis]
    newshape_a = as_[:shared] + (int(np.product([as_[ax] for ax in notin_a if ax >= shared])), N2_a)
    olda = [as_[axis] for axis in notin_a if axis >= shared]

    notin_b = [k for k in range(ndb) if k not in axes_b]
    newaxes_b = notin_b + axes_b
    N2_b = 1
    for axis in axes_b:
        N2_b *= bs[axis]
    newshape_b = as_[:shared] + (N2_b, int(np.product([bs[ax] for ax in notin_b if ax >= shared])))
    oldb = [bs[axis] for axis in notin_b if axis >= shared]

    at = a.transpose(newaxes_a).reshape(newshape_a)
    bt = b.transpose(newaxes_b).reshape(newshape_b)
    res = np.matmul(at, bt)
    final_shape = list(a_shape[:shared]) + olda + oldb
    return res.reshape(final_shape)
def vec_tdot(tensa, tensb, axes=[[-1], [1]]):
    """
    Tensor dot but just along the final axes by default. Totally a convenience function.

    :param tensa:
    :type tensa:
    :param tensb:
    :type tensb:
    :param axes:
    :type axes:
    :return:
    :rtype:
    """

    return vec_tensordot(tensa, tensb, axes=axes)


################################################
#
#       pts_normals
#

def pts_normals(pts1, pts2, pts3, normalize=True):
    """Provides the vector normal to the plane of the three points

    :param pts1:
    :type pts1: np.ndarray
    :param pts2:
    :type pts2: np.ndarray
    :param pts3:
    :type pts3: np.ndarray
    :param normalize:
    :type normalize:
    :return:
    :rtype: np.ndarray
    """
    # should I normalize these...?
    return vec_crosses(pts2-pts1, pts3-pts1, normalize=normalize)

################################################
#
#       pts_dihedrals
#

def pts_dihedrals(pts1, pts2, pts3, pts4):
    """Provides the dihedral angle between pts4 and the plane of the other three vectors

    :param pts1:
    :type pts1: np.ndarray
    :param pts2:
    :type pts2: np.ndarray
    :param pts3:
    :type pts3: np.ndarray
    :return:
    :rtype:
    """
    # # should I normalize these...?
    # normals = pts_normals(pts2, pts3, pts4, normalize=False)
    # off_plane_vecs = pts1 - pts4
    # return vec_angles(normals, off_plane_vecs)[0]

    # # less efficient but mirrors what I did in Mathematica (and works)
    b1 = pts2-pts1
    b2 = pts3-pts2
    b3 = pts4-pts3

    n1 = vec_crosses(b1, b2, normalize=True)
    n2 = vec_crosses(b2, b3, normalize=True)
    m1 = vec_crosses(n1, vec_normalize(b2))
    d1 = vec_dots(n1, n2)
    d2 = vec_dots(m1, n2)
    return np.arctan2(d2, d1)

################################################
#
#       mat_vec_muls

def mat_vec_muls(mats, vecs):
    """Pairwise multiplies mats and vecs

    :param mats:
    :type mats:
    :param vecs:
    :type vecs:
    :return:
    :rtype:
    """

    vecs_2 = np.reshape(vecs, vecs.shape + (1,))
    vecs_2 = np.matmul(mats, vecs_2)
    return np.reshape(vecs_2, vecs.shape)

################################################
#
#       one_pad_vecs
def one_pad_vecs(vecs):
    ones = np.ones((len(vecs), 1))
    vecs = np.concatenate((vecs, ones), axis=1)
    return vecs

################################################
#
#       affine_multiply

def affine_multiply(mats, vecs):
    """
    Multiplies affine mats and vecs

    :param mats:
    :type mats:
    :param vecs:
    :type vecs:
    :return:
    :rtype:
    """

    vec_shape = vecs.shape
    if vec_shape[-1] != 4:
        vecs = one_pad_vecs(vecs)
    res = mat_vec_muls(mats, vecs)
    if vec_shape[-1] != 4:
        res = res[:, :3]
    return res
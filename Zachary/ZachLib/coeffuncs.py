"""
coeffuncs defines the functions we use when computing coefficients for FD
"""
import numpy as np

try:
    from .lib import StirlingS1 as _StirlingS1
except ImportError:
    raise # we'll make this work later
    def _StirlingS1(n):
        pass

def StirlingS1(n):
    """simple recursive definition of the StirlingS1 function in Mathematica
    implemented at the C level mostly just for fun

    :param n:
    :type n:
    :return:
    :rtype:
    """

    return _StirlingS1(n)

try:
    from .lib import Binomial as _Binomial
except ImportError:
    def _Binomial(n):
        pass

def Binomial(n):
    """simple recursive Binomial coefficients up to r, computed all at once to vectorize later ops
    wastes space, justified by assuming a small-ish value for n

    :param n:
    :type n:
    :return:
    :rtype:
    """
    return _Binomial(n)

def GammaBinomial(s, n):
    """Generalized binomial gamma function

    :param s:
    :type s:
    :param n:
    :type n:
    :return:
    :rtype:
    """
    g = np.math.gamma
    g1 = g(s+1)
    g2 = np.array([g(m+1)*g(s-m+1) for m in range(n)])
    g3 = g1/g2
    return g3

def Factorial(n):
    """I was hoping to do this in some built in way with numpy...but I guess it's not possible?
    looks like by default things don't vectorize and just call math.factorial

    :param n:
    :type n:
    :return:
    :rtype:
    """

    base = np.arange(n, dtype=np.int64)
    base[0] = 1
    for i in range(1, n):
        base[i] = base[i]*base[i-1]
    return base

def EvenFiniteDifferenceWeights(m, s, n):
    """Finds the series coefficients for x^s*ln(x)^m centered at x=1. Uses the method:

             Table[
               Sum[
                ((-1)^(r - k))*Binomial[r, k]*
                    Binomial[s, r - j] StirlingS1[j, m] (m!/j!),
                {r, k, n},
                {j, 0, r}
                ],
               {k, 0, n}
               ]
             ]

        which is shown by J.M. here: https://chat.stackexchange.com/transcript/message/49528234#49528234

    :param m:
    :type m:
    :param s:
    :type s:
    :param n:
    :type n:
    :return:
    :rtype:
    """

    n = n+1 # in J.M.'s algorithm we go from 0 to n in Mathematica -- which means we have n+1 elements
    stirlings = StirlingS1(n)[:, m]
    bins = Binomial(n)
    sTest = s - int(s)
    if sTest == 0:
        bges = bins[ int(s) ]
    else:
        bges = GammaBinomial(s, n)
    bges = np.flip(bges)
    facs = Factorial(n)
    fcos = facs[m]/facs # factorial coefficient (m!/j!)

    coeffs = np.zeros(n)
    for k in range(n):
        # each of these bits here should go from
        # Binomial[s, r - j] * StirlingS1[j, m] *
        bs = bges
        ss = stirlings
        fs = fcos
        bits = np.zeros(n-k)
        for r in range(k+1, n+1):
            bits[r-k-1] = np.dot(bs[-r:], ss[:r]*fs[:r])

        # (-1)^(r - k))*Binomial[r, k]
        cs = (-1)**(np.arange(n-k)) * bins[k:n, k]
        # print(bits, file=sys.stderr)
        coeffs[k] = np.dot(cs, bits)

    return coeffs

try:
    from .lib import UnevenFiniteDifferenceWeights as _UnevenFiniteDifferenceWeights
except ImportError:
    def _UnevenFiniteDifferenceWeights(m, s, n):
        pass
def UnevenFiniteDifferenceWeights(m, z, x):
    return _UnevenFiniteDifferenceWeights(m, z, x)
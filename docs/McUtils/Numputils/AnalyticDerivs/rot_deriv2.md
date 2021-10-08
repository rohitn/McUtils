# <a id="McUtils.Numputils.AnalyticDerivs.rot_deriv2">rot_deriv2</a>

```python
rot_deriv2(angle, axis, dAngle1, dAxis1, dAngle2, dAxis2, d2Angle, d2Axis): 
```
Gives a rotation matrix second derivative w/r/t some unspecified coordinate
    (you have to supply the chain rule terms)
- `angle`: `float`
    >angle for rotation
- `axis`: `np.ndarray`
    >axis for rotation
- `dAngle`: `float`
    >chain rule angle deriv.
- `dAxis`: `np.ndarray`
    >chain rule axis deriv.
- `:returns`: `np.ndarray`
    >derivatives of the rotation matrices with respect to both the angle and the axis 

### Examples: 



___

[Edit Examples](https://github.com/McCoyGroup/McUtils/edit/edit/ci/examples/ci/docs/McUtils/Numputils/AnalyticDerivs/rot_deriv2.md) or 
[Create New Examples](https://github.com/McCoyGroup/McUtils/new/edit/?filename=ci/examples/ci/docs/McUtils/Numputils/AnalyticDerivs/rot_deriv2.md) <br/>
[Edit Template](https://github.com/McCoyGroup/McUtils/edit/edit/ci/docs/ci/docs/McUtils/Numputils/AnalyticDerivs/rot_deriv2.md) or 
[Create New Template](https://github.com/McCoyGroup/McUtils/new/edit/?filename=ci/docs/templates/ci/docs/McUtils/Numputils/AnalyticDerivs/rot_deriv2.md) <br/>
[Edit Docstrings](https://github.com/McCoyGroup/McUtils/edit/edit/McUtils/Numputils/AnalyticDerivs.py?message=Update%20Docs)
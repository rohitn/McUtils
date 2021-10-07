## <a id="McUtils.Zachary.Mesh.Mesh">Mesh</a>
A general Mesh class representing data points in n-dimensions
in either a structured, unstructured, or semi-structured manner.
Exists mostly to provides a unified interface to difference FD and Surface methods.

### Properties and Methods
```python
MeshError: type
MeshType: EnumMeta
get_npoints: method
get_gridpoints: method
get_mesh_subgrids: method
get_mesh_spacings: method
get_mesh_type: method
RegularMesh: method
```
<a id="McUtils.Zachary.Mesh.Mesh.__new__" class="docs-object-method">&nbsp;</a>
```python
__new__(cls, data, mesh_type=None, allow_indeterminate=None): 
```

- `griddata`: `np.ndarray`
    >the raw grid-point data the mesh uses
- `mesh_type`: `None | str`
    >the type of mesh we have
- `opts`: `Any`
    >No description...

<a id="McUtils.Zachary.Mesh.Mesh.__init__" class="docs-object-method">&nbsp;</a>
```python
__init__(self, *args, **kwargs): 
```

<a id="McUtils.Zachary.Mesh.Mesh.__array_finalize__" class="docs-object-method">&nbsp;</a>
```python
__array_finalize__(self, mesh): 
```

<a id="McUtils.Zachary.Mesh.Mesh.mesh_spacings" class="docs-object-method">&nbsp;</a>
```python
@property
mesh_spacings(self): 
```

<a id="McUtils.Zachary.Mesh.Mesh.subgrids" class="docs-object-method">&nbsp;</a>
```python
@property
subgrids(self): 
```

<a id="McUtils.Zachary.Mesh.Mesh.dimension" class="docs-object-method">&nbsp;</a>
```python
@property
dimension(self): 
```
Returns the dimension of the grid (not necessarily ndim)
- `:returns`: `int`
    >No description...

<a id="McUtils.Zachary.Mesh.Mesh.npoints" class="docs-object-method">&nbsp;</a>
```python
@property
npoints(self): 
```
Returns the number of gridpoints in the mesh
- `:returns`: `int`
    >No description...

<a id="McUtils.Zachary.Mesh.Mesh.gridpoints" class="docs-object-method">&nbsp;</a>
```python
@property
gridpoints(self): 
```
Returns the flattened set of gridpoints for a structured tensor grid and otherwise just returns the gridpoints
- `:returns`: `_`
    >No description...

<a id="McUtils.Zachary.Mesh.Mesh.get_slice_iter" class="docs-object-method">&nbsp;</a>
```python
get_slice_iter(self, axis=-1): 
```
Returns an iterator over the slices of the mesh along the specified axis
- `axis`: `Any`
    >No description...
- `:returns`: `_`
    >No description...

### Examples


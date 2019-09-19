
import numpy as np

__all__ = [
    "StructuredType",
    "StructuredTypeArray",
    "DisappearingType"
]

class StructuredType:
    """
    Represents a structured type with a defined calculus to simplify the construction of combined types when writing
    parsers that take multi-typed data
    """
    def __init__(self,
                 base_type,
                 shape = None,
                 is_alternative = False,
                 is_optional = False,
                 default_value = None
                 ):
        if shape is None and isinstance(base_type, tuple) and len(base_type) == 2 and (
                isinstance(base_type[1], int) or isinstance(base_type[1], tuple)
        ): # to make it possible to initialize the type like (str, 3) or (int, (3,))
            base_type, shape = base_type
        # if isinstance(base_type, (list, tuple)):
        #     base_type = tuple(b for b in base_type if not (b is DisappearingType or isinstance(b, DisappearingTypeClass)))
        #     base_type, shape = self._condense_types(base_type, shape)
        self.dtype = base_type
        self.shape = shape

        # there's some question as to how we should declare alternative types?
        # currently we have a flag in the type but we could also make 3 subtypes of StructuredType:
        #   AlternativeTypes(...), PrimitiveType(...), CompoundType(...) ?

        self.is_alternative = is_alternative
        self.is_optional = is_optional
        self.default = default_value # for optional types

    @property
    def is_simple(self):
        return (
                self.dtype is None or (isinstance(self.dtype, type) and not self.is_optional and not self.is_alternative)
        )

    def __add__(self, other):
        if other is DisappearingType or isinstance(other, type(DisappearingType)):
            return self
        elif self is DisappearingType or isinstance(self, type(DisappearingType)):
            return other
        else:
            if not isinstance(other, StructuredType):
                other = StructuredType(other)

            # we define a very simple calculus on the structured types
            #   if both are the same we simply futz with the shapes if possible
            #   if they're different we construct a compound type from the two structured types
            # _unless_ we have an alternative type in which case...?

            if self.shape is None or other.shape is None:
                shape_mismatches = None
            else:
                shape_mismatches = np.array([ (x is None) or (y is None) or int(x != y) for x,y in zip(self.shape, other.shape)])
            if (
                    self.is_simple and
                    self.dtype == other.dtype and (
                            shape_mismatches is None or (
                            len(self.shape) == len(other.shape) and np.sum(shape_mismatches) <= 1
                            )
                    )
                ):

                if self.shape is None and other.shape is None:
                    new_shape = (2,)
                elif self.shape is None:
                    new_shape = other.shape[:-1] + (other.shape[-1]+1, ) # this isn't quite right but will work for now
                elif other.shape is None:
                    new_shape = self.shape[:-1] + (self.shape[-1]+1, ) # this isn't quite right but will work for now
                else:
                    mismatch_pos = np.argwhere(shape_mismatches == 1)
                    if len(mismatch_pos) == 0:
                        mismatch_pos = -1
                    else:
                        mismatch_pos = mismatch_pos[-1]
                    new_shape = list(self.shape)
                    me = self.shape[mismatch_pos]
                    yu = other.shape[mismatch_pos]
                    if me is None or yu is None:
                        new_shape[mismatch_pos] = None
                    else:
                        new_shape[mismatch_pos] = me + yu

                import copy
                new = copy.copy(self)
                new.shape = tuple(new_shape)
                return new
            else:
                return type(self)((self, other))

    def repeat(self, n = None, m = None):
        """Returns a new version of the type, but with the appropriate shape for being repeated n-to-m times

        :param n:
        :type n:
        :param m:
        :type m:
        :return:
        :rtype:
        """

        import copy
        new = copy.copy(self)
        if new.shape is None:
            new.shape = (None,) if (n is None or m is None or n !=m ) else (n,)
        elif n is not None and m is not None and n == m:
            new.shape = (n,) + new.shape
        else:
            new.shape = (None,) + new.shape # we won't handle things like between 10 and 20 elements for now
        return new

    def extend_shape(self, base_shape):
        """Extends the shape of the type such that base_shape precedes the existing shape

        :param base_shape:
        :type base_shape:
        :return:
        :rtype:
        """
        shape = self.shape
        if self.shape is None:
            self.shape = base_shape
        else:
            self.shape = base_shape + shape

    def _condense_types(self, base_types, shape):
        # what do I do about this existing shape...?

        raw_types = [ b.dtype for b in base_types ]
        shapes = [ b.shape for b in base_types ]

        if shape is None and (
                all(r is raw_types[0] for r in raw_types) and
                (
                        all( s is None for s in shapes ) or
                        all( isinstance(s, tuple) and s == shapes[0] for s in shapes )
                )
        ):
            # means we can actually condense them but I might want to be a bit smarter with how I handle the tuple shape check...

            base_types = base_types[0] # no differences in type
            if shapes[0] is None:
                shape = (len(shapes),)
            else:
                shape += (len(shapes),)

        return base_types, shape


    def __repr__(self):
        return "{}({}, shape={})".format(
            type(self).__name__,
            self.dtype,
            self.shape
        )

class DisappearingTypeClass(StructuredType):
    """
    A special type that is entirely ignored in the structured type algebra
    """
    def __init__(self):
        self.is_disappearing = True
        super().__init__(None)
DisappearingType = DisappearingTypeClass() # redefinition but it should be a singleton anyway

class StructuredTypeArray:
    """
    Represents an array of objects defined by the StructuredType spec provided
    mostly useful as it dispatches to NumPy where things are simple enough to do so
    """

    # at some point this should make use of the more complex structured dtypes that NumPy provides...
    def __init__(self, stype, num_elements = 50):
        """
        :param stype:
        :type stype: StructuredType
        :param num_elements: number of default elements in dynamically sized arrays
        :type num_elements: int
        """
        self._is_simple = stype.is_simple
        self._extend_along = None
        self._dtype = None
        self.stype = stype

        self._filled_to = 0

        self._default_num_elements = num_elements
        self._array = None
        self._array = self.empty_array() # empty_array tries to use shape if possible

    @property
    def is_simple(self):
        """Just returns wheter the core datatype is simple

        :return:
        :rtype:
        """
        return self._is_simple
    @property
    def extension_axis(self):
        """Determines which axis to extend when adding more memory to the array
        :return:
        :rtype:
        """
        if self._extend_along is None:
            if self.stype.shape is None:
                self._extend_along = 0
            else:
                shape_nones = np.array([x is None for x in self.stype.shape], dtype=bool)
                if len(shape_nones) == 0:
                    self._extend_along = 0
                else:
                    self._extend_along = np.arange(len(shape_nones))
                    hmm = self._extend_along[shape_nones]
                    if len(hmm) == 0:
                        hmm = self._extend_along
                    self._extend_along = hmm[0]
        return self._extend_along
    @extension_axis.setter
    def extension_axis(self, ax):
        self._extend_along = ax
    @property
    def shape(self):
        if self._array is None:
            return None
        if self.is_simple:
            if isinstance(self._array, np.ndarray):
                self._shape = list(self._array.shape)
                self._shape[self.extension_axis] = self._filled_to # this will mess up on things like (3,)...
                self._shape = tuple(self._shape)
            else:
                self._shape = None
        else:
            self._shape = [s.shape for s in self._array]
        return self._shape
    @shape.setter
    def shape(self, s):
        self._shape = s
    @property
    def block_size(self):
        if self.is_simple:
            s = list(self.shape)
            s[self.extension_axis] = 1 # this will mess up on things like (3,)...
            self._block_size = np.product(s)
        else:
            self._block_size = sum([s.block_size for s in self._array])
        return self._block_size

    def _get_complex_dtype(self):
        shape = self.stype.shape
        # Means we gotta do this recursively
        # The shape should be fed back down to the object's children at this point
        dt = [
            StructuredType(s) if not isinstance(s, StructuredType) else s for s in self.stype.dtype
        ]
        if shape is not None:
            # we have to take our shape and feed it back down to our children
            # the mechanism for this will have to be to take each type in dt and stick our shape onto the
            # front of the dtype's shape
            import copy
            dt = [ copy.copy(d) for d in dt ]
            for d in dt:
                d.extend_shape(shape)
        return tuple(dt)
    @property
    def dtype(self):
        if self._dtype is None:
            if self.is_simple:
                self._dtype = self.stype.dtype
            else:
                self._dtype = self._get_complex_dtype()
        return self._dtype
    @property
    def array(self):
        if self.is_simple:
            return self._array[:self._filled_to]
        else:
            return self._array

    @property
    def has_indeterminate_shape(self):
        if self.is_simple:
            indet = self._filled_to == 0
            if indet and self.stype.shape is not None:
                count_None = 0
                for c in self.stype.shape:
                    if c is None:
                        count_None += 1
                        if count_None > 1:
                            break
                indet = count_None > 1
            return indet # eh we'll call this enough for now
        else:
            return any( a.has_indeterminate_shape for a in self._array )

    @property
    def filled_to(self):
        if self._is_simple:
            return self._filled_to
        else:
            return [s.filled_to for s in self._array]
    def __len__(self):
        return self._filled_to

    def empty_array(self, num_elements = None):
        """Creates empty arrays with (potentially) default elements

        The shape handling rules operate like this:
            if shape is None, we assume we'll initialize this as an array with a single element to be filled out
            if shape is (None,) or (n,) we'll initialize this as an array with multiple elments to be filled out
            otherwise we'll just take the specified shape

        :param num_elements:
        :type num_elements:
        :return:
        :rtype:
        """

        stype = self.stype
        dt = self.dtype
        shape = stype.shape if self.shape is None else self.shape
        if num_elements is None:
            num_elements = self._default_num_elements
        if stype.is_simple:
            if shape is None:
                # means we expect to have single object, not a vector of them
                if stype.default is None:
                    arr = np.empty((1, ), dtype=dt)
                else:
                    arr = np.full((1, ), stype.default, dtype=dt)
            else:
                if any(x is None for x in shape):
                    # means we have an array of indeterminate size in that dimension
                    shape = tuple(num_elements if x is None else x for x in shape)
                # might want to add a check to see if dt is valid fo np.array
                if stype.default is None:
                    arr = np.empty(shape, dtype=dt)
                else:
                    arr = np.full(shape, stype.default, dtype=dt)
            return arr
        else:
            return tuple( StructuredTypeArray(s) for s in dt )

    def extend_array(self):
        array = self._array
        if isinstance(array, np.ndarray):
            ax = self.extension_axis
            empty = self.empty_array() # should effectively double array size?
            self._array = np.concatenate(
                (
                    array,
                    empty
                ),
                axis=ax
            )
        else:
            for arr in array:
                arr.extend_array()

    def __setitem__(self, key, value):
        """Recursively sets parts of an array if not simple, otherwise just delegates to NumPy

        :param key:
        :type key:
        :param value:
        :type value:
        :return:
        :rtype:
        """
        if self.is_simple:
            # should we do some type coercion if we're fed a string?

            if self._array.shape[0] == key:
                self.extend_array()

            self._array[key] = value
            if isinstance(key, int) and key == self._filled_to:
                self._filled_to += 1
        else:
            if isinstance(key, (int, str)):
                key = [ key ] * len(self._array)
            if len(value) > len(self._array):
                # means we need to reshape our value arrays since it came from a groups call but groups just returns flat values,
                # not the actual grouping we might want
                shapes = self.shape
                # since we're assigning to a slice I guess this means we're assigning the shape of element 2?
                # so we can just split it by the number of elements we need from shape[1:] and then use np.reshape on that
                # ah but we have pre-populated a number of the np.array rows so really we need to go from shape[2:]
                old_value = value
                value = [None]*len(shapes)
                for i, s in enumerate(shapes):
                    sub_shape = s[1:]
                    s_num = np.product(sub_shape) # get the number of elements
                    if s_num == 1:
                        value[i] = old_value[0]
                        old_value = old_value[1:]
                    else:
                        v = old_value[:s_num]
                        old_value = old_value[s_num:]
                        value[i] = np.reshape(np.array(v, dtype=object), sub_shape)

            for a, k, v in zip(self._array, key, value):
                a[k] = v
    def __getitem__(self, item):
        """If simple, delegates to NumPy, otherwise tries to recursively get parts...?
        Unclear how slicing is best handled here.

        :param item:
        :type item:
        :return:
        :rtype:
        """
        if self.is_simple:
            return self._array[item]
        else:
            if isinstance(item, tuple):
                compound_index = True
                first_thingy = item[0]
            else:
                compound_index = False
                first_thingy = item
            if isinstance(first_thingy, slice) and compound_index:
                bits = self._array[first_thingy]
                return [ b[item[1:]] for b in bits ]
            elif isinstance(first_thingy, slice):
                raise NotImplemented("Not sure how I want to slice StructuredType objects yet")
            elif compound_index:
                bit = self._array[first_thingy]
                return bit[item[1:]]
            else:
                bit = self._array[first_thingy]
                return bit

    def add_axis(self, which = 0, num_elements = None):

        if self.is_simple:
            if self.has_indeterminate_shape:
                import copy
                self.stype = copy.copy(self.stype)

                if self.stype.shape is None:
                    self.stype.shape = (None,)
                else:
                    self.stype.shape += (None,)
                    self._array = None
                    self._array = self.empty_array(50 if num_elements is None else num_elements)

            elif self.stype.shape is not None:
                # if we've already got a flexible shape I think we actually dont need to add an axis...
                # otherwise we add an axis where specified, but in practice which will never not be 0

                shape = self._array.shape # just broadcast the numpy array
                if num_elements is None:
                    num_elements = 50 # hard coded for now but could be changed

                new_shape_1 = shape[:which] + (1,) + shape[which:] # we gotta broadcast to the 1 first for some corner cases
                self._array = np.broadcast_to(self._array, new_shape_1)
                new_shape_2 = shape[:which] + (num_elements,) + shape[which:] # now we can fully broadcast
                self._array = np.broadcast_to(self._array, new_shape_2).copy()

                import copy
                self.stype = copy.copy(self.stype)
                if self.stype.shape is None:
                    self.stype.shape = (None,)
                else:
                    self.stype.shape = self.stype.shape[:which] + (None,) + self.stype.shape[which:]

                if self._filled_to > 0:
                    self._filled_to = 1 # we have one copy of our data already
                else:
                    self._filled_to = 0

        else:
            # we'll recursively add axes to the subarrays I think...
            # this might not be entirely in keeping with how a np.ndarray works but I think is acceptable
            for a in self._array:
                a.add_axis(which, num_elements)

            # raise NotImplementedError("Not sure yet how I want to broadcast compound type arrays to different shapes...")

    def can_cast(self, val):
        """Determines whether val can probably be cast to the right return type and shape without further processing or if that's definitely not possible

        :param val:
        :type val:
        :return:
        :rtype:
        """

        castable = self.is_simple
        if castable:
            val = np.asarray(val) # make sure we can use .shape
            if not isinstance(val, np.ndarray) or val.shape == ():
                # can't cast to some shape so we gotta have no shape and be a primitive type
                castable = self.shape is None
            elif len(self.shape) == 1:
                # gotta have a vector of values but we can fill without filling the entire thing I'd say
                castable = len(val.shape) == 1
            else:
                axis, remainder, shape = self._get_casting_shape(val)
                castable = remainder == int(remainder)

        return castable

    def append(self, val):
        """Puts val in the first empty slot in the array

        :param val:
        :type val:
        :return:
        :rtype:
        """

        self[self.filled_to] = val
        # self._filled_to+=1 # handled automatically by a small bit of cleverness in the filling code

    def _get_casting_shape(self, val):
        axis = self.extension_axis
        vs = val.shape
        ss = self.shape
        vs_a = vs[:axis] + vs[axis+1:]
        ss_a = ss[:axis] + ss[axis+1:]
        if vs_a != ss_a:
            total_stuffs = np.product(vs)
            my_stuffs = np.product(ss_a)
            remaining_stuff = total_stuffs/my_stuffs
            new_shape = ss[:axis] + (int(remaining_stuff),) + ss[axis+1:]
        else:
            remaining_stuff = 0
            new_shape = vs
        return axis, remaining_stuff, new_shape

    def extend(self, val, single = True):
        """Adds the sequence val to the array

        :param val:
        :type val:
        :param single: a flag that indicates whether val can be treated as a single object or if it needs to be reshapen when handling in non-simple case
        :type single: bool
        :return:
        :rtype:
        """

        if self.is_simple:
            if isinstance(val, StructuredTypeArray):
                val = val.array

            # we have a minor issue here, where we might not actually have any data in our array and in that case we
            # won't know what 'extend' means
            # in that case I think we would be safe enough delegating to 'fill'
            if self.has_indeterminate_shape and len(self.shape) == len(val.shape if isinstance(val, np.ndarray) else val):
                return self.fill(val)

            # now check for shape mismatches so they may be corrected _before_ the insertion
            axis, remainder, new_shape = self._get_casting_shape(val)
            if remainder != int(remainder):
                raise StructuredTypeArrayException("{}.{}: object with shape '{}' can't be used to extend array of shape '{}' along axis '{}'".format(
                    type(self).__name__,
                    'extend',
                    val.shape,
                    self.shape,
                    axis
                ))
            val = val.reshape(new_shape)

            self._array = np.concatenate(
                (
                    self._array[:self._filled_to],
                    val
                ),
                axis = axis
            )
            self._filled_to = self._array.shape[axis]
        else:
            # hmm... how to handle parse_all string array cases here?
            # need some kind of flag that indicates that we val is misshapen?
            if not single: # single alone might tell us we have an issue...
                if len(val[0]) == len(self._array):
                    # just need to transpose the groups, basically,
                    gg = val.T
                else:
                    blocks = [b.block_size for b in self._array]
                    # we'll assume val is an np.ndarray for now since that's the most common case
                    # but this might not work in general...
                    gg = [ None ] * len(blocks)
                    sliced = 0
                    for i, b in enumerate(blocks):
                        if b == 1:
                            gg[i] = val[:, sliced]
                        else:
                            gg[i] = val[:, sliced:sliced+b]
                        sliced += b
                val = gg
            for a, v in zip(self._array, val):
                a.extend(v)

    def fill(self, array):
        """Sets the result array to be the passed array

        :param array:
        :type array: str | np.ndarray
        :return:
        :rtype:
        """
        if isinstance(array, str):
            array = self.cast_to_array(array)
        elif isinstance(array, StructuredTypeArray):
            array = array.array

        if self._is_simple:
            # not sure why the array _wouldn't_ be an np.ndarray but there's a lot going on and I'm tired and don't
            # want to figure it out
            if isinstance(array, np.ndarray):
                self._array = array.astype(self.dtype)
                # now we can fux with our shapes?
                # or maybe we just leave that be...?
            else:
                self._array = array
            self._filled_to = len(self._array)
        else:
            for arr, data in zip(self._array, array):
                arr.fill(data)

    def cast_to_array(self, txt):
        """Casts a string of things with a given data type to an array of that type and does some optional
        shape coercion

        :param txt:
        :type txt: str | iterable[str]
        :return:
        :rtype:
        """
        if self.is_simple:
            if len(txt.strip()) == 0:
                arr = np.array([], dtype=self.stype)
            else:
                try:
                    # we'll try the base conversion first just assuming we got a number or whatever
                    # and it managed to filter through the code to here
                    arr = np.array([txt], dtype=self.stype)
                except TypeError:
                    import io
                    arr = np.loadtxt(io.StringIO(txt), dtype=self.stype)
                    shape = np.array(self.shape)
                    axis = self.extension_axis
                    if shape is not None and shape[axis] > 0: # make sure arr needs to be reshaped...
                        arr = arr.flatten()
                        num_els = len(arr)
                        # the number of elements that the length of the parsed out array must be divisible by
                        num_not_along_axis = np.product(shape) / shape[axis]
                        if num_els % num_not_along_axis == 0:
                            # means we can cleanly reshape it once we know the target shape
                            shape[self.extension_axis] = num_els / num_not_along_axis
                            arr = arr.reshape(shape)
                        # should we raise an error if not?

        else: #we'll assume we got some block of strings since there's no reason to put a parser here...
            arr = [a.cast_to_array(t) for a, t in zip(self._array, txt)]

        return arr

    def __repr__(self):
        return "{}(shape={}, dtype={})".format(
            type(self).__name__,
            self.shape,
            self.dtype
        )


class StructuredTypeArrayException(Exception):
    pass
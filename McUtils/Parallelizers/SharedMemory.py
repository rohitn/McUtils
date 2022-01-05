"""
Provides classes for working with `multiprocessing.SharedMemory`
in a slightly more convenient way
"""

import abc, os, numpy as np, typing
from dataclasses import dataclass

from ..Scaffolding import BaseObjectManager, NDarrayMarshaller

__all__ = [
    "SharedObjectManager",
    "SharedMemoryDict",
    "SharedMemoryList"
]

class SharedMemoryInterface(typing.Protocol):

    @abc.abstractmethod
    def __init__(self, name=None, create=False, size=None):
        raise NotImplementedError("interface class")

    buf: bytearray

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError("interface class")

    @abc.abstractmethod
    def unlink(self):
        raise NotImplementedError("interface class")

class SharedMemoryNDarray:
    """
    Provides a very simple tracker for shared NumPy arrays
    """

    def __init__(self, shape, dtype, buf, autoclose=True, parallelizer=None):
        """
        :param shape:
        :type shape: tuple[int]
        :param dtype:
        :type dtype: np.dtype
        :param buf:
        :type buf: SharedMemoryInterface
        :param parallelizer:
        :type parallelizer: Parallelizer
        """
        self.dtype = dtype
        self.shape = shape
        self.buf = buf
        self.autoclose = autoclose
        self.array = np.ndarray(self.shape, dtype=self.dtype, buffer=self.buf.buf)
        self.parallelizer = parallelizer

    def __getstate__(self):
        return {
            'dtype': self.dtype,
            'shape': self.shape,
            'buf': self.buf,
            'autoclose': self.autoclose,
            'parallelizer': self.parallelizer
        }

    def __setstate__(self, state):
        self.dtype = state['dtype']
        self.shape = state['shape']
        self.buf = state['buf']
        self.autoclose = state['autoclose']
        self.parallelizer = state['parallelizer']
        self.array = np.ndarray(self.shape, dtype=self.dtype, buffer=self.buf.buf)

    @classmethod
    def from_array(cls, arr, buf,
                   autoclose=None,
                   parallelizer=None
                   ):
        """
        Initializes by pulling metainfo from an array

        :param arr:
        :type arr: np.ndarray
        :param buf:
        :type buf: SharedMemoryInterface
        :return:
        :rtype:
        """
        opts = {}
        if autoclose is not None:
            opts['autoclose'] = autoclose
        if parallelizer is not None:
            opts['parallelizer'] = parallelizer
        new = cls(arr.shape, arr.dtype, buf, **opts)
        new[:] = arr
        return new

    def __setitem__(self, key, value):
        self.array[key] = value

    def __getitem__(self, item):
        return self.array[item]

    def close(self):
        self.buf.close()

    def unlink(self):
        self.buf.unlink()

    def __del__(self):
        if self.autoclose:
            self.close()
            if self.parallelizer is not None and self.parallelizer.on_main:
                self.unlink()

    def __repr__(self):
        return "{}({}, dtype={})".format(
            type(self).__name__,
            self.shape,
            self.dtype
        )

class SharedArrayAllocator:
    """
    Provides the base API to allocate/deallocate
    NumPy arrays
    """

    def __init__(self, parallelizer=None, mem_manager=None):
        if mem_manager is None:
            try:
                from multiprocessing import shared_memory
                self.api = shared_memory
            except ImportError:
                self.api = None
                raise NotImplementedError(
                    "{}: either `multiprocessing` needs the `shared_memory` submodule or `mem_manager` must be provided".format(
                        type(self).__name__
                    )
                )
        self.parallelizer = parallelizer
        self.mem_manager = mem_manager

    def __getstate__(self):
        base = self.__dict__
        base['api'] = None
        return base

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.mem_manager is None:
            try:
                from multiprocessing import shared_memory
                self.api = shared_memory
            except ImportError:
                self.api = None
                raise NotImplementedError(
                    "{}: either `multiprocessing` needs the `shared_memory` submodule or `mem_manager` must be provided".format(
                        type(self).__name__
                    )
                )


    def create_shared_array(self, data, name=None):
        """
        Makes a SharedNDarray object for an existing data chunk

        :param data:
        :type data: np.ndarray
        :return:
        :rtype: SharedMemoryNDarray
        """

        if self.mem_manager is not None:
            shm = self.mem_manager.SharedMemory
        else:
            shm = self.api.SharedMemory
        buf = shm(name, create=True, size=data.nbytes)
        return SharedMemoryNDarray.from_array(data, buf, parallelizer=self.parallelizer)

    def delete_shared_array(self, shared_array):
        """
        Closes a buffer for a numpy array

        :param shared_array:
        :type shared_array: SharedMemoryNDarray
        :return:
        :rtype:
        """
        shared_array.close()

    def update_shared_array(self, shared_array, data):
        """
        Updates a buffer for a numpy array

        :param shared_array:
        :type shared_array: SharedMemoryNDarray
        :return:
        :rtype:
        """
        try:
            shared_array.buf[:] = data
        except ValueError:
            shared_array = self.create_shared_array(data)
        return shared_array

class SharedMemoryPrimitive:
    """
    Provides basic support for storing shared memory arrays
    """
    def __init__(self, sync_buffer, allocator=None, marshaller=None, parallelizer=None):

        self.buffers = sync_buffer

        self.allocator = SharedArrayAllocator() if allocator is None else allocator

        if marshaller is None:
            marshaller = NDarrayMarshaller()
        self.marshaller = marshaller
        # self.buffers = {} if buffers is None else buffers
        self.parallelizer = parallelizer

    def _save_to_buffer(self, tree, name, data):
        """
        Saves `data` to a series of `SharedNDarrays` by
        recursing into structures to save them as buffers
        in a dict-like structure

        :param tree:
        :type tree:
        :param name:
        :type name:
        :param data:
        :type data:
        :return:
        :rtype:
        """
        arr = self.marshaller.convert(data)
        del data # just to help minimize bugs
        if isinstance(arr, np.ndarray):
            if hasattr(tree, 'keys'):
                # add the array as an attr
                if name in tree and isinstance(tree[name], SharedMemoryNDarray):
                    tree[name] = self.allocator.update_shared_array(tree[name], arr)
                else:
                    tree[name] = self.allocator.create_shared_array(arr)
            elif isinstance(name, (int, np.integer)):
                # add the array as a list element
                if len(tree) < name:
                    if tree[name] is None:
                        tree[name] = self.allocator.create_shared_array(arr)
                    else:
                        tree[name] = self.allocator.update_shared_array(tree[name], arr)
                else:
                    # expand the tree to just the necessary space
                    padding = len(tree) - name - 1
                    tree = tree + [None] * padding
                    tree[name] = self.allocator.create_shared_array(arr)
            else:
                raise ValueError("cannot save {} into {}".format(arr, tree))
        else:
            # walk an expression tree, updating buffers as needed
            if name in tree:
                subtree = tree[name]
            elif hasattr(arr, 'keys'):
                subtree = {}
            else:
                subtree = []

            if hasattr(arr, 'keys'):
                for k,v in arr.items():
                    self._save_to_buffer(subtree, k, v)
            else:
                for i,v in enumerate(arr):
                    self._save_to_buffer(subtree, i, v)

    def __setitem__(self, key, value):
        self._save_to_buffer(self.buffers, key, value)

    def _handle_delete(self, arr):
        """
        Loads recursively, maintaining
        structure where possible

        :param arr:
        :type arr:
        :return:
        :rtype:
        """
        if arr is None:
            pass
        elif isinstance(arr, SharedMemoryNDarray):
            self.allocator.delete_shared_array(arr)
        elif isinstance(arr, dict):
            for v in arr.values():
                self._handle_delete(v)
        else:  # build a list of loaded values
            for v in arr:
                self._handle_delete(v)

    def _del_buffer(self, tree, name):
        """
        Reloads shared data from the buffers, trying
        to maintain fidelity where possible

        :param tree:
        :type tree:
        :param name:
        :type name:
        :return:
        :rtype:
        """
        self._handle_delete(tree[name])
        del tree[name]

    def __delitem__(self, key):
        return self._del_buffer(self.buffers, key)

    def _handle_load(self, arr):
        """
        Loads recursively, maintaining
        structure where possible

        :param arr:
        :type arr:
        :return:
        :rtype:
        """
        if arr is None:
            data = None
        elif isinstance(arr, SharedMemoryNDarray):
            data = arr.array.copy()
            self.allocator.delete_shared_array(arr)
        elif isinstance(arr, np.ndarray): # protection but not sure how we'd get here...
            data = arr
        elif isinstance(arr, dict):
            data = {
                k:self._handle_load(v) for k,v in arr.items()
            }
        else: # build a list of loaded values
            data = [self._handle_load(v) for v in arr]

        return data

    def _load_from_buffer(self, tree, name):
        """
        Reloads shared data from the buffers, trying
        to maintain fidelity where possible

        :param tree:
        :type tree:
        :param name:
        :type name:
        :return:
        :rtype:
        """
        data = self._handle_load(tree[name])
        # self._del_buffer(tree, name)
        return data

    def load_item(self, item):
        return self._load_from_buffer(self.buffers, item)

    def __getitem__(self, item):
        return self.buffers[item]
        #
        # self.buffers[key] = self.marshaller.convert(value)

    def __repr__(self):
        return "{}({})".format(type(self).__name__, self.buffers)

class SharedMemoryList(SharedMemoryPrimitive):
    """
        Implements a shared dict that uses
        a managed dict to synchronize array metainfo
        across processes
        """

    def __init__(self, *seq, sync_list=None, marshaller=None, allocator=None, parallelizer=None):
        """
        :param marshaller:
        :type marshaller:
        :param sync_dict:
        :type sync_dict:
        :param allocator:
        :type allocator:
        :param parallelizer:
        :type parallelizer:
        """

        if sync_list is None:
            from multiprocessing import Manager
            sync_list = Manager().list()

        super().__init__(sync_list, marshaller, allocator, parallelizer)

        if len(seq) == 1:
            self.extend(seq[0])
        elif len(seq) > 0:
            raise ValueError("only one positional argument allowed") # standardize this

    def __iter__(self):
        return iter(self.buffers)
    def __len__(self):
        return len(self.buffers)
    def load(self):
        return [self._load_from_buffer(self.buffers, i) for i in range(len(self))]

    def pop(self, k=0):
        val = self.buffers.pop(k)
        return self._handle_load(val)
    def insert(self, k, v):
        self.buffers.insert(k, None)
        self[k] = v
    def append(self, v):
        self.buffers.append(None)
        self.buffers[len(self.buffers)] = v
    def extend(self, v):
        base_len = len(self.buffers)
        self.buffers.extend([None]*len(v))
        for i,a in enumerate(v):
            self.buffers[base_len+i] = v

class SharedMemoryDict(SharedMemoryPrimitive):
    """
    Implements a shared dict that uses
    a managed dict to synchronize array metainfo
    across processes
    """

    def __init__(self, *seq, sync_dict=None, marshaller=None, allocator=None, parallelizer=None):
        """
        :param marshaller:
        :type marshaller:
        :param sync_dict:
        :type sync_dict:
        :param allocator:
        :type allocator:
        :param parallelizer:
        :type parallelizer:
        """

        if sync_dict is None:
            from multiprocessing import Manager
            sync_dict = Manager().dict()

        super().__init__(sync_dict, marshaller, allocator, parallelizer)

        if len(seq) == 1:
            self.update(seq[0])
        elif len(seq) > 0:
            raise ValueError("only one positional argument allowed") # standardize this

    def __iter__(self):
        return iter(self.buffers)
    def __len__(self):
        return len(self.buffers)

    def keys(self):
        return self.buffers.keys()
    def values(self):
        return self.buffers.values()
    def items(self):
        return self.buffers.items()
    def load(self):
        return {k:self._load_from_buffer(self.buffers, k) for k in self.keys()}

    def update(self, v):
        v = dict(v)
        self.buffers.update({k:None for k in v.keys()})
        for k,a in v.items():
            self[k] = a

class SharedAttribute:
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager

@dataclass
class PrimitiveTypeHolder:
    val: object

class SharedObjectManager(BaseObjectManager):
    """
    Provides a high-level interface to create a manager
    that supports shared memory objects through the multiprocessing
    interface
    Only supports data that can be marshalled into a NumPy array.
    """

    def __init__(self, obj, base_dict=None, parallelizer=None):
        """
        :param mem_manager: a memory manager like `multiprocessing.SharedMemoryManager`
        :type mem_manager:
        :param obj: the object whose attributes should be given by shared memory objects
        :type obj:
        :param base_dict: the dict that stores the shared arrays (can also be shared)
        :type base_dict: SharedMemoryDict
        """

        if self.is_primitive(obj):
            obj = PrimitiveTypeHolder(obj)
        super().__init__(obj)

        self.base_dict = SharedMemoryDict() if base_dict is None else base_dict
        self.parallelizer = parallelizer

    primitive_types = (
        set,
        list,
        tuple,
        dict,
        np.ndarray
    )
    @classmethod
    def is_primitive(cls, val):
        return isinstance(val, cls.primitive_types)

    def save_attr(self, attr):
        val = getattr(self.obj, attr)
        if not isinstance(val, SharedAttribute):
            self.base_dict[attr] = val
            setattr(self.obj, attr, SharedAttribute(self, attr))
            val = getattr(self.obj, attr)
        return val

    def del_attr(self, attr):
        val = getattr(self.obj, attr)
        if isinstance(val, SharedAttribute):
            del self.base_dict[attr]
        delattr(self.obj, attr)

    def load_attr(self, attr):
        val = getattr(self.obj, attr)
        if isinstance(val, SharedAttribute):
            val = self.base_dict[attr]
            setattr(self.obj, attr, val)
        return val

    def get_saved_keys(self, obj):
        return obj.__dict__.keys()

    def save(self, keys=None):
        if keys is None:
            keys = self.get_saved_keys(self.obj)
        for k in keys:
            self.save_attr(k)
        return self.obj

    def load(self, keys=None):
        if keys is None:
            keys = self.get_saved_keys(self.obj)
        for k in keys:
            self.load_attr(k)
        if isinstance(self.obj, PrimitiveTypeHolder):
            return self.obj.val
        else:
            return self.obj

    def _cleanup(self):
        try:
            saved_keys = self.base_dict.keys()
        except:
            pass
        else:
            for k in saved_keys:
                self.del_attr(k)

    def __del__(self):
        self._cleanup()
    # def delete(self):
    #     for k in self.get_saved_keys(self.obj):
    #         self.del_attr(k)
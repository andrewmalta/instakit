#!/usr/bin/env python
# encoding: utf-8
"""
                                                                                
                        d8888 888888b.    .d8888b.                              
      o                d88888 888  "88b  d88P  Y88b                    o        
     d8b              d88P888 888  .88P  888    888                   d8b       
    d888b            d88P 888 8888888K.  888        .d8888b          d888b      
"Y888888888P"       d88P  888 888  "Y88b 888        88K          "Y888888888P"  
  "Y88888P"        d88P   888 888    888 888    888 "Y8888b.       "Y88888P"    
  d88P"Y88b       d8888888888 888   d88P Y88b  d88P      X88       d88P"Y88b    
 dP"     "Yb     d88P     888 8888888P"   "Y8888P"   88888P'      dP"     "Yb   
                                                                                
                                                                                
Instakit’s Abstract Base Classes – née ABCs – for processors and data structures

"""
from __future__ import print_function

from pkgutil import extend_path
from abc import ABC, abstractmethod as abstract
from collections import defaultdict
from enum import Enum as EnumBase
from functools import wraps

if '__path__' in locals():
    __path__ = extend_path(__path__, __name__)

__all__ = ('is_in_class',
           'Processor', 'Enum',
           'Container', 'MutableContainer',
           'NOOp', 'Fork',
           'ThresholdMatrixProcessor',
           'NDProcessorBase')

__dir__ = lambda: list(__all__)

def is_in_class(attr, cls):
    """ Test whether or not a class has a named attribute,
        regardless of whether the class uses `__slots__` or
        an internal `__dict__`.
    """
    if hasattr(cls, '__dict__'):
        return attr in cls.__dict__
    elif hasattr(cls, '__slots__'):
        return attr in cls.__slots__
    return False

class Processor(ABC):
    
    """ Base abstract processor class. """
    __slots__ = tuple()
    
    @abstract
    def process(self, image):
        """ Process an image instance, per the processor instance,
            returning the processed image data
        """
        ...
    
    def __call__(self, image):
        return self.process(image)
    
    @classmethod
    def __subclasshook__(cls, subclass):
        if subclass is Processor:
            if any(is_in_class('process', ancestor) for ancestor in subclass.__mro__):
                return True
        return NotImplemented

class Enum(EnumBase):
    
    """ Base abstract processor enum. """
    __slots__ = tuple()
    
    @abstract
    def process(self, image): ...

class Container(Processor):
    
    """ Base abstract processor container. """
    __slots__ = tuple()
    
    @abstract
    def iterate(self):
        """ Return an ordered iterable of sub-processors. """
        ...
    
    @classmethod
    @abstract
    def base_type(cls): ...
    
    @abstract
    def __len__(self): ...
    
    @abstract
    def __contains__(self, value): ...
    
    @abstract
    def __getitem__(self, idx): ...
    
    def index(self, value):
        raise NotImplementedError()
    
    def get(self, idx, default_value):
        raise NotImplementedError()
    
    def last(self):
        raise NotImplementedError()

class MutableContainer(Container):
    
    """ Base abstract processor mutable container. """
    __slots__ = tuple()
    
    @abstract
    def __setitem__(self, idx, value): ...
    
    @abstract
    def __delitem__(self, idx, value): ...
    
    def append(self, value):
        raise NotImplementedError()
    
    def extend(self, iterable):
        raise NotImplementedError()
    
    def update(self, iterable=None, **kwargs):
        raise NotImplementedError()

class NOOp(Processor):
    
    """ A no-op processor. """
    __slots__ = tuple()
    
    def process(self, image):
        return image

class Fork(MutableContainer):
    
    """ Base abstract forking processor. """
    __slots__ = ('dict', '__weakref__')
    
    @classmethod
    def base_type(cls):
        return defaultdict
    
    def __init__(self, default_factory, *args, **kwargs):
        if default_factory in (None, NOOp):
            default_factory = NOOp
        if not callable(default_factory):
            raise AttributeError("Fork() requires a callable default_factory")
        
        self.dict = defaultdict(default_factory, *args, **kwargs)
        super(Fork, self).__init__()
    
    @property
    def default_factory(self):
        return self.dict.default_factory
    
    @wraps(defaultdict.__len__)
    def __len__(self):
        return len(self.dict)
    
    @wraps(defaultdict.__contains__)
    def __contains__(self, value):
        return value in self.dict
    
    @wraps(defaultdict.__getitem__)
    def __getitem__(self, idx):
        return self.dict[idx]
    
    @wraps(defaultdict.__setitem__)
    def __setitem__(self, idx, value):
        if value in (None, NOOp):
            value = NOOp()
        self.dict[idx] = value
    
    @wraps(defaultdict.__delitem__)
    def __delitem__(self, idx):
        del self.dict[idx]
    
    def get(self, idx, default_value=None):
        """ Get a value from the Fork, with an optional default
            value to use should a value not be present for this key.
            See dict.get(…) for details.
        """
        return self.dict.get(idx, default_value)
    
    def update(self, iterable=None, **kwargs):
        """ Update the Fork with new dict info.
            See dict.update(…) for details.
        """
        self.dict.update(iterable or tuple(), **kwargs)
    
    @abstract
    def split(self, image): ...
    
    @abstract
    def compose(self, *bands): ...

class ThresholdMatrixProcessor(Processor):
    
    """ Abstract base class for a processor using a uint8 threshold matrix """
    # This is used in instakit.processors.halftone
    __slots__ = ('threshold_matrix',)
    
    LO_TUP = (0,)
    HI_TUP = (255,)
    
    def __init__(self, threshold = 128.0):
        """ Initialize with a threshold value between 0 and 255 """
        self.threshold_matrix = int(threshold)  * self.LO_TUP + \
                           (256-int(threshold)) * self.HI_TUP

class NDProcessorBase(Processor):
    
    """ An image processor ancestor class that represents PIL image
        data in a `numpy.ndarray`. This is the base abstract class,
        specifying necessary methods for subclasses to override.
        
        Note that “process(…)” has NOT been implemented yet in the
        inheritance chain – a subclass will need to furnish it.
    """
    __slots__ = tuple()
    
    @abstract
    def process_nd(self, ndimage):
        """ Override NDProcessor.process_nd(…) in subclasses
            to provide functionality that acts on image data stored
            in a `numpy.ndarray`.
        """
        ...
    
    @staticmethod
    @abstract
    def compand(ndimage): ...
    
    @staticmethod
    @abstract
    def uncompand(ndimage): ...


def test():
    
    class SlowAtkinson(ThresholdMatrixProcessor):
        __slots__ = tuple()
        def process(self, image):
            from instakit.utils.mode import Mode
            image = Mode.L.process(image)
            for y in range(image.size[1]):
                for x in range(image.size[0]):
                    old = image.getpixel((x, y))
                    new = self.threshold_matrix[old]
                    err = (old - new) >> 3 # divide by 8.
                    image.putpixel((x, y), new)
                    for nxy in [(x+1, y),
                                (x+2, y),
                                (x-1, y+1),
                                (x, y+1),
                                (x+1, y+1),
                                (x, y+2)]:
                        try:
                            image.putpixel(nxy, int(
                            image.getpixel(nxy) + err))
                        except IndexError:
                            pass
            return image
    
    from pprint import pprint
    slow_atkinson = SlowAtkinson()
    pprint(slow_atkinson)
    print("DICT?", hasattr(slow_atkinson, '__dict__'))
    print("SLOTS?", hasattr(slow_atkinson, '__slots__'))
    pprint(slow_atkinson.__slots__)
    pprint(slow_atkinson.__class__.__base__.__slots__)
    print("THRESHOLD_MATRIX:", slow_atkinson.threshold_matrix)

if __name__ == '__main__':
    test()
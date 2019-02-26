
from __future__ import print_function

from PIL import ImageOps, ImageChops
from abc import ABC, abstractmethod as abstract
from collections import defaultdict
from enum import Enum as EnumBase, unique
from functools import wraps
# from six import add_metaclass

try:
    from functools import reduce
except ImportError:
    pass

from instakit.utils.mode import Mode
from instakit.utils.misc import string_types

class Processor(ABC):
    
    """ Base abstract processor class. """
    
    @abstract
    def process(self, image): ...
    
    def __call__(self, image):
        return self.process(image)

class Enum(EnumBase):
    
    """ Base abstract processor enum. """
    
    @abstract
    def process(self, image): ...

class Container(Processor):
    
    """ Base abstract processor container. """
    
    @abstract
    def iterate(self):
        """ Return an ordered iterable of sub-processors. """
        ...
    
    @abstract
    def __len__(self): ...
    
    @abstract
    def __contains__(self, value): ...
    
    @abstract
    def __getitem__(self, idx): ...
    
    # Abstract but optional methods:
    
    def __setitem__(self, idx, value):
        raise NotImplementedError()
    
    def get(self, idx, default_value):
        raise NotImplementedError()
    
    def index(self, value):
        raise NotImplementedError()

class Pipeline(Container):
    """ A linear pipeline of processors to be applied en masse.
        Derived from an ImageKit class:
        imagekit.processors.base.ProcessorPipeline
    """
    @wraps(list.__init__)
    def __init__(self, *args):
        self.list = list(*args)
    
    def iterate(self):
        return iter(self.list)
    
    @wraps(list.__len__)
    def __len__(self):
        return len(self.list)
    
    @wraps(list.__contains__)
    def __contains__(self, value):
        return value in self.list
    
    @wraps(list.__getitem__)
    def __getitem__(self, idx):
        return self.list(idx)
    
    @wraps(list.__setitem__)
    def __setitem__(self, idx, value):
        if value in (None, NOOp):
            value = NOOp()
        self.list[idx] = value
    
    @wraps(list.index)
    def index(self, value):
        return self.list.index(value)
    
    @wraps(list.append)
    def append(self, value):
        self.list.append(value)
    
    @wraps(list.extend)
    def extend(self, iterable):
        self.list.extend(iterable)
    
    def last(self):
        return self.list[-1]
    
    def process(self, image):
        for p in self.iterate():
            image = p.process(image)
        return image

class Fork(Container):
    
    """ Base abstract forking processor. """
    
    def __init__(self, default_factory, *args, **kwargs):
        if default_factory in (None, NOOp):
            default_factory = NOOp
        if not callable(default_factory):
            raise AttributeError("Fork() requires a callable default_factory")
        
        self.dict = defaultdict(default_factory, **kwargs)
        super(Fork, self).__init__(*args, **kwargs)
    
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
    
    @wraps(defaultdict.get)
    def get(self, idx, default_value=None):
        return self.dict.get(idx, default_value)
    
    @abstract
    def split(self, image): ...
    
    @abstract
    def compose(self, *bands): ...


class BandFork(Fork):
    """ A processor wrapper that, for each image channel:
        - applies a band-specific processor, or
        - applies a default processor.
        
        * Ex. 1: apply the Atkinson ditherer to each of an images' bands:
        >>> from instakit.utils.pipeline import BandFork
        >>> from instakit.processors.halftone import Atkinson
        >>> BandFork(Atkinson).process(my_image)
        
        * Ex. 2: apply the Atkinson ditherer to only one band:
        >>> from instakit.utils.pipeline import BandFork
        >>> from instakit.processors.halftone import Atkinson
        >>> bfork = BandFork(None)
        >>> bfork['G'] = Atkinson()
        >>> bfork.process(my_image)
    """
    
    mode_t = Mode.RGB
    
    def __init__(self, default_factory, *args, **kwargs):
        if 'mode' in kwargs:
            new_mode = kwargs.pop('mode')
            if type(new_mode) in string_types:
                new_mode = Mode.for_string(new_mode)
            if type(new_mode) is Mode:
                self.mode_t = new_mode # SHADOW!!
        
        super(BandFork, self).__init__(default_factory, *args, **kwargs)
    
    @property
    def mode(self):
        return self.mode_t
    
    @mode.setter
    def mode(self, value):
        if type(value) in string_types:
            value = Mode.for_string(value)
        if type(value) is Mode:
            self.set_mode_t(value)
        else:
            raise TypeError("invalid mode type: %s (%s)" % (type(value), value))
    
    def set_mode_t(self, value):
        self.mode_t = value
    
    @property
    def band_labels(self):
        return self.mode_t.bands
    
    def iterate(self):
        for band in self.band_labels:
            yield self[band]
    
    def split(self, image):
        return self.mode_t.process(image).split()
    
    def compose(self, *bands):
        return self.mode_t.merge(*bands)
    
    def process(self, image):
        processed = []
        for processor, band in zip(self.iterate(),
                                   self.split(image)):
            processed.append(processor.process(band))
        return self.compose(*processed)

Pipe = Pipeline

class NOOp(Processor):
    """ A no-op processor. """
    def process(self, image):
        return image

ChannelFork = BandFork

ink_values = (
    (255, 255, 255),    # White
    (0,   250, 250),    # Cyan
    (250, 0,   250),    # Magenta
    (250, 250, 0),      # Yellow
    (0,   0,   0),      # Key (blacK)
    (255, 0,   0),      # Red
    (0,   255, 0),      # Green
    (0,   0,   255),    # Blue
)

class Ink(Enum):
    
    def rgb(self):
        return ink_values[self.value]
    
    def process(self, image):
        InkType = type(self)
        return ImageOps.colorize(Mode.L.process(image),
                                 InkType(0).rgb(),
                                 InkType(self.value).rgb())

@unique
class CMYKInk(Ink):
    
    WHITE = 0
    CYAN = 1
    MAGENTA = 2
    YELLOW = 3
    KEY = 4
    
    @classmethod
    def CMYK(cls):
        return (cls.CYAN, cls.MAGENTA, cls.YELLOW, cls.KEY)
    
    @classmethod
    def CMY(cls):
        return (cls.CYAN, cls.MAGENTA, cls.YELLOW)

@unique
class RGBInk(Ink):
    
    WHITE = 0
    RED = 5
    GREEN = 6
    BLUE = 7
    KEY = 4
    
    @classmethod
    def RGB(cls):
        return (cls.RED, cls.GREEN, cls.BLUE)
    
    @classmethod
    def BGR(cls):
        return (cls.BLUE, cls.GREEN, cls.RED)

class OverprintFork(BandFork):
    
    mode_t = Mode.CMYK
    
    def __init__(self, default_factory, *args, **kwargs):
        # Call super():
        super(OverprintFork, self).__init__(default_factory, *args, **kwargs)
        
        # Make each band-processor a Pipeline() ending in
        # the channel-appropriate CMYKInk enum processor:
        self.apply_CMYK_inks()
    
    def apply_CMYK_inks(self):
        modestring = self.mode_t.to_string()
        CMYKLabels = CMYKInk.CMYK()
        for band in self.band_labels:
            processor = self[band]
            idx = modestring.index(band)
            ink = CMYKInk(CMYKLabels[idx])
            if hasattr(processor, 'append'):
                if processor[-1] is not ink:
                    processor.append(ink)
                    self[band] = processor
            else:
                self[band] = Pipeline([processor, ink])
    
    def set_mode_t(self, value):
        if value is not type(self).mode_t:
            raise AttributeError(
                "OverprintFork only works in %s mode" % self.mode_t.to_string())
    
    def compose(self, *bands):
        return reduce(ImageChops.multiply, bands)

class Grid(Fork):
    pass

class Sequence(Fork):
    pass

ChannelOverprinter = OverprintFork

if __name__ == '__main__':
    from pprint import pprint
    from instakit.utils.static import asset
    from instakit.processors.halftone import Atkinson
    
    image_paths = list(map(
        lambda image_file: asset.path('img', image_file),
            asset.listfiles('img')))
    image_inputs = list(map(
        lambda image_path: Mode.RGB.open(image_path),
            image_paths))
    
    for image_input in image_inputs[:2]:
        OverprintFork(Atkinson).process(image_input).show()
        
        print('Creating ChannelOverprinter and ChannelFork with Atkinson ditherer...')
        overatkins = OverprintFork(Atkinson)
        forkatkins = BandFork(Atkinson)
        
        print('Processing image with ChannelForked Atkinson in default (RGB) mode...')
        forkatkins.process(image_input).show()
        forkatkins.mode = 'CMYK'
        print('Processing image with ChannelForked Atkinson in CMYK mode...')
        forkatkins.process(image_input).show()
        forkatkins.mode = 'RGB'
        print('Processing image with ChannelForked Atkinson in RGB mode...')
        forkatkins.process(image_input).show()
        
        overatkins.mode = 'CMYK'
        print('Processing image with ChannelOverprinter-ized Atkinson in CMYK mode...')
        overatkins.process(image_input).show()
        
        print('Attempting to reset ChannelOverprinter to RGB mode...')
        import traceback, sys
        try:
            overatkins.mode = 'RGB'
            overatkins.process(image_input).show()
        except:
            print(">>>>>>>>>>>>>>>>>>>>> TRACEBACK <<<<<<<<<<<<<<<<<<<<<")
            traceback.print_exc(file=sys.stdout)
            print("<<<<<<<<<<<<<<<<<<<<< KCABECART >>>>>>>>>>>>>>>>>>>>>")
            print('')
    
    bandfork = BandFork(None)
    pprint(bandfork)
    
    print(image_paths)
    

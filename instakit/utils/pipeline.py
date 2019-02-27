# encoding: utf-8
from __future__ import print_function

from PIL import ImageOps, ImageChops
from enum import unique
from functools import wraps

try:
    from functools import reduce
except ImportError:
    pass

from instakit.abc import Enum, Fork, Container, MutableContainer, NOOp
from instakit.utils.gcr import BasicGCR
from instakit.utils.mode import Mode
from instakit.utils.misc import string_types
from instakit.processors.adjust import AutoContrast

class Pipe(Container):
    
    """ A static linear pipeline of processors to be applied en masse.
        Derived from an ImageKit class:
        imagekit.processors.base.ProcessorPipeline
    """
    __slots__ = ('tuple',)
    
    @classmethod
    def base_type(cls):
        return tuple
    
    @wraps(tuple.__init__)
    def __init__(self, *args):
        self.tuple = tuple(*args)
    
    def iterate(self):
        return iter(self.tuple)
    
    @wraps(tuple.__len__)
    def __len__(self):
        return len(self.tuple)
    
    @wraps(tuple.__contains__)
    def __contains__(self, value):
        return value in self.tuple
    
    @wraps(tuple.__getitem__)
    def __getitem__(self, idx):
        return self.tuple[idx]
    
    @wraps(tuple.index)
    def index(self, value):
        return self.tuple.index(value)
    
    def last(self):
        return self.tuple[-1]
    
    def process(self, image):
        for p in self.iterate():
            image = p.process(image)
        return image

class Pipeline(MutableContainer):
    
    """ A mutable linear pipeline of processors to be applied en masse.
        Derived from an ImageKit class:
        imagekit.processors.base.ProcessorPipeline
    """
    __slots__ = ('list',)
    
    @classmethod
    def base_type(cls):
        return list
    
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
        return self.list[idx]
    
    @wraps(list.__setitem__)
    def __setitem__(self, idx, value):
        if value in (None, NOOp):
            value = NOOp()
        self.list[idx] = value
    
    @wraps(list.__delitem__)
    def __delitem__(self, idx):
        del self.list[idx]
    
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

class BandFork(Fork):
    
    """ BandFork is a processor container -- a processor that applies other
        processors. BandFork acts selectively on the individual bands of
        input image data, either:
        - applying a band-specific processor instance, or
        - applying a default processor successively across all bands.
        
        BandFork’s interface is closely aligned with Python’s mutable-mapping
        API‡ -- with which most programmers are no doubt quite familiar:
        
        • Ex. 1: apply Atkinson dithering to each of an RGB images’ bands:
        >>> from instakit.utils.pipeline import BandFork
        >>> from instakit.processors.halftone import Atkinson
        >>> BandFork(Atkinson).process(my_image)
        
        • Ex. 2: apply Atkinson dithering to only the green band:
        >>> from instakit.utils.pipeline import BandFork
        >>> from instakit.processors.halftone import Atkinson
        >>> bfork = BandFork(None)
        >>> bfork['G'] = Atkinson()
        >>> bfork.process(my_image)
        
        BandFork inherits from `instakit.abc.Fork`, which itself is not just
        an Instakit Processor. The Fork ABC implements the required methods
        of an Instakit Processor Container†, through which it furnishes an
        interface to individual bands -- also generally known as channels,
        per the labeling of the relevant Photoshop UI elements -- of image
        data. 
        
        † q.v. the `instakit.abc` module source code supra.
        ‡ q.v. the `collections.abc` module, and the `MutableMapping`
                    abstract base class within, supra.
    """
    __slots__ = ('mode', 'mode_t')
    
    mode_t = Mode.RGB
    
    def __init__(self, default_factory, *args, **kwargs):
        """ Initialize a BandFork instance, using the given callable value
            for `default_factory` and any band-appropriate keyword-arguments,
            e.g. `(R=MyProcessor, G=MyOtherProcessor, B=None)`
        """
        # Reset mode if a new mode was specified:
        if 'mode' in kwargs:
            self.mode = kwargs.pop('mode')
        
        # Call super(…):
        super(BandFork, self).__init__(default_factory, *args, **kwargs)
    
    @property
    def mode(self):
        return self.mode_t
    
    @mode.setter
    def mode(self, value):
        if type(value) in string_types:
            value = Mode.for_string(value)
        if type(value) is Mode:
            if value is not self.mode_t:
                self.set_mode_t(value)
        else:
            raise TypeError("invalid mode type: %s (%s)" % (type(value), value))
    
    def set_mode_t(self, value):
        self.mode_t = value # SHADOW!!
    
    @property
    def band_labels(self):
        return self.mode_t.bands
    
    def iterate(self):
        for band_label in self.band_labels:
            yield self[band_label]
    
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
    
    """ A ChannelFork subclass that rebuilds its output image using
        multiply-mode to simulate CMYK overprinting effects.
        
        N.B. While this Fork-based processor operates strictly in CMYK mode,
        the composite image it eventually returns will be in RGB mode. This is
        because the CMYK channels are each individually converted to colorized
        representations in order to simulate monotone ink preparations; the
        final compositing operation, in which these colorized channel separation
        images are combined with multiply-mode, is also computed using the RGB
        color model.
    """
    __slots__ = ('contrast', 'basicgcr')
    
    mode_t = Mode.CMYK
    inks = CMYKInk.CMYK()
    
    def __init__(self, default_factory, gcr=20, *args, **kwargs):
        """ Initialize an OverprintFork instance with the given callable value
            for `default_factory` and any band-appropriate keyword-arguments,
            e.g. `(C=MyProcessor, M=MyOtherProcessor, Y=MyProcessor, K=None)`
        """
        # Store BasicGCR and AutoContrast processors:
        self.contrast = AutoContrast()
        self.basicgcr = BasicGCR(percentage=gcr)
        
        # Call super():
        super(OverprintFork, self).__init__(default_factory, *args, **kwargs)
        
        # Make each band-processor a Pipeline() ending in
        # the channel-appropriate CMYKInk enum processor:
        if default_factory is not None:
            self.apply_CMYK_inks()
    
    def apply_CMYK_inks(self):
        """ This method ensures that each bands’ processor is set up
            as a Pipeline() ending in a CMYKInk corresponding to the
            band in question. Calling it multiple times *should* be
            idempotent (but don’t quote me on that)
        """
        for band_label, ink in zip(self.band_labels,
                              type(self).inks):
            processor = self[band_label]
            if hasattr(processor, 'append'):
                if processor[-1] is not ink:
                    processor.append(ink)
                    self[band_label] = processor
            else:
                self[band_label] = Pipeline([processor, ink])
    
    def set_mode_t(self, value):
        """ Raise an exception if an attempt is made to set the mode to anything
            other than CMYK
        """
        if value is not Mode.CMYK:
            raise AttributeError(
                "OverprintFork only works in %s mode" % Mode.CMYK.to_string())
    
    def update(self, iterable=None, **kwargs):
        """ OverprintFork.update(…) re-applies CMYK ink processors to the
            updated processing dataflow
        """
        super(OverprintFork, self).update(iterable, **kwargs)
        self.apply_CMYK_inks()
    
    def split(self, image):
        """ OverprintFork.split(image) uses imagekit.utils.gcr.BasicGCR(…) to perform
            gray-component replacement in CMYK-mode images; for more information,
            see the imagekit.utils.gcr module
        """
        return self.basicgcr.process(image).split()
    
    def compose(self, *bands):
        """ OverprintFork.compose(…) uses PIL.ImageChops.multiply() to create
            the final composite image output
        """
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
        
        print('Creating OverprintFork and BandFork with Atkinson ditherer...')
        overatkins = OverprintFork(Atkinson)
        forkatkins = BandFork(Atkinson)
        
        print('Processing image with BandForked Atkinson in default (RGB) mode...')
        forkatkins.process(image_input).show()
        forkatkins.mode = 'CMYK'
        print('Processing image with BandForked Atkinson in CMYK mode...')
        forkatkins.process(image_input).show()
        forkatkins.mode = 'RGB'
        print('Processing image with BandForked Atkinson in RGB mode...')
        forkatkins.process(image_input).show()
        
        overatkins.mode = 'CMYK'
        print('Processing image with OverprintFork-ized Atkinson in CMYK mode...')
        overatkins.process(image_input).show()
        
        print('Attempting to reset OverprintFork to RGB mode...')
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
    

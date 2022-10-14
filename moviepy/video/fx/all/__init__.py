"""
Loads all the fx !
Usage:
import moviepy.video.fx.all as vfx
clip = vfx.resize(some_clip, width=400)
clip = vfx.mirror_x(some_clip)
"""

import pkgutil

import moviepy.video.fx as fx

__all__ = [name for _, name, _ in pkgutil.iter_modules(
    fx.__path__) if name != "all"]

# for name in __all__:
#     # exec("from ..%s import %s" % (name, name))
#     print("from  moviepy.video.fx import %s" % (name))

from moviepy.video.fx import accel_decel
from moviepy.video.fx import blackwhite
from moviepy.video.fx import blink
from moviepy.video.fx import colorx
from moviepy.video.fx import crop
from moviepy.video.fx import even_size
from moviepy.video.fx import fadein
from moviepy.video.fx import fadeout
from moviepy.video.fx import freeze
from moviepy.video.fx import freeze_region
from moviepy.video.fx import gamma_corr
from moviepy.video.fx import headblur
from moviepy.video.fx import invert_colors
from moviepy.video.fx import loop
from moviepy.video.fx import lum_contrast
from moviepy.video.fx import make_loopable
from moviepy.video.fx import margin
from moviepy.video.fx import mask_and
from moviepy.video.fx import mask_color
from moviepy.video.fx import mask_or
from moviepy.video.fx import mirror_x
from moviepy.video.fx import mirror_y
from moviepy.video.fx import painting
from moviepy.video.fx import resize
from moviepy.video.fx import rotate
from moviepy.video.fx import scroll
from moviepy.video.fx import speedx
from moviepy.video.fx import supersample
from moviepy.video.fx import time_mirror
from moviepy.video.fx import time_symmetrize

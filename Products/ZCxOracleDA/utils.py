
from os import path as os_path
from App.ImageFile import ImageFile
from OFS.misc_ import Misc_ as MiscImage
from OFS.misc_ import misc_ as misc_images


def registerIcon(klass, iconspec, _prefix=None):

    """ Make an icon available for a given class.
    o 'klass' is the class being decorated.
    o 'iconspec' is the path within the product where the icon lives.
    """
    modname = klass.__module__
    pid = modname.split('.')[1]
    name = os_path.split(iconspec)[1]
    klass.icon = 'misc_/%s/%s' % (pid, name)
    icon = ImageFile(iconspec, _prefix)
    icon.__roles__=None
    if not hasattr(misc_images, pid):
        setattr(misc_images, pid, MiscImage(pid, {}))
    getattr(misc_images, pid)[name]=icon


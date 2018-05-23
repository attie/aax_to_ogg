from os import path
from glob import glob
from importlib import import_module

FT_MODULE_BASE = 'aax_to_ogg.filetypes'

class FileHandler:
    def __init__(self, config):
        self.config = config

        # load each of the filetype plugins...
        filetypes_path = import_module(FT_MODULE_BASE).__path__._path[0]
        plugin_names = [ name for name in glob(path.join(filetypes_path, '*.py')) ]

        self.plugins = []
        for plugin in [ name.rsplit(path.sep, 1)[-1].rsplit('.', 1)[0] for name in plugin_names]:
            module_name = '%s.%s' % ( FT_MODULE_BASE, plugin )
            class_name = 'FileHandler_%s' % ( plugin )

            try:
                ft_module = import_module(module_name)
                ft_class = getattr(ft_module, class_name)
            except:
                print('WARNING: plugin [%s] failed to load...' % ( plugin ))
                raise
                continue

            self.plugins.append(ft_class)

    def get_file_handler(self, filename):
        for plugin in self.plugins:
            if not plugin.can_handle_file(filename):
                continue

            return plugin

        raise Exception('cannot handle file... [%s]' % ( filename ))

    def handle_file(self, filename):
        plugin = self.get_file_handler(filename)

        p = plugin(self, self.config, filename)
        p.process()

from aax_to_ogg.args import Args
from aax_to_ogg.filehandler import FileHandler

def main():
    config = Args().parse()
    handler = FileHandler(config)

    for filename in config.files:
        print('Processing [%s]...' % ( filename ))
        try:
            handler.handle_file(filename)
        except Exception as e:
            if config.debug:
                raise
            print('    ERROR: %s' % ( e ))

    return 0

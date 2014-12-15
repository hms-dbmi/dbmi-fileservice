import logging
import sys,os

from cliff.app import App
from cliff.commandmanager import CommandManager

from .utils import parseConfig


class FileService(App):

    log = logging.getLogger(__name__)
    
    configoptions = {}
    user=None
    description = 'fileservice app'
    version = '0.1'

    def __init__(self):
        super(FileService, self).__init__(
            description=self.description,
            version=self.version,
            command_manager=CommandManager('fileservice.application'),
            )

    def build_option_parser(self, description, version):
        parser = super(FileService, self).build_option_parser(
            description, version)

        parser.add_argument('--config',
                            default=os.path.expanduser("~")+'/.fileservice.cfg',
                            help="This is the config file (in python config format): "+os.path.expanduser("~")+'/.fileservice.cfg')

        parser.add_argument('--cloud',
                            default="aws",
                            help="Cloud you are using. Default AWS.",
                            choices=["aws","google"])

        
        return parser

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)
        self.configoptions = parseConfig(self.options.config)
        if not self.configoptions:
            self.log.info("Need a valid conf file")
            sys.exit(1)
            
        #self.user = User(self.configoptions)
        
        if not self.user.auth():
            self.log.info("unable to authenticate user %s" % self.configoptions["username"])
            sys.exit(1)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = FileService()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
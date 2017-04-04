class CommandParserBase:
    """A basic command parser.

To use this class, inherit from it and define do_xxx methods for commands. They will be passed strings with the command stripped off.  Commands start with ..  Any line that doesn't start with . is passed to do_default. You must implement do_default or else.

Subclasses should define the member variable prompt to a prompt string.

Docstrings are documentation. The first line should be a brief, one-line description.  The rest should explain syntax and parameters.
This class implements a .help command for you. You can override it by overriding do_help.

This class also implements a .quit, overridable by implementing do_quit.
To quit without using the quit command, call quit().

This class does not provide an intro message."""

    def __init__(self):
        self._running = True

    def run(self):
        self._running = True
        while self._running:
            line = input(self.prompt)
            if line.startswith("."):
                word, sep, rest = line.partition(" ")
                rest = rest.lstrip().rstrip()
                cmd = getattr(self, "do_"+word[1:], None)
                if cmd is None:
                    print(word + " is not a valid command. Use .help for help.")
                    continue
                cmd(rest)
            else:
                self.do_default(line)

    def do_help(self, argument):
        """Get help on a command.

Syntax: .help or .help <command>

use .help for a list of commands. Use .help <command> for info on a command."""
        if len(argument) == 0:
            commands = dir(self)
            commands.sort()
            for i in commands:
                if i == "do_default" or not i.startswith("do_"):
                    continue
                cmd = getattr(self, i)
                cmd_name = "."+i[3:]
                cmd_summary = cmd.__doc__.split("\n")[0]
                print("{}: {}".format(cmd_name, cmd_summary))
        else:
            cmd = getattr(self, "do_"+argument, None)
            if cmd is None:
                print(".{} is not a valid command.".format(argument))
                return
            print(cmd.__doc__)

    def do_quit(self, argument):
        """Quit the program.

syntax: .quit"""
        self.quit_hook()
        self._running = False

    def quit_hook(self):
        """A hook to let subclasses do something on quit."""
        pass